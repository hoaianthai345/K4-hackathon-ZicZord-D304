import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.catchup_service import CatchupService
from app.chat_service import ChatService
from app.context_tools import ContextPlan, ContextToolService
from app.dataset_ingest import localized_timestamp
from app.learning_ingest import (
    parse_transcript,
    parse_workshop_transcript,
    redact_for_model,
)
from app.schemas import Memory
from app.scopes import user_record
from app.store import JsonStore


class FakeDatabase:
    def __init__(self):
        self.learning_calls = []
        self.message_calls = []

    async def search_learning(self, query, scopes, **kwargs):
        self.learning_calls.append((query, scopes, kwargs))
        return [
            {
                "source_id": "lesson-test",
                "source_type": "lesson",
                "source_kind": "transcript",
                "source_ref": "T06-001",
                "title": "Transformer",
                "day_code": "transformer-attention",
                "channel_key": "lecture",
                "scope_key": "cohort:K4",
                "sequence_number": 1,
                "page_number": None,
                "created_at": None,
                "content": "Attention giúp mô hình chú ý đến token liên quan.",
                "metadata": {},
            }
        ]

    async def search_messages(self, query, scopes, **kwargs):
        self.message_calls.append((query, scopes, kwargs))
        return [
            {
                "source_id": "qa-test",
                "source_type": "message",
                "channel_key": "qa",
                "scope_key": "cohort:K4",
                "created_at": datetime(2026, 7, 29, 9, 0, tzinfo=UTC),
                "content": "Học viên hỏi cách kiểm tra trạng thái điểm danh.",
                "metadata": {},
            }
        ]


def test_transcript_parser_preserves_citation_codes(tmp_path: Path):
    path = tmp_path / "transcript-01-clean.md"
    path.write_text(
        "# Bài giảng\n\n## Xác định vấn đề\n\n"
        "**[T01-001]** Nội dung thứ nhất.\n\n"
        "**[T01-002]** Nội dung thứ hai.\n",
        encoding="utf-8",
    )
    records = parse_transcript(path, tmp_path)
    assert [row["source_ref"] for row in records] == ["T01-001", "T01-002"]
    assert records[0]["metadata"]["section"] == "Xác định vấn đề"
    assert records[0]["content_original"] == "Nội dung thứ nhất."


def test_learning_redaction_covers_credentials_before_model():
    value = (
        "Mã 01862, gửi mail student@example.com, gọi 0912345678, "
        "key sk-or-v1-abcdefghijklmnopqrstuvwxyz123456"
    )
    redacted = redact_for_model(value)
    assert "01862" not in redacted
    assert "student@example.com" not in redacted
    assert "0912345678" not in redacted
    assert "sk-or-v1-" not in redacted
    assert "[API_KEY_REDACTED]" in redacted


def test_workshop_parser_keeps_local_event_time_and_source_timestamp(
    tmp_path: Path,
):
    workshop_dir = tmp_path / "workshops"
    workshop_dir.mkdir()
    path = workshop_dir / "workshop.txt"
    path.write_text(
        "# Workshop\n\n"
        "Meeting started: 7/30/2026, 8:13:11 PM\n\n"
        "## Transcript\n\n"
        "00:40 Mentor: Team phải chốt phạm vi sáu tuần.\n"
        "00:40 Học viên: Em đã rõ yêu cầu.\n"
        "01:02:03 Học viên: Team cần làm gì tiếp theo?\n",
        encoding="utf-8",
    )
    records = parse_workshop_transcript(path, tmp_path)
    assert len(records) == 3
    assert records[0]["day_code"] == "workshop-2026-07-30"
    assert records[0]["occurred_at"].isoformat() == "2026-07-30T20:13:51+07:00"
    assert len({record["context_id"] for record in records}) == 3
    assert records[2]["metadata"]["timestamp_code"] == "01:02:03"


def test_crawler_timestamp_without_offset_is_vietnam_local_time():
    value = localized_timestamp("2026-07-30T16:08:49.699000")
    assert value is not None
    assert value.isoformat() == "2026-07-30T16:08:49.699000+07:00"


def test_lesson_query_calls_local_learning_search_with_authorized_scopes():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    result = asyncio.run(
        service.retrieve(
            user,
            "Giảng viên giải thích Transformer và attention như thế nào?",
            "bot-commands",
        )
    )
    assert result.should_answer_directly is True
    assert database.learning_calls
    _, scopes, kwargs = database.learning_calls[0]
    assert "cohort:K4" in scopes
    assert "team:T004" in scopes
    assert kwargs["day_codes"] == ["transformer-attention"]
    assert any(call.name == "search_learning_context" for call in result.calls)


def test_generic_course_overview_routes_to_learning_context():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    result = asyncio.run(
        service.retrieve(
            user,
            "Mọi người học cái gì?",
            "bot-commands",
        )
    )

    assert result.plan.lesson_intent is True
    assert result.should_answer_directly is True
    assert database.learning_calls
    assert database.message_calls == []
    assert any(call.name == "search_learning_context" for call in result.calls)
    assert not any(
        call.name == "rag_anything_hybrid_search"
        for call in result.calls
    )


def test_workshop_yesterday_routes_to_dated_event_context():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    plan = service.plan(
        user,
        "Tóm tắt workshop hôm qua",
        "bot-commands",
        now=datetime(2026, 7, 31, 5, 0, tzinfo=UTC),
    )
    assert plan.lesson_intent is True
    assert plan.day_codes == ["workshop-2026-07-30"]
    assert plan.source_kinds == ["event_brief", "workshop_transcript"]
    assert plan.start_time == datetime(2026, 7, 29, 17, 0, tzinfo=UTC)
    assert plan.end_time == datetime(2026, 7, 30, 17, 0, tzinfo=UTC)
    asyncio.run(
        service.retrieve(
            user,
            "Tóm tắt workshop hôm qua",
            "bot-commands",
            now=datetime(2026, 7, 31, 5, 0, tzinfo=UTC),
        )
    )
    assert database.learning_calls
    assert database.message_calls == []


