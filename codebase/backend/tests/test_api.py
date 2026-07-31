import os
from datetime import UTC, datetime
from pathlib import Path

os.environ["MEMORY_PROVIDER"] = "local"
os.environ["STATE_PATH"] = str(Path("/tmp") / "kute-discord-test.json")
for credential_name in (
    "OPENROUTER_API_KEY",
    "OPENROUTER_API_KEY_PHUC",
    "OPENROUTER_API_KEY_KHANG",
    "OPENROUTER_API_KEY_TRINH",
    "GROQ_API_KEY",
):
    os.environ[credential_name] = ""

from fastapi.testclient import TestClient

from app.apify_gateway import normalize_apify_item
from app.config import Settings
from app.main import app, database, rag
from app.rag_anything_gateway import (
    RAGAnythingResult,
    RAGAnythingSource,
)


client = TestClient(app)


def setup_function():
    client.post("/api/reset")


def test_frontend_origin_supports_local_and_vercel_deployments():
    configured = Settings(
        frontend_origin="http://localhost:3000, https://kute-demo.vercel.app"
    )
    assert configured.frontend_origins == [
        "http://localhost:3000",
        "https://kute-demo.vercel.app",
    ]


def test_public_admin_is_disabled_when_admin_key_is_not_configured():
    response = client.get(
        "/api/admin/overview",
        headers={"Host": "public-demo.example"},
    )
    assert response.status_code == 503


def test_health_and_discord_state_expose_hierarchy():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["memory_provider"] == "local-demo"

    response = client.get("/api/discord-state", params={"user_id": "U01862"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["team_id"] == "T004"
    assert {(scope["type"], scope["id"]) for scope in payload["scopes"]} == {
        ("user", "U01862"),
        ("team", "T004"),
        ("group", "G10"),
        ("room", "LEC-D302"),
        ("room", "LAB-D304"),
        ("cohort", "K4"),
    }
    assert "team-t009" not in {channel["id"] for channel in payload["channels"]}


def test_learner_profile_is_reused_by_student_id_last5(monkeypatch):
    saved_profiles = {}

    async def fake_upsert_learner_profile(**values):
        existing = next(
            (
                profile
                for profile in saved_profiles.values()
                if profile["student_id_last5"] == values["student_id_last5"]
            ),
            None,
        )
        timestamp = datetime.now(UTC)
        if existing:
            existing.update(
                full_name=values["full_name"],
                demo_user_id=values["demo_user_id"],
                updated_at=timestamp,
                last_seen_at=timestamp,
            )
            return existing
        profile = {
            **values,
            "created_at": timestamp,
            "updated_at": timestamp,
            "last_seen_at": timestamp,
        }
        saved_profiles[profile["profile_id"]] = profile
        return profile

    async def fake_get_learner_profile(profile_id):
        return saved_profiles.get(profile_id)

    monkeypatch.setattr(database, "upsert_learner_profile", fake_upsert_learner_profile)
    monkeypatch.setattr(database, "get_learner_profile", fake_get_learner_profile)

    first = client.post(
        "/api/learner-profiles",
        json={
            "full_name": "  Nguyễn   Văn An  ",
            "student_id_last5": "01862",
            "demo_user_id": "U01862",
        },
    )
    repeated = client.post(
        "/api/learner-profiles",
        json={
            "full_name": "Nguyễn Văn An",
            "student_id_last5": "01862",
            "demo_user_id": "U01862",
        },
    )

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json()["profile_id"] == first.json()["profile_id"]
    assert first.json()["full_name"] == "Nguyễn Văn An"

    restored = client.get(
        f"/api/learner-profiles/{first.json()['profile_id']}"
    )
    assert restored.status_code == 200
    assert restored.json()["student_id_last5"] == "01862"


def test_learner_profile_requires_exactly_five_digits():
    response = client.post(
        "/api/learner-profiles",
        json={
            "full_name": "Nguyễn Văn An",
            "student_id_last5": "1862",
            "demo_user_id": "U01862",
        },
    )
    assert response.status_code == 422


def test_profiled_chat_is_logged_without_blocking_the_answer(monkeypatch):
    captured = {}

    async def fake_get_learner_profile(profile_id):
        assert profile_id == "profile-test"
        return {"profile_id": profile_id}

    async def fake_log_chat_interaction(**values):
        captured.update(values)
        return True

    monkeypatch.setattr(database, "get_learner_profile", fake_get_learner_profile)
    monkeypatch.setattr(database, "log_chat_interaction", fake_log_chat_interaction)

    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "profile_id": "profile-test",
            "message": "Team mình còn blocker nào?",
            "channel_id": "bot-commands",
        },
    )

    assert response.status_code == 200
    assert captured["profile_id"] == "profile-test"
    assert captured["question"] == "Team mình còn blocker nào?"
    assert captured["answer"] == response.json()["message"]["content"]
    assert isinstance(captured["citations"], list)
    assert isinstance(captured["tool_calls"], list)


