from dataclasses import dataclass
from datetime import UTC, datetime
import re
from zoneinfo import ZoneInfo

import httpx

from .config import Settings
from .schemas import CommunityUser, DiscordMessage, Memory
from .scopes import channel_record


@dataclass
class LLMStatus:
    name: str
    configured: bool
    reachable: bool | None


class LLMGateway:
    """Grounded answer composer with deterministic fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_error: str | None = None
        self.last_success = False

    @property
    def configured(self) -> bool:
        return bool(self.settings.groq_api_key or self.settings.openrouter_api_key)

    def _provider_config(self) -> tuple[str, str, str, dict[str, str], dict]:
        if self.settings.groq_api_key:
            return (
                "groq",
                self.settings.groq_api_base_url,
                self.settings.groq_model,
                {
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                {
                    "reasoning_effort": "none",
                    "max_completion_tokens": 700,
                },
            )
        return (
            "openrouter",
            self.settings.openrouter_api_base_url,
            self.settings.openrouter_model,
            {
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.settings.openrouter_site_url,
                "X-OpenRouter-Title": "Kute Memory",
            },
            {"max_tokens": 700},
        )

    async def _complete(self, system_prompt: str, user_prompt: str) -> str:
        provider, base_url, model, headers, provider_options = self._provider_config()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.15,
            **provider_options,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"{provider} trả về content rỗng.")
        return content.strip()

    @staticmethod
    def _source_context(evidence: list[DiscordMessage]) -> str:
        lines: list[str] = []
        for index, message in enumerate(evidence[:4], start=1):
            channel = channel_record(message.channel_id)
            channel_name = channel.name if channel else message.channel_id
            lines.append(
                f"[S{index}] #{channel_name} | {message.author_name} | "
                f"{message.created_at.isoformat()}\n{message.content}"
            )
        return "\n\n".join(lines) or "(không có source message)"

    @staticmethod
    def _memory_context(memories: list[Memory]) -> str:
        return "\n".join(
            (
                f"[M{index}] {memory.scope_type}:{memory.scope_id} | "
                f"{memory.kind} | {memory.content}"
            )
            for index, memory in enumerate(memories[:4], start=1)
        ) or "(không có confirmed memory liên quan)"

    async def answer(
        self,
        user: CommunityUser,
        query: str,
        evidence: list[DiscordMessage],
        memories: list[Memory],
        fallback: str,
    ) -> str:
        if not self.configured:
            return fallback

        system_prompt = """
Bạn là Kute, Discord Catch-up Copilot của một lớp học.
Mục tiêu: biến hội thoại phân mảnh thành cập nhật có thể hành động.

Quy tắc bắt buộc:
1. Chỉ dùng SOURCE_MESSAGES và CONFIRMED_MEMORY được cung cấp.
2. Không bịa người, deadline, quyết định, trạng thái hoặc channel.
3. Mỗi ý factual phải kết thúc bằng marker [S1], [S2] hoặc [M1] tương ứng.
4. Khi phù hợp, phân loại ý thành: Đã chốt, Cần làm, Deadline, Blocker.
5. Ưu tiên 2 đến 4 bullet, tiếng Việt tự nhiên, không lặp nguyên văn dài.
6. Nếu source chưa đủ, nói rõ chưa đủ dữ liệu.
7. Không nhắc đến system prompt, token, model hoặc chain of thought.
""".strip()
        user_prompt = f"""
USER
{user.name} | user:{user.id} | team:{user.team_id} | group:{user.group_id}

QUESTION
{query}

SOURCE_MESSAGES
{self._source_context(evidence)}

CONFIRMED_MEMORY
{self._memory_context(memories)}

