from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .hindsight_gateway import HindsightGateway
from .llm_gateway import LLMGateway
from .schemas import (
    AssistantMessage,
    ChatResponse,
    Citation,
    CommunityUser,
    DiscordMessage,
    Memory,
    MemoryCandidate,
)
from .scopes import (
    allowed_scope_keys,
    can_access_channel,
    can_write_scope,
    channel_record,
)
from .store import JsonStore


def now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return now().isoformat()


def _normal(value: str) -> str:
    return value.casefold().replace("đ", "d")


class ChatService:
    def __init__(
        self,
        store: JsonStore,
        hindsight: HindsightGateway,
        llm: LLMGateway,
    ):
        self.store = store
        self.hindsight = hindsight
        self.llm = llm

    def _visible_memories(self, user: CommunityUser) -> list[Memory]:
        allowed = allowed_scope_keys(user)
        snapshot = self.store.snapshot()
        return [
            Memory.model_validate(memory)
            for memory in snapshot["memories"]
            if (memory["scope_type"], memory["scope_id"]) in allowed
        ]

    def _visible_discord_messages(self, user: CommunityUser) -> list[DiscordMessage]:
        values: list[DiscordMessage] = []
        for raw in self.store.snapshot()["discord_messages"]:
            channel = channel_record(raw["channel_id"])
            if channel and can_access_channel(user, channel):
                values.append(DiscordMessage.model_validate(raw))
        return sorted(values, key=lambda value: value.created_at, reverse=True)

    @staticmethod
    def _intent(query: str) -> str:
        lowered = _normal(query)
        if any(
            term in lowered
            for term in [
                "bai giang",
                "bài giảng",
                "ly thuyet",
                "lý thuyết",
                "lecture",
                "lec-",
            ]
        ):
            return "lecture"
        if any(term in lowered for term in ["mentor", "g10", "group"]):
            return "group"
        if any(term in lowered for term in ["team", "t004", "nhom minh", "blocker", "repo"]):
            return "team"
        if any(term in lowered for term in ["lab", "thuc hanh", "thực hành"]):
            return "lab"
        if any(
            term in lowered
            for term in [
                "chat chinh",
                "chat chính",
                "cong dong",
                "cộng đồng",
                "hom nay",
                "hôm nay",
                "kenh chung",
                "kênh chung",
            ]
        ):
            return "common"
        return "all"

    @staticmethod
    def _message_matches_intent(
        message: DiscordMessage,
        user: CommunityUser,
        intent: str,
    ) -> bool:
        channel = channel_record(message.channel_id)
        if not channel:
            return False
        if intent == "lecture":
            return channel.kind == "lecture" and channel.scope_id == user.lecture_room_id
        if intent == "lab":
            return channel.kind == "lab" and channel.scope_id == user.lab_room_id
        if intent == "team":
            return channel.kind == "team" and channel.scope_id == user.team_id
        if intent == "group":
            return channel.kind == "group" and channel.scope_id == user.group_id
        if intent == "common":
            return channel.id in {"general", "announcements", "qa", "sharing"}
        return True

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        ignored = {
            "cho",
            "minh",
            "mình",
            "toi",
            "tôi",
            "nhung",
            "những",
            "dang",
            "đang",
            "cua",
            "của",
            "voi",
            "với",
            "tom",
            "tat",
            "tóm",
            "tắt",
            "gi",
            "gì",
        }
        return {
            token.strip(".,?!:;()[]").casefold()
            for token in query.split()
            if len(token.strip(".,?!:;()[]")) > 2
            and token.strip(".,?!:;()[]").casefold() not in ignored
        }

    def _evidence_for(
        self,
        user: CommunityUser,
        query: str,
    ) -> list[DiscordMessage]:
        intent = self._intent(query)
        values = [
            value
            for value in self._visible_discord_messages(user)
            if self._message_matches_intent(value, user, intent)
        ]
        lowered = _normal(query)
        today = now().date()
        if "hom qua" in lowered or "hôm qua" in lowered:
            yesterday = today - timedelta(days=1)
            dated = [value for value in values if value.created_at.date() == yesterday]
            if dated:
                values = dated
        elif "hom nay" in lowered or "hôm nay" in lowered:
            dated = [value for value in values if value.created_at.date() == today]
            if dated:
                values = dated

        terms = self._query_terms(query)

        def score(message: DiscordMessage) -> tuple[int, datetime]:
            matches = sum(term in message.content.casefold() for term in terms)
            return matches, message.created_at

        return sorted(values, key=score, reverse=True)[:4]

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

    @staticmethod
    def _scope_label(memory: Memory) -> str:
        labels = {
            "user": "Cá nhân",
            "team": f"Team {memory.scope_id}",
            "group": f"Group {memory.scope_id}",
            "room": memory.scope_id.replace("LEC", "Lec").replace("LAB", "Lab"),
            "cohort": f"Cộng đồng {memory.scope_id}",
        }
        return labels[memory.scope_type]

    def _compose_answer(
        self,
        user: CommunityUser,
        query: str,
        evidence: list[DiscordMessage],
        memories: list[Memory],
        external_memories: list[str],
    ) -> str:
        intent = self._intent(query)
        relevant_memory = [
            memory
            for memory in memories
            if (
                intent == "all"
                or (intent == "team" and memory.scope_type == "team")
                or (intent == "group" and memory.scope_type == "group")
                or (intent in {"lecture", "lab"} and memory.scope_type == "room")
                or (intent == "common" and memory.scope_type == "cohort")
            )
        ][:3]

        titles = {
            "lecture": "Tóm tắt bài giảng của phòng Lec-D302",
            "lab": "Tóm tắt phòng thực hành Lab-D304",
            "team": "T004 đang tập trung vào ba điểm",
            "group": "Mentor G10 đang nhắc hai việc",
            "common": "Điểm chính từ các kênh cộng đồng",
            "all": "Ngữ cảnh liên quan nhất mình tìm thấy",
        }
        lines: list[str] = []
        for message in evidence[:3]:
            content = message.content.rstrip(".")
            lines.append(f"• {content}.")

        if not lines and relevant_memory:
            lines.extend(f"• {memory.content.rstrip('.')}." for memory in relevant_memory)
        if not lines:
            return (
                "Mình chưa tìm thấy tin nhắn nào trong các channel bạn được phép xem. "
                "Bạn có thể hỏi rõ team, group mentor, phòng học hoặc kênh chung."
            )

        memory_note = ""
        if relevant_memory:
            memory = relevant_memory[0]
            memory_note = (
                f"\n\nMemory đã xác nhận dùng để nối ngữ cảnh: "
                f"[{self._scope_label(memory)}] {memory.content}"
            )
        elif external_memories:
            memory_note = f"\n\nHindsight recall: {external_memories[0]}"

        safety = (
            f"\n\nMình chỉ đọc {len(allowed_scope_keys(user))} scope mà tài khoản "
            f"{user.name} được tham gia; dữ liệu team khác không đi vào câu trả lời."
        )
        return f"{titles[intent]}:\n" + "\n".join(lines) + memory_note + safety

    @staticmethod
    def _candidate_for(
        user: CommunityUser,
        message_id: str,
        query: str,
        channel_id: str,
    ) -> MemoryCandidate | None:
        lowered = _normal(query)
        if "?" in query:
            return None

        kind: str | None = None
        if any(
            term in lowered
            for term in [
                "team minh chot",
                "team mình chốt",
                "nhom minh chot",
                "nhóm mình chốt",
                "quyet dinh dung",
                "quyết dịnh dùng",
                "quyết định dùng",
            ]
        ):
            kind = "decision"
        elif any(
            term in lowered
            for term in ["minh se", "mình sẽ", "phu trach", "phụ trách", "deadline", "can xong"]
        ):
            kind = "task"
        elif any(
            term in lowered
            for term in ["blocker", "dang bi ket", "đang bị kẹt", "chua co token", "chưa có token"]
        ):
            kind = "blocker"
        elif any(
            term in lowered
            for term in [
                "minh thich",
                "mình thích",
                "toi thich",
                "tôi thích",
                "hay tom tat cho minh",
                "hãy tóm tắt cho mình",
            ]
        ):
            kind = "preference"
        if not kind:
            return None

        channel = channel_record(channel_id)
        scope_type = "user"
        scope_id = user.id
        if channel and channel.scope_type in {"team", "group", "room"}:
            scope_type = channel.scope_type
            scope_id = channel.scope_id
        elif any(term in lowered for term in ["team", "nhom"]):
            scope_type = "team"
            scope_id = user.team_id or user.id

        if not can_write_scope(user, scope_type, scope_id):
            scope_type = "user"
            scope_id = user.id

        return MemoryCandidate(
            id=f"candidate-{uuid4().hex[:10]}",
            scope_type=scope_type,
            scope_id=scope_id,
            kind=kind,
            content=query.strip().rstrip(".") + ".",
            evidence=[message_id],
            created_by=user.id,
            created_at=now(),
        )

    async def chat(
        self,
        user: CommunityUser,
        query: str,
        channel_id: str,
    ) -> ChatResponse:
        user_message = AssistantMessage(
            id=f"turn-{uuid4().hex[:10]}",
            role="user",
            author_name=user.name,
            content=query.strip(),
            created_at=now(),
        )
        evidence = self._evidence_for(user, query)
        memories = self._visible_memories(user)
        external_memories = await self.hindsight.recall_confirmed(
            list(allowed_scope_keys(user)),
            query,
        )
        fallback_answer = self._compose_answer(
            user,
            query,
            evidence,
            memories,
            external_memories,
        )
        relevant_memories = [
            memory for memory in memories if memory.content in fallback_answer
        ]
        answer = await self.llm.answer(
            user,
            query,
            evidence,
            relevant_memories,
            fallback_answer,
        )
        used_ids = [memory.id for memory in relevant_memories]
        assistant_message = AssistantMessage(
            id=f"turn-{uuid4().hex[:10]}",
            role="assistant",
            author_name="Trợ lý Kute",
            content=answer,
            citations=[self._citation(value) for value in evidence[:3]],
            memory_used=used_ids,
            created_at=now(),
        )
        candidate = self._candidate_for(user, user_message.id, query, channel_id)

        def operation(state: dict):
            state["assistant_messages"].setdefault(user.id, [])
            state["assistant_messages"][user.id].extend(
                [
                    user_message.model_dump(mode="json"),
                    assistant_message.model_dump(mode="json"),
                ]
            )
            if candidate:
                state["candidates"].append(candidate.model_dump(mode="json"))
            return True

        self.store.mutate(operation)
        await self.hindsight.retain_evidence(
            user_message.id,
            query,
            "user",
            user.id,
        )
        return ChatResponse(
            message=assistant_message,
            candidate=candidate,
            provider=self.llm.status().name,
        )

    async def confirm_candidate(self, candidate_id: str, user: CommunityUser) -> Memory:
        created: dict = {}

        def operation(state: dict):
            index = next(
                (
                    position
                    for position, item in enumerate(state["candidates"])
                    if item["id"] == candidate_id
                ),
                None,
            )
            if index is None:
                raise KeyError(candidate_id)
            candidate = state["candidates"][index]
            if candidate["created_by"] != user.id or not can_write_scope(
                user,
                candidate["scope_type"],
                candidate["scope_id"],
            ):
                raise PermissionError(candidate_id)
            state["candidates"].pop(index)
            timestamp = iso_now()
            memory = {
                "id": f"mem-{uuid4().hex[:10]}",
                "scope_type": candidate["scope_type"],
                "scope_id": candidate["scope_id"],
                "kind": candidate["kind"],
                "content": candidate["content"],
                "evidence": candidate["evidence"],
                "created_by": user.id,
                "status": "confirmed",
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            state["memories"].append(memory)
            created.update(memory)
            return memory

        self.store.mutate(operation)
        memory = Memory.model_validate(created)
        await self.hindsight.retain_confirmed(memory)
        return memory

    async def update_memory(
        self,
        memory_id: str,
        content: str,
        user: CommunityUser,
    ) -> Memory:
        updated: dict = {}

        def operation(state: dict):
            memory = next(
                (item for item in state["memories"] if item["id"] == memory_id),
                None,
            )
            if not memory:
                raise KeyError(memory_id)
            if not can_write_scope(user, memory["scope_type"], memory["scope_id"]):
                raise PermissionError(memory_id)
            memory["content"] = content.strip()
            memory["updated_at"] = iso_now()
            updated.update(memory)
            return memory

        self.store.mutate(operation)
        memory = Memory.model_validate(updated)
        await self.hindsight.retain_confirmed(memory)
        return memory

    async def delete_memory(self, memory_id: str, user: CommunityUser) -> None:
        deleted: dict = {}

        def operation(state: dict):
            memory = next(
                (item for item in state["memories"] if item["id"] == memory_id),
                None,
            )
            if not memory:
                raise KeyError(memory_id)
            if not can_write_scope(user, memory["scope_type"], memory["scope_id"]):
                raise PermissionError(memory_id)
            deleted.update(memory)
            state["memories"] = [
                item for item in state["memories"] if item["id"] != memory_id
            ]
            return True

        self.store.mutate(operation)
        await self.hindsight.delete_confirmed(Memory.model_validate(deleted))