def test_admin_evaluation_exposes_submission_evidence():
    response = client.get("/api/admin/evaluation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] >= 20
    assert payload["observed_cases"] >= 10
    assert len(payload["risk_coverage"]) == 4
    assert all(item["count"] >= 2 for item in payload["risk_coverage"])
    assert payload["acceptance_threshold"]["locked"] is True
    assert payload["decision_statement"].startswith("AI đọc các kênh Discord")
    assert payload["model"] == "qwen/qwen3.6-27b"


def test_team_memory_and_messages_are_isolated():
    thai = client.get("/api/discord-state", params={"user_id": "U01862"}).json()
    lan = client.get("/api/discord-state", params={"user_id": "U09999"}).json()

    thai_memories = {memory["id"] for memory in thai["memories"]}
    lan_memories = {memory["id"] for memory in lan["memories"]}
    assert "mem-team-t004-stack" in thai_memories
    assert "mem-team-t009-private" not in thai_memories
    assert "mem-team-t009-private" in lan_memories
    assert "mem-team-t004-stack" not in lan_memories

    thai_channels = {message["channel_id"] for message in thai["discord_messages"]}
    lan_channels = {message["channel_id"] for message in lan["discord_messages"]}
    assert "team-t009" not in thai_channels
    assert "team-t004" not in lan_channels


def test_chat_summary_has_discord_citations():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Team mình đang chốt gì và còn blocker nào?",
            "channel_id": "bot-commands",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["message"]["citations"]) >= 2
    assert all(
        citation["channel_id"] == "team-t004"
        for citation in payload["message"]["citations"]
    )
    assert "T009" not in payload["message"]["content"]