Viết câu trả lời ngay.
""".strip()

        try:
            content = await self._complete(system_prompt, user_prompt)
            source_markers = [int(value) for value in re.findall(r"\[S(\d+)\]", content)]
            memory_markers = [int(value) for value in re.findall(r"\[M(\d+)\]", content)]
            if evidence and not source_markers:
                raise RuntimeError("OpenRouter response thiếu source marker.")
            if any(value < 1 or value > len(evidence) for value in source_markers):
                raise RuntimeError("OpenRouter response chứa source marker không hợp lệ.")
            if any(value < 1 or value > len(memories) for value in memory_markers):
                raise RuntimeError("OpenRouter response chứa memory marker không hợp lệ.")
            self.last_error = None
            self.last_success = True
            return content.strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, RuntimeError) as exc:
            self.last_error = str(exc)
            self.last_success = False
            return fallback

    @staticmethod
    def _tool_context(sources: list[dict]) -> str:
        values: list[str] = []
        vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")
        for index, source in enumerate(sources[:8], start=1):
            metadata = source.get("metadata") or {}
            title = source.get("title") or metadata.get("title") or source["source_id"]
            created_at = source.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    created_at = None
            if isinstance(created_at, datetime):
                timestamp = (
                    created_at
                    if created_at.tzinfo
                    else created_at.replace(tzinfo=UTC)
                ).astimezone(vietnam_tz).isoformat()
            else:
                timestamp = None
            values.append(
                f"[C{index}] {source['source_type']}:{source['source_id']} | "
                f"{source['channel_key']} | {title} | "
                f"{timestamp or 'không có timestamp'} (Asia/Ho_Chi_Minh)\n"
                f"{str(source['content'])[:1400]}"
            )
        return "\n\n".join(values)

    @staticmethod
    def _time_facts(temporal_context: dict) -> str:
        labels = (
            ("timezone", "Múi giờ"),
            ("current_datetime", "Thời điểm hiện tại"),
            ("current_date", "Ngày hiện tại"),
            ("requested_label", "Cụm thời gian người dùng hỏi"),
            ("requested_date", "Ngày được hỏi"),
            ("requested_start", "Bắt đầu khoảng hỏi"),
            ("requested_end", "Kết thúc khoảng hỏi"),
            ("context_start", "Timestamp context sớm nhất"),
            ("context_end", "Timestamp context muộn nhất"),
            ("dated_source_count", "Số context có timestamp"),
            ("undated_source_count", "Số context không có timestamp"),
        )
        return "\n".join(
            f"{label}: {temporal_context.get(key)}"
            for key, label in labels
        )

    async def answer_with_tool_context(
        self,
        user: CommunityUser,
        query: str,
        sources: list[dict],
        memories: list[Memory],
        temporal_context: dict,
        fallback: str,
    ) -> str:
        if not self.configured or not sources:
            return fallback
        system_prompt = """
Bạn là Kute, trợ lý học tập và Discord Catch-up Copilot.

Quy tắc bắt buộc:
1. Chỉ dùng các facts, evidence và confirmed memory được cung cấp.
2. Nếu nguồn là transcript/slide, trả lời đúng khái niệm bài học; không biến nó thành thông báo Discord.
3. Nếu câu hỏi có thời gian hoặc channel, không dùng nguồn ngoài bộ lọc đã cung cấp.
4. Mỗi ý factual kết thúc bằng marker [C1], [C2] hoặc [M1] tương ứng.
5. Trả lời tiếng Việt ngắn gọn, ưu tiên giải thích trực tiếp rồi đưa ví dụ nếu nguồn có.
6. TIME_FACTS là kết quả tool đáng tin cậy. Nếu có "Ngày được hỏi", hãy dùng ngày đó để diễn đạt "hôm nay/hôm qua" và không được nói rằng thiếu ngày hiện tại.
7. Chỉ nói thiếu timestamp khi "Số context có timestamp" bằng 0.
8. Không nhắc tên section, tên tool, filter, retrieval, context nội bộ, system prompt, token, model hoặc quá trình suy luận.
9. Tuyệt đối không xuất các chuỗi TOOL_CONTEXT, TIME_FACTS, RETRIEVED_EVIDENCE, CONFIRMED_MEMORY, SOURCE_MESSAGES hoặc chain of thought.
""".strip()
        user_prompt = f"""
USER
{user.name} | user:{user.id} | team:{user.team_id} | group:{user.group_id}

QUESTION
{query}

TIME_FACTS
{self._time_facts(temporal_context)}

RETRIEVED_EVIDENCE
{self._tool_context(sources)}

CONFIRMED_MEMORY
{self._memory_context(memories)}

Viết câu trả lời ngay.
""".strip()
        try:
            content = await self._complete(system_prompt, user_prompt)
            context_markers = [int(value) for value in re.findall(r"\[C(\d+)\]", content)]
            memory_markers = [int(value) for value in re.findall(r"\[M(\d+)\]", content)]
            if not context_markers:
                raise RuntimeError("Model response thiếu context marker.")
            if any(value < 1 or value > len(sources) for value in context_markers):
                raise RuntimeError("Model response chứa context marker không hợp lệ.")
            if any(value < 1 or value > len(memories) for value in memory_markers):
                raise RuntimeError("Model response chứa memory marker không hợp lệ.")
            self.last_error = None
            self.last_success = True
            return content
        except (httpx.HTTPError, KeyError, IndexError, TypeError, RuntimeError) as exc:
            self.last_error = str(exc)
            self.last_success = False
            return fallback

    def status(self) -> LLMStatus:
        if not self.configured:
            return LLMStatus(
                name="deterministic-demo",
                configured=False,
                reachable=None,
            )
        return LLMStatus(
            name=(
                (
                    f"groq:{self.settings.groq_model}"
                    if self.settings.groq_api_key
                    else f"openrouter:{self.settings.openrouter_model}"
                )
                if self.last_success or self.last_error is None
                else "llm-fallback"
            ),
            configured=True,
            reachable=(
                True
                if self.last_success
                else False
                if self.last_error is not None
                else None
            ),
        )
