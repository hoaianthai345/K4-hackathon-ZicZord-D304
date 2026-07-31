from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
import re
import unicodedata
from zoneinfo import ZoneInfo

from .database import Database
from .schemas import CommunityUser
from .scopes import allowed_scope_keys


VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
TIME_PATTERNS = (
    "hôm nay",
    "hom nay",
    "hôm qua",
    "hom qua",
    "giờ qua",
    "gio qua",
    "ngày qua",
    "ngay qua",
)
LESSON_TERMS = (
    "bài học",
    "bài giảng",
    "lý thuyết",
    "lecture",
    "transcript",
    "slide",
    "foundation",
    "transformer",
    "attention",
    "llm",
    "human-centered",
    "double diamond",
    "viên kim cương",
    "product manager",
    "problem statement",
    "xác định bài toán",
    "tự động hoá",
    "tự động hóa",
    "workshop",
    "coaching",
    "hackathon",
    "mini hackathon",
    "cuộc thi",
    "the le",
    "thể lệ",
    "rubric",
    "checkpoint",
)
PROBLEM_TERMS = (
    "vì sao",
    "nguyên nhân",
    "pain point",
    "lỗi",
    "không nhận",
    "không thấy",
    "cách xử lý",
    "bao nhiêu người",
)


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


@dataclass
class ToolCall:
    name: str
    arguments: dict
    reason: str
    result_count: int = 0


@dataclass
class ContextPlan:
    query: str
    normalized_query: str
    channel_keys: list[str] = field(default_factory=list)
    day_codes: list[str] = field(default_factory=list)
    source_kinds: list[str] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    time_label: str | None = None
    lesson_intent: bool = False
    strict_discord_filter: bool = False
    use_rag: bool = False
    use_memory: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass
class ContextRetrieval:
    plan: ContextPlan
    calls: list[ToolCall]
    sources: list[dict]
    temporal_context: dict = field(default_factory=dict)

    @property
    def should_answer_directly(self) -> bool:
        return bool(self.sources) and (
            self.plan.lesson_intent or self.plan.strict_discord_filter
        )