def test_candidate_can_be_confirmed_only_by_creator_scope():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Team mình chốt demo scope memory trước 18h.",
            "channel_id": "team-t004",
        },
    )
    assert response.status_code == 200
    candidate = response.json()["candidate"]
    assert candidate["scope_type"] == "team"
    assert candidate["scope_id"] == "T004"

    forbidden = client.post(
        f"/api/memory-candidates/{candidate['id']}/confirm",
        params={"user_id": "U09999"},
    )
    assert forbidden.status_code == 403

    confirmed = client.post(
        f"/api/memory-candidates/{candidate['id']}/confirm",
        params={"user_id": "U01862"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["scope_id"] == "T004"


def test_apify_item_normalizer_fails_closed_for_unknown_channel():
    item = {
        "messageId": "123",
        "channelId": "dc-team-t004",
        "author": {"id": "discord-01862", "username": "an"},
        "content": "Team chốt API contract.",
        "timestamp": "2026-07-30T08:00:00Z",
        "url": "https://discord.com/channels/demo/dc-team-t004/123",
    }
    normalized = normalize_apify_item(item)
    assert normalized is not None
    assert normalized.channel_id == "team-t004"
    assert normalized.author_id == "U01862"

    item["channelId"] = "private-unknown-channel"
    assert normalize_apify_item(item) is None


def test_ingest_endpoint_requires_configured_dataset():
    response = client.post("/api/ingest/apify", json={"max_items": 20})
    assert response.status_code == 409


def test_catchup_returns_actionable_categories_with_citations():
    response = client.post(
        "/api/catch-up",
        json={"user_id": "U01862", "window_hours": 24},
    )
    assert response.status_code == 200
    brief = response.json()
    kinds = {item["kind"] for item in brief["items"]}
    assert {"decision", "task", "blocker"}.issubset(kinds)
    assert all(item["citations"] for item in brief["items"])
    assert all(
        citation["channel_id"] != "team-t009"
        for item in brief["items"]
        for citation in item["citations"]
    )
    content = " ".join(item["detail"] for item in brief["items"])
    assert "API ingest" in content
    assert "Lab-D304" in content


def test_catchup_can_create_and_complete_checklist_then_acknowledge():
    brief = client.post(
        "/api/catch-up",
        json={"user_id": "U01862", "window_hours": 24},
    ).json()
    checklist_response = client.post(
        f"/api/catch-up/{brief['id']}/checklist",
        params={"user_id": "U01862"},
    )
    assert checklist_response.status_code == 200
    checklist = checklist_response.json()
    assert checklist
    assert any("API ingest" in item["text"] for item in checklist)

    item = checklist[0]
    completed = client.patch(
        f"/api/checklist/{item['id']}",
        params={"user_id": "U01862"},
        json={"completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    acknowledged = client.post(
        f"/api/catch-up/{brief['id']}/acknowledge",
        params={"user_id": "U01862"},
    )
    assert acknowledged.status_code == 204
    refreshed = client.post(
        "/api/catch-up",
        json={"user_id": "U01862", "window_hours": 24},
    ).json()
    assert refreshed["acknowledged"] is True


def test_rag_query_and_chat_use_server_authorized_sources(monkeypatch):
    result = RAGAnythingResult(
        answer=(
            "GitHub invite đang ở hàng đợi. "
            "[SOURCE_ID=painpoint-0039|TYPE=painpoint|CHANNEL=qa]"
        ),
        sources=[
            RAGAnythingSource(
                source_id="painpoint-0039",
                source_type="painpoint",
                channel_key="qa",
                label="painpoint:painpoint-0039",
            )
        ],
        scopes_queried=["cohort:K4"],
        provider="HKUDS/RAG-Anything@test",
    )

    async def fake_query(user, query):
        assert user.id == "U01862"
        assert query
        return result

    monkeypatch.setattr(rag, "query", fake_query)
    response = client.post(
        "/api/rag/query",
        json={"user_id": "U01862", "query": "GitHub invite bị gì?"},
    )
    assert response.status_code == 200
    assert response.json()["scopes_queried"] == ["cohort:K4"]
    assert response.json()["sources"][0]["source_id"] == "painpoint-0039"

    chat_response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "GitHub invite bị gì?",
            "channel_id": "bot-commands",
        },
    )
    assert chat_response.status_code == 200
    chat_payload = chat_response.json()
    assert chat_payload["provider"] == "HKUDS/RAG-Anything@test"
    assert "SOURCE_ID" not in chat_payload["message"]["content"]
    assert chat_payload["message"]["citations"][0]["channel_id"] == "qa"


def test_rag_source_is_redacted_and_scope_guarded(monkeypatch):
    async def fake_source(source_type, source_id):
        return {
            "source_id": source_id,
            "source_type": source_type,
            "channel_key": "team-t004",
            "scope_key": "team:T004",
            "content": "Liên hệ [REDACTED_EMAIL].",
            "created_at": None,
            "metadata": {"source_row": 42},
        }

    monkeypatch.setattr(database, "source", fake_source)
    allowed = client.get(
        "/api/rag/sources/message/team-message-1",
        params={"user_id": "U01862"},
    )
    assert allowed.status_code == 200
    assert "[REDACTED_EMAIL]" in allowed.json()["content"]
    assert "content_original" not in allowed.text

    forbidden = client.get(
        "/api/rag/sources/message/team-message-1",
        params={"user_id": "U09999"},
    )
    assert forbidden.status_code == 403


def test_admin_can_create_update_and_delete_confirmed_memory():
    created = client.post(
        "/api/admin/memories",
        json={
            "scope_type": "team",
            "scope_id": "T004",
            "kind": "decision",
            "content": "Team chốt dùng local lecture retrieval.",
            "evidence": ["T06-001"],
            "created_by": "admin-test",
        },
    )
    assert created.status_code == 200
    memory_id = created.json()["id"]

    listed = client.get("/api/admin/memories")
    assert listed.status_code == 200
    assert memory_id in {memory["id"] for memory in listed.json()}

    updated = client.patch(
        f"/api/admin/memories/{memory_id}",
        json={"content": "Team chốt dùng PostgreSQL local lecture retrieval."},
    )
    assert updated.status_code == 200
    assert "PostgreSQL" in updated.json()["content"]

    deleted = client.delete(f"/api/admin/memories/{memory_id}")
    assert deleted.status_code == 204


def test_admin_tool_inspector_exposes_server_computed_plan():
    response = client.post(
        "/api/admin/context/plan",
        json={
            "user_id": "U01862",
            "query": "Giảng viên giải thích Transformer và attention như thế nào?",
            "channel_id": "bot-commands",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["lesson_intent"] is True
    assert payload["filters"]["day_codes"] == ["transformer-attention"]
    calls = {call["name"] for call in payload["tool_calls"]}
    assert "get_current_datetime" in calls
    assert "search_learning_context" in calls
    assert "inspect_context_date_range" in calls
    assert "recall_confirmed_memory" in calls