def test_hackathon_explicit_date_routes_to_official_competition_rules():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    plan = service.plan(
        user,
        "Giải thích cuộc thi mini hackathon ngày 30/07",
        "bot-commands",
        now=datetime(2026, 7, 31, 5, 0, tzinfo=UTC),
    )
    assert plan.day_codes == ["mini-hackathon-2026"]
    assert plan.source_kinds == ["competition_rule"]
    assert plan.start_time == datetime(2026, 7, 29, 17, 0, tzinfo=UTC)
    assert plan.end_time == datetime(2026, 7, 30, 17, 0, tzinfo=UTC)
    assert "30/07" not in plan.normalized_query


def test_time_and_channel_query_builds_exact_discord_filter():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    now = datetime(2026, 7, 30, 5, 0, tzinfo=UTC)
    result = asyncio.run(
        service.retrieve(
            user,
            "Tóm tắt kênh hỏi đáp hôm qua",
            "bot-commands",
            now=now,
        )
    )
    assert database.message_calls
    _, _, kwargs = database.message_calls[0]
    assert kwargs["channel_keys"] == ["qa"]
    assert kwargs["start_time"] == datetime(2026, 7, 28, 17, 0, tzinfo=UTC)
    assert kwargs["end_time"] == datetime(2026, 7, 29, 17, 0, tzinfo=UTC)
    assert result.plan.time_label == "hôm qua"
    calls = {call.name: call for call in result.calls}
    assert calls["get_current_datetime"].arguments["current_date"] == "2026-07-30"
    inspected = calls["inspect_context_date_range"].arguments
    assert inspected["requested_date"] == "2026-07-29"
    assert inspected["context_start"].startswith("2026-07-29T16:00:00")
    assert inspected["dated_source_count"] == 1


def test_internal_prompt_labels_and_thinking_are_removed_from_visible_answer():
    value = (
        "<think>hidden reasoning</think>"
        "Dựa trên TOOL_CONTEXT và TIME_FACTS, hôm qua là 29/07/2026. [C1]"
    )
    cleaned = ChatService._clean_tool_answer(value)
    assert "hidden reasoning" not in cleaned
    assert "TOOL_CONTEXT" not in cleaned
    assert "TIME_FACTS" not in cleaned
    assert "[C1]" not in cleaned
    assert "29/07/2026" in cleaned


def test_strict_channel_answer_does_not_mix_unrelated_confirmed_memory():
    timestamp = datetime(2026, 7, 30, tzinfo=UTC)
    team_memory = Memory(
        id="mem-team",
        scope_type="team",
        scope_id="T004",
        kind="decision",
        content="Team T004 chốt demo memory trước 18h.",
        created_by="U01862",
        created_at=timestamp,
        updated_at=timestamp,
    )
    plan = ContextPlan(
        query="Tóm tắt kênh hỏi đáp hôm qua",
        normalized_query="",
        channel_keys=["qa"],
        strict_discord_filter=True,
    )
    assert ChatService._memories_for_tool_answer(plan, [team_memory]) == []


def test_semantic_problem_query_keeps_rag_tool():
    database = FakeDatabase()
    service = ContextToolService(database)
    user = user_record("U01862")
    result = asyncio.run(
        service.retrieve(
            user,
            "Vì sao nhiều học viên không nhận được GitHub invite?",
            "bot-commands",
        )
    )
    assert result.should_answer_directly is False
    assert any(call.name == "rag_anything_hybrid_search" for call in result.calls)


class FakeTimelineDatabase:
    configured = True

    def __init__(self):
        self.scopes = []

    async def recent_messages(self, scopes, **_kwargs):
        self.scopes = scopes
        return [
            {
                "source_id": "message-real-1",
                "channel_key": "qa",
                "scope_key": "cohort:K4",
                "reporter_key": "U01862",
                "author_name": "Thái Hoài An",
                "created_at": datetime.now(UTC),
                "content": "Team chốt hoàn thiện API ingest trước 18h.",
                "flags": {},
                "reaction_count": 1,
            }
        ]

    async def recent_learning_events(self, scopes, **_kwargs):
        self.scopes = scopes
        return [
            {
                "source_id": "lesson-workshop-brief",
                "source_kind": "event_brief",
                "channel_key": "announcement",
                "scope_key": "cohort:K4",
                "title": "Workshop & Coaching 30/07/2026",
                "created_at": datetime.now(UTC),
                "content": "Mentor yêu cầu team chốt vai trò và project charter.",
                "metadata": {},
            }
        ]


def test_catchup_reads_authorized_database_timeline_and_event_brief(
    tmp_path: Path,
):
    database = FakeTimelineDatabase()
    service = CatchupService(
        JsonStore(tmp_path / "state.json"),
        database=database,
        api_public_url="https://api.example",
    )
    brief = asyncio.run(service.generate(user_record("U01862"), 24))
    source_ids = {
        citation.message_id
        for item in brief.items
        for citation in item.citations
    }
    assert "message-real-1" in source_ids
    assert "lesson-workshop-brief" in source_ids
    assert not any(source_id.startswith("dc-msg-") for source_id in source_ids)
    assert "cohort:K4" in database.scopes
    assert "team:T004" in database.scopes
    workshop_citation = next(
        citation
        for item in brief.items
        for citation in item.citations
        if citation.message_id == "lesson-workshop-brief"
    )
    assert "/api/rag/sources/lesson/" in workshop_citation.permalink