class ContextToolService:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _time_window(query: str, now: datetime) -> tuple[datetime | None, datetime | None, str | None]:
        value = normalize(query)
        local_now = now.astimezone(VIETNAM_TZ)
        if "hom nay" in value:
            start_local = datetime.combine(local_now.date(), time.min, VIETNAM_TZ)
            return start_local.astimezone(UTC), None, "hôm nay"
        if "hom qua" in value:
            day = local_now.date() - timedelta(days=1)
            start_local = datetime.combine(day, time.min, VIETNAM_TZ)
            end_local = start_local + timedelta(days=1)
            return start_local.astimezone(UTC), end_local.astimezone(UTC), "hôm qua"
        hour_match = re.search(r"\b(\d{1,3})\s*(?:gio|h)\s*qua\b", value)
        if hour_match:
            hours = min(max(int(hour_match.group(1)), 1), 168)
            return now - timedelta(hours=hours), None, f"{hours} giờ qua"
        day_match = re.search(r"\b(\d{1,2})\s*ngay\s*qua\b", value)
        if day_match:
            days = min(max(int(day_match.group(1)), 1), 30)
            return now - timedelta(days=days), None, f"{days} ngày qua"
        date_match = re.search(
            r"\b(?:ngay\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",
            value,
        )
        if date_match:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            raw_year = date_match.group(3)
            year = int(raw_year) if raw_year else local_now.year
            if year < 100:
                year += 2000
            try:
                start_local = datetime(year, month, day, tzinfo=VIETNAM_TZ)
            except ValueError:
                return None, None, None
            return (
                start_local.astimezone(UTC),
                (start_local + timedelta(days=1)).astimezone(UTC),
                f"ngày {day:02d}/{month:02d}/{year}",
            )
        return None, None, None

    @staticmethod
    def _as_local(value: datetime | None) -> str | None:
        if value is None:
            return None
        timestamp = value if value.tzinfo else value.replace(tzinfo=UTC)
        return timestamp.astimezone(VIETNAM_TZ).isoformat()

    @classmethod
    def _temporal_context(
        cls,
        plan: ContextPlan,
        moment: datetime,
        sources: list[dict],
    ) -> dict:
        local_now = moment.astimezone(VIETNAM_TZ)
        dated_sources: list[datetime] = []
        for source in sources:
            created_at = source.get("created_at")
            if isinstance(created_at, datetime):
                dated_sources.append(
                    created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
                )
        requested_start_local = cls._as_local(plan.start_time)
        requested_end_local = cls._as_local(plan.end_time)
        requested_date = (
            plan.start_time.astimezone(VIETNAM_TZ).date().isoformat()
            if plan.start_time
            else None
        )
        return {
            "timezone": str(VIETNAM_TZ),
            "current_datetime": local_now.isoformat(),
            "current_date": local_now.date().isoformat(),
            "requested_label": plan.time_label,
            "requested_date": requested_date,
            "requested_start": requested_start_local,
            "requested_end": requested_end_local,
            "context_start": cls._as_local(min(dated_sources)) if dated_sources else None,
            "context_end": cls._as_local(max(dated_sources)) if dated_sources else None,
            "dated_source_count": len(dated_sources),
            "undated_source_count": len(sources) - len(dated_sources),
        }

    @staticmethod
    def _channels(query: str, current_channel: str) -> list[str]:
        value = normalize(query)
        channels: list[str] = []
        aliases = {
            "qa": ("hoi dap", "kenh qa", "#qa"),
            "common": ("chat chinh", "kenh chung", "cong dong", "#chung"),
            "bot-commands": ("bot command", "go commands", "kenh bot"),
            "lecture": ("bai giang", "ly thuyet", "lecture", "lec-"),
            "lab": ("thuc hanh", "lab-", "phong lab"),
            "team": ("team minh", "nhom minh", "t004", "t009"),
            "group": ("mentor", "group g10", "nhom g10"),
        }
        for channel, terms in aliases.items():
            if any(term in value for term in terms):
                channels.append(channel)
        if any(term in value for term in ("kenh nay", "channel nay")):
            channels.append(current_channel)
        return list(dict.fromkeys(channels))

    @staticmethod
    def _day_codes(query: str) -> list[str]:
        value = normalize(query)
        values: list[str] = []
        if any(term in value for term in ("day 1", "ngay 1", "foundation", "llm hoat dong")):
            values.extend(["day01-llm-foundation", "transformer-attention"])
        if any(term in value for term in ("day 2", "ngay 2", "xac dinh bai toan")):
            values.extend(
                [
                    "day02-problem-framing",
                    "day02-success-automation",
                    "day02-team-review",
                ]
            )
        if any(term in value for term in ("transformer", "attention")):
            values.append("transformer-attention")
        if any(term in value for term in ("danh gia", "du lieu")):
            values.append("problem-evaluation-data")
        if any(term in value for term in ("hackathon", "mini hackathon", "cuoc thi", "the le", "rubric")):
            values.append("mini-hackathon-2026")
        return list(dict.fromkeys(values))

    @staticmethod
    def _source_kinds(query: str) -> list[str]:
        value = normalize(query)
        if any(term in value for term in ("workshop", "coaching")):
            return ["event_brief", "workshop_transcript"]
        if any(term in value for term in ("hackathon", "mini hackathon", "cuoc thi", "the le", "rubric")):
            return ["competition_rule"]
        if "slide" in value:
            return ["slide"]
        if "transcript" in value or "giang vien noi" in value:
            return ["transcript"]
        if any(term in value for term in ("tutor", "hoc vien tung hoi", "hoi dap bai hoc")):
            return ["tutor_qa"]
        return []

    @staticmethod
    def _search_query(query: str) -> str:
        value = query
        removable = (
            *TIME_PATTERNS,
            "kênh này",
            "channel này",
            "kênh hỏi đáp",
            "kenh hoi dap",
            "kênh chung",
            "kenh chung",
            "chat chính",
            "chat chinh",
            "giảng viên",
            "giang vien",
            "giải thích",
            "giai thich",
            "như thế nào",
            "nhu the nao",
            "tóm tắt",
            "bắt kịp",
            "bat kip",
            "cho mình",
            "giúp mình",
        )
        for phrase in removable:
            value = re.sub(re.escape(phrase), " ", value, flags=re.IGNORECASE)
        value = re.sub(
            r"\b(?:ngày|ngay)?\s*\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
            " ",
            value,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", value).strip()

    def plan(
        self,
        user: CommunityUser,
        query: str,
        current_channel: str,
        *,
        now: datetime | None = None,
    ) -> ContextPlan:
        moment = now or datetime.now(UTC)
        normalized_query = normalize(query)
        start_time, end_time, time_label = self._time_window(query, moment)
        channel_keys = self._channels(query, current_channel)
        channel_keys = [
            (
                f"team-{user.team_id.casefold()}"
                if channel == "team" and user.team_id
                else f"group-{user.group_id.casefold()}"
                if channel == "group"
                else f"lecture-{user.lecture_room_id.split('-', 1)[-1].casefold()}"
                if channel == "lecture" and user.lecture_room_id
                else f"lab-{user.lab_room_id.split('-', 1)[-1].casefold()}"
                if channel == "lab" and user.lab_room_id
                else channel
            )
            for channel in channel_keys
        ]
        lesson_intent = any(normalize(term) in normalized_query for term in LESSON_TERMS)
        explicit_channel = bool(channel_keys)
        strict_filter = bool(start_time or explicit_channel)
        day_codes = self._day_codes(query)
        if "workshop" in normalized_query and start_time:
            workshop_date = start_time.astimezone(VIETNAM_TZ).date().isoformat()
            day_codes.append(f"workshop-{workshop_date}")
            day_codes = list(dict.fromkeys(day_codes))
        source_kinds = self._source_kinds(query)
        use_rag = any(normalize(term) in normalized_query for term in PROBLEM_TERMS)
        if lesson_intent:
            use_rag = False
        notes: list[str] = []
        official_event_intent = any(
            kind in {"event_brief", "workshop_transcript", "competition_rule"}
            for kind in source_kinds
        )
        if lesson_intent and time_label and not official_event_intent:
            notes.append(
                "Transcript và slide không có timestamp lịch học. Time window chỉ áp dụng "
                "cho Discord hoặc tutor Q&A có thời gian; day_code được ưu tiên nếu câu hỏi nêu rõ."
            )
        return ContextPlan(
            query=query,
            normalized_query=self._search_query(query),
            channel_keys=channel_keys,
            day_codes=day_codes,
            source_kinds=source_kinds,
            start_time=start_time,
            end_time=end_time,
            time_label=time_label,
            lesson_intent=lesson_intent,
            strict_discord_filter=strict_filter,
            use_rag=False if lesson_intent else (use_rag or not strict_filter),
            use_memory=True,
            notes=notes,
        )

    async def retrieve(
        self,
        user: CommunityUser,
        query: str,
        current_channel: str,
        *,
        now: datetime | None = None,
    ) -> ContextRetrieval:
        moment = now or datetime.now(UTC)
        plan = self.plan(user, query, current_channel, now=moment)
        scopes = sorted(
            f"{scope_type}:{scope_id}"
            for scope_type, scope_id in allowed_scope_keys(user)
        )
        local_now = moment.astimezone(VIETNAM_TZ)
        calls: list[ToolCall] = [
            ToolCall(
                name="get_current_datetime",
                arguments={
                    "timezone": str(VIETNAM_TZ),
                    "current_datetime": local_now.isoformat(),
                    "current_date": local_now.date().isoformat(),
                },
                reason="Neo các cụm thời gian tương đối vào ngày hiện tại theo giờ Việt Nam.",
                result_count=1,
            )
        ]
        sources: list[dict] = []

        if plan.lesson_intent:
            lesson_call = ToolCall(
                name="search_learning_context",
                arguments={
                    "query": plan.normalized_query,
                    "scope_keys": scopes,
                    "day_codes": plan.day_codes or None,
                    "source_kinds": plan.source_kinds or None,
                    "limit": 6,
                },
                reason="Câu hỏi nhắc nội dung bài học, transcript, slide hoặc khái niệm lớp.",
            )
            lesson_sources = await self.database.search_learning(
                plan.normalized_query,
                scopes,
                day_codes=plan.day_codes or None,
                source_kinds=plan.source_kinds or None,
                limit=6,
            )
            lesson_call.result_count = len(lesson_sources)
            calls.append(lesson_call)
            sources.extend(lesson_sources)

        discord_channels = plan.channel_keys
        only_lesson_channel = (
            plan.lesson_intent
            and discord_channels
            and all(channel.startswith("lecture-") for channel in discord_channels)
        )
        official_event_intent = any(
            kind in {"event_brief", "workshop_transcript", "competition_rule"}
            for kind in plan.source_kinds
        )
        if (
            plan.strict_discord_filter
            and not only_lesson_channel
            and not official_event_intent
        ):
            discord_call = ToolCall(
                name="search_discord_messages",
                arguments={
                    "query": plan.normalized_query,
                    "scope_keys": scopes,
                    "channel_keys": discord_channels or None,
                    "start_time": plan.start_time.isoformat() if plan.start_time else None,
                    "end_time": plan.end_time.isoformat() if plan.end_time else None,
                    "limit": 8,
                },
                reason="Câu hỏi có time window hoặc chỉ rõ channel cần đọc.",
            )
            discord_sources = await self.database.search_messages(
                plan.normalized_query,
                scopes,
                channel_keys=discord_channels or None,
                start_time=plan.start_time,
                end_time=plan.end_time,
                limit=8,
            )
            discord_call.result_count = len(discord_sources)
            calls.append(discord_call)
            sources.extend(discord_sources)

        calls.append(
            ToolCall(
                name="recall_confirmed_memory",
                arguments={"scope_keys": scopes, "query": plan.normalized_query},
                reason="Memory chỉ được recall trong scope server cấp cho user.",
            )
        )
        if plan.use_rag and not plan.lesson_intent:
            calls.append(
                ToolCall(
                    name="rag_anything_hybrid_search",
                    arguments={"scope_keys": scopes, "query": plan.normalized_query},
                    reason="Không có bộ lọc thời gian/kênh chặt hoặc câu hỏi cần semantic pain point.",
                )
            )

        deduplicated: list[dict] = []
        seen: set[str] = set()
        for source in sources:
            source_id = str(source["source_id"])
            if source_id in seen:
                continue
            seen.add(source_id)
            deduplicated.append(source)
        selected_sources = deduplicated[:8]
        temporal_context = self._temporal_context(plan, moment, selected_sources)
        calls.append(
            ToolCall(
                name="inspect_context_date_range",
                arguments=temporal_context,
                reason=(
                    "Đối chiếu ngày của context đã lấy với khoảng thời gian người dùng hỏi."
                ),
                result_count=temporal_context["dated_source_count"],
            )
        )
        return ContextRetrieval(
            plan=plan,
            calls=calls,
            sources=selected_sources,
            temporal_context=temporal_context,
        )
