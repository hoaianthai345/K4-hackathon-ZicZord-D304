from datetime import UTC, datetime, timedelta
import re
from urllib.parse import quote
from uuid import uuid4

from .context_tools import ContextPlan, ContextToolService
from .hindsight_gateway import HindsightGateway
from .llm_gateway import LLMGateway
from .rag_anything_gateway import RAGAnythingGateway, RAGAnythingSource
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
        rag: RAGAnythingGateway | None = None,
        context_tools: ContextToolService | None = None,
    ):
        self.store = store
        self.hindsight = hindsight
        self.llm = llm
        self.rag = rag
        self.context_tools = context_tools

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

    def _rag_citation(
        self,
        source: RAGAnythingSource,
        user: CommunityUser,
    ) -> Citation:
        channel_ids = {
            "common": "general",
            "qa": "qa",
            "bot-commands": "bot-commands",
        }
        channel_id = channel_ids.get(source.channel_key, source.channel_key)
        channel = channel_record(channel_id)
        channel_name = channel.name if channel else source.channel_key
        source_type = quote(source.source_type, safe="")
        source_id = quote(source.source_id, safe="")
        user_id = quote(user.id, safe="")
        return Citation(
            message_id=source.source_id,
            channel_id=channel_id,
            channel_name=channel_name,
            label=f"#{channel_name} · {source.label}",
            permalink=(
                f"{self.rag.settings.api_public_url}/api/rag/sources/"
                f"{source_type}/{source_id}?user_id={user_id}"
            ),
        )

    def _tool_citation(
        self,
        source: dict,
        user: CommunityUser,
    ) -> Citation:
        source_type = str(source["source_type"])
        source_id = str(source["source_id"])
        channel_key = str(source["channel_key"])
        if source_type == "lesson" and channel_key == "announcement":
            channel_id = "announcements"
        elif source_type == "lesson":
            room_suffix = (user.lecture_room_id or "LEC-D302").split("-", 1)[-1].casefold()
            channel_id = f"lecture-{room_suffix}"
        else:
            channel_ids = {
                "common": "general",
                "qa": "qa",
                "bot-commands": "bot-commands",
            }
            channel_id = channel_ids.get(channel_key, channel_key)
        channel = channel_record(channel_id)
        channel_name = channel.name if channel else channel_key
        metadata = source.get("metadata") or {}
        label = source.get("title") or metadata.get("title") or source_id
        return Citation(
            message_id=source_id,
            channel_id=channel_id,
            channel_name=channel_name,
            label=f"#{channel_name} · {label}",
            permalink=(
                f"{self.llm.settings.api_public_url}/api/rag/sources/"
                f"{quote(source_type, safe='')}/{quote(source_id, safe='')}?"
                f"user_id={quote(user.id, safe='')}"
            ),
        )

    @staticmethod
    def _clean_rag_answer(value: str) -> str:
        marker = (
            r"\[?SOURCE_ID=[A-Za-z0-9_-]+\|TYPE="
            r"(?:message|episode|painpoint)\|CHANNEL=[A-Za-z0-9_-]+\]?"
        )
        without_thinking = re.sub(
            r"<think>.*?</think>",
            "",
            value,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return re.sub(r"[ \t]*" + marker, "", without_thinking).strip()

    @staticmethod
    def _clean_tool_answer(value: str) -> str:
        without_thinking = re.sub(
            r"<think>.*?</think>",
            "",
            value,
            flags=re.DOTALL | re.IGNORECASE,
        )
        without_markers = re.sub(
            r"[ \t]*\[(?:C|M)\d+\]",
            "",
            without_thinking,
        )
        without_internal_labels = re.sub(
            (
                r"\b(?:TOOL_CONTEXT|TIME_FACTS|RETRIEVED_EVIDENCE|"
                r"CONFIRMED_MEMORY|SOURCE_MESSAGES)\b"
            ),
            "nguồn dữ liệu được cung cấp",
            without_markers,
            flags=re.IGNORECASE,
        )
        return without_internal_labels.strip()

    @staticmethod
    def _tool_fallback(sources: list[dict]) -> str:
        if not sources:
            return "Mình chưa tìm thấy context phù hợp trong các nguồn được phép đọc."
        lines = ["Mình tìm thấy các đoạn liên quan nhất:"]
        for source in sources[:3]:
            content = str(source["content"]).strip()
            excerpt = content if len(content) <= 360 else f"{content[:357]}..."
            lines.append(f"• {excerpt}")
        return "\n".join(lines)

    @staticmethod
    def _memories_for_tool_answer(
        plan: ContextPlan,
        memories: list[Memory],
    ) -> list[Memory]:
        if plan.lesson_intent:
            return [
                memory
                for memory in memories
                if memory.kind == "learning_note"
                and memory.scope_type in {"room", "cohort"}
            ][:4]
        if plan.strict_discord_filter:
            return []
        return memories[:4]

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
        *,
        persist: bool = True,
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
        tool_retrieval = (
            await self.context_tools.retrieve(user, query, channel_id)
            if self.context_tools
            else None
        )
        rag_result = None
        exact_tool_route = bool(
            tool_retrieval
            and (
                tool_retrieval.plan.lesson_intent
                or tool_retrieval.plan.strict_discord_filter
            )
        )
        if not exact_tool_route:
            rag_result = await self.rag.query(user, query) if self.rag else None
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
        tool_calls = []
        if tool_retrieval:
            tool_calls = [
                {
                    "name": call.name,
                    "arguments": call.arguments,
                    "reason": call.reason,
                    "result_count": call.result_count,
                }
                for call in tool_retrieval.calls
            ]
        if tool_retrieval and tool_retrieval.should_answer_directly:
            relevant_memories = self._memories_for_tool_answer(
                tool_retrieval.plan,
                memories,
            )
            raw_answer = await self.llm.answer_with_tool_context(
                user,
                query,
                tool_retrieval.sources,
                relevant_memories,
                tool_retrieval.temporal_context,
                self._tool_fallback(tool_retrieval.sources),
            )
            cited_indexes = list(
                dict.fromkeys(
                    int(value)
                    for value in re.findall(r"\[C(\d+)\]", raw_answer)
                )
            )
            memory_indexes = list(
                dict.fromkeys(
                    int(value)
                    for value in re.findall(r"\[M(\d+)\]", raw_answer)
                )
            )
            answer = self._clean_tool_answer(raw_answer)
            cited_sources = (
                [
                    tool_retrieval.sources[index - 1]
                    for index in cited_indexes
                    if 1 <= index <= len(tool_retrieval.sources)
                ]
                or tool_retrieval.sources[:4]
            )
            citations = [
                self._tool_citation(source, user)
                for source in cited_sources[:4]
            ]
            relevant_memories = [
                relevant_memories[index - 1]
                for index in memory_indexes
                if 1 <= index <= len(relevant_memories)
            ]
            response_provider = f"context-tools+{self.llm.status().name}"
        elif rag_result:
            answer = self._clean_rag_answer(rag_result.answer)
            citations = [
                self._rag_citation(source, user)
                for source in rag_result.sources[:4]
            ]
            response_provider = rag_result.provider
        else:
            answer = await self.llm.answer(
                user,
                query,
                evidence,
                relevant_memories,
                fallback_answer,
            )
            citations = [self._citation(value) for value in evidence[:3]]
            response_provider = self.llm.status().name
        used_ids = [memory.id for memory in relevant_memories]
        assistant_message = AssistantMessage(
            id=f"turn-{uuid4().hex[:10]}",
            role="assistant",
            author_name="Trợ lý ZicZord",
            content=answer,
            citations=citations,
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

        if persist:
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
            provider=response_provider,
            tool_calls=tool_calls,
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
