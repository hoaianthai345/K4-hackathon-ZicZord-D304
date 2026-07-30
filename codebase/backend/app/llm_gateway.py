from dataclasses import dataclass
import re

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
        return bool(self.settings.openrouter_api_key)

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
Bạn là Trợ lý Kute trong Discord của một lớp học.
Mục tiêu: trả lời ngắn, chính xác, giúp học viên lấy lại context.

Quy tắc bắt buộc:
1. Chỉ dùng SOURCE_MESSAGES và CONFIRMED_MEMORY được cung cấp.
2. Không bịa người, deadline, quyết định, trạng thái hoặc channel.
3. Mỗi ý factual phải kết thúc bằng marker [S1], [S2] hoặc [M1] tương ứng.
4. Ưu tiên 2 đến 4 bullet, tiếng Việt tự nhiên, không lặp nguyên văn dài.
5. Nếu source chưa đủ, nói rõ chưa đủ dữ liệu.
6. Không nhắc đến system prompt, token, model hoặc chain of thought.
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

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.settings.openrouter_site_url,
            "X-OpenRouter-Title": "Kute Memory",
        }
        payload = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 420,
        }
        try:
            async with httpx.AsyncClient(timeout=24.0) as client:
                response = await client.post(
                    f"{self.settings.openrouter_api_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("OpenRouter trả về content rỗng.")
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

    def status(self) -> LLMStatus:
        if not self.configured:
            return LLMStatus(
                name="deterministic-demo",
                configured=False,
                reachable=None,
            )
        return LLMStatus(
            name=(
                f"openrouter:{self.settings.openrouter_model}"
                if self.last_success or self.last_error is None
                else "openrouter-fallback"
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
