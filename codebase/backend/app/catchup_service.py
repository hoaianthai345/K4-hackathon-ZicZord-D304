from datetime import UTC, datetime, timedelta
import hashlib
import re

from .schemas import (
    CatchupBrief,
    CatchupItem,
    ChecklistItem,
    Citation,
    CommunityUser,
    DiscordMessage,
)
from .scopes import can_access_channel, channel_record
from .store import JsonStore


DECISION_RE = re.compile(r"\b(?:chốt|quyết định|thống nhất|chọn|dùng|ưu tiên)\b", re.I)
TASK_RE = re.compile(
    r"\b(?:phụ trách|cần|nhớ|chuẩn bị|hoàn thiện|làm|đẩy repo|setup|giữ backend|yêu cầu)\b",
    re.I,
)
BLOCKER_RE = re.compile(
    r"\b(?:blocker|đang bị kẹt|chưa map|chưa có|không nhận|không vào|lỗi|vướng|kẹt|invalid)\b",
    re.I,
)
RESOLVED_RE = re.compile(r"\b(?:đã xử lý|đã xong|resolved|ổn rồi|fix xong)\b", re.I)
OWNER_RE = re.compile(
    r"\b(An|Dũng|Phong|Châu|Lan|mentor|team)\s+(?:phụ trách|làm|giữ|chuẩn bị|cần)",
    re.I,
)
TIME_RE = re.compile(
    r"(?:\b\d{1,2}h(?:\d{2})?\b(?:\s*hôm nay)?|trước\s+(?:buổi\s+)?[^.,;]+|"
    r"\bthứ\s+(?:hai|ba|tư|năm|sáu|bảy|2|3|4|5|6|7)\b)",
    re.I,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _key(*values: str) -> str:
    joined = "|".join(values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


class CatchupService:
    def __init__(self, store: JsonStore):
        self.store = store

    @staticmethod
    def _citation(message: DiscordMessage) -> Citation:
        channel = channel_record(message.channel_id)
        channel_name = channel.name if channel else message.channel_id
        return Citation(
            message_id=message.id,
            channel_id=message.channel_id,
            channel_name=channel_name,
            label=f"#{channel_name} · {message.author_name}",
            permalink=message.permalink,
        )

    def _visible_messages(
        self,
        user: CommunityUser,
        window_hours: int,
    ) -> list[DiscordMessage]:
        cutoff = _now() - timedelta(hours=window_hours)
        visible: list[DiscordMessage] = []
        for raw in self.store.snapshot()["discord_messages"]:
            message = DiscordMessage.model_validate(raw)
            channel = channel_record(message.channel_id)
            if (
                channel
                and can_access_channel(user, channel)
                and message.created_at >= cutoff
            ):
                visible.append(message)
        return sorted(visible, key=lambda item: item.created_at, reverse=True)

    @staticmethod
    def _kind(message: DiscordMessage) -> str | None:
        channel = channel_record(message.channel_id)
        content = message.content
        if BLOCKER_RE.search(content):
            return "blocker"
        if channel and channel.kind == "announcement":
            return "announcement"
        if DECISION_RE.search(content):
            return "decision"
        if TASK_RE.search(content):
            return "task"
        return None

    @staticmethod
    def _owner(content: str, author_name: str) -> str | None:
        match = OWNER_RE.search(content)
        if match:
            value = match.group(1)
            return value[0].upper() + value[1:]
        if "mình sẽ" in content.casefold():
            return author_name.split("-")[-2] if "-" in author_name else author_name
        return None

    @staticmethod
    def _deadline(content: str) -> str | None:
        match = TIME_RE.search(content)
        return match.group(0).strip().rstrip(".") if match else None

    @staticmethod
    def _title(content: str) -> str:
        cleaned = content.strip().rstrip(".")
        return cleaned[:116] + ("…" if len(cleaned) > 116 else "")

    def generate(self, user: CommunityUser, window_hours: int = 24) -> CatchupBrief:
        messages = self._visible_messages(user, window_hours)
        items: list[CatchupItem] = []
        seen: set[tuple[str, str]] = set()
        limits = {"decision": 2, "task": 3, "blocker": 2, "announcement": 2}
        counts: dict[str, int] = {key: 0 for key in limits}

        for message in messages:
            kind = self._kind(message)
            if not kind or counts[kind] >= limits[kind]:
                continue
            normalized = re.sub(r"\s+", " ", message.content.casefold()).strip()
            dedupe_key = (kind, normalized)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            counts[kind] += 1
            status = "resolved" if RESOLVED_RE.search(message.content) else "open"
            items.append(
                CatchupItem(
                    id=f"brief-item-{_key(user.id, message.id, kind)}",
                    kind=kind,
                    title=self._title(message.content),
                    detail=message.content,
                    owner=self._owner(message.content, message.author_name),
                    deadline=self._deadline(message.content),
                    status=status,
                    citations=[self._citation(message)],
                )
            )

        order = {"decision": 0, "task": 1, "blocker": 2, "announcement": 3}
        items.sort(key=lambda item: (order[item.kind], item.status == "resolved"))
        source_ids = {citation.message_id for item in items for citation in item.citations}
        channel_ids = {citation.channel_id for item in items for citation in item.citations}
        brief_id = f"brief-{_key(user.id, str(window_hours), *sorted(source_ids))}"
        acknowledged = brief_id in self.store.snapshot()["acknowledged_briefs"].get(user.id, [])
        summary_parts = [
            f"{counts['decision']} quyết định",
            f"{counts['task']} việc cần làm",
            f"{counts['blocker']} blocker",
            f"{counts['announcement']} thông báo",
        ]
        brief = CatchupBrief(
            id=brief_id,
            user_id=user.id,
            window_hours=window_hours,
            generated_at=_now(),
            source_message_count=len(source_ids),
            channel_count=len(channel_ids),
            summary=" · ".join(summary_parts),
            items=items,
            acknowledged=acknowledged,
        )

        def operation(state: dict):
            history = state["catchup_briefs"].setdefault(user.id, [])
            history[:] = [item for item in history if item["id"] != brief.id]
            history.insert(0, brief.model_dump(mode="json"))
            del history[5:]
            return True

        self.store.mutate(operation)
        return brief

    def acknowledge(self, brief_id: str, user: CommunityUser) -> None:
        def operation(state: dict):
            history = state["catchup_briefs"].get(user.id, [])
            if not any(item["id"] == brief_id for item in history):
                raise KeyError(brief_id)
            values = state["acknowledged_briefs"].setdefault(user.id, [])
            if brief_id not in values:
                values.append(brief_id)
            return True

        self.store.mutate(operation)

    def create_checklist(self, brief_id: str, user: CommunityUser) -> list[ChecklistItem]:
        created: list[dict] = []

        def operation(state: dict):
            brief = next(
                (item for item in state["catchup_briefs"].get(user.id, []) if item["id"] == brief_id),
                None,
            )
            if not brief:
                raise KeyError(brief_id)
            current = state["checklists"].setdefault(user.id, [])
            existing_sources = {item["source_item_id"] for item in current}
            for source in brief["items"]:
                actionable = source["kind"] in {"task", "blocker"} or bool(source.get("deadline"))
                if not actionable or source["id"] in existing_sources:
                    continue
                item = ChecklistItem(
                    id=f"check-{_key(user.id, source['id'])}",
                    user_id=user.id,
                    source_brief_id=brief_id,
                    source_item_id=source["id"],
                    text=source["title"],
                    owner=source.get("owner"),
                    deadline=source.get("deadline"),
                    created_at=_now(),
                )
                current.append(item.model_dump(mode="json"))
            created.extend(current)
            return current

        self.store.mutate(operation)
        return [ChecklistItem.model_validate(item) for item in created]

    def update_checklist(
        self,
        item_id: str,
        completed: bool,
        user: CommunityUser,
    ) -> ChecklistItem:
        updated: dict = {}

        def operation(state: dict):
            item = next(
                (value for value in state["checklists"].get(user.id, []) if value["id"] == item_id),
                None,
            )
            if not item:
                raise KeyError(item_id)
            item["completed"] = completed
            updated.update(item)
            return item

        self.store.mutate(operation)
        return ChecklistItem.model_validate(updated)
