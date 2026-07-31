from dataclasses import dataclass
from datetime import UTC, datetime
import json
import re
from zoneinfo import ZoneInfo

import httpx

from .config import Settings
from .key_pool import OpenRouterKeyPool, RECOVERABLE_STATUS_CODES
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
        self.last_provider: str | None = None
        self.openrouter_pool = OpenRouterKeyPool(
            settings.openrouter_keys,
            settings.openrouter_flow_orders,
        )

    @property
    def configured(self) -> bool:
        return bool(self.settings.groq_api_key or self.openrouter_pool.configured)

    async def _request_completion(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        provider: str,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        provider_options: dict[str, object] = {"max_tokens": max_tokens}
        if provider == "openrouter":
            headers.update(
                {
                    "HTTP-Referer": self.settings.openrouter_site_url,
                    "X-OpenRouter-Title": "Kute Discord Copilot",
                }
            )
            provider_options["reasoning"] = {
                "effort": "none",
                "exclude": True,
            }
        else:
            provider_options = {
                "reasoning_effort": "none",
                "max_completion_tokens": max_tokens,
            }
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
    def _retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(1.0, float(value))
        except ValueError:
            return None

    async def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        flow: str = "chat",
        max_tokens: int = 700,
    ) -> str:
        failures: list[str] = []
        for slot in self.openrouter_pool.candidates(flow):
            try:
                content = await self._request_completion(
                    api_key=slot.value,
                    base_url=self.settings.openrouter_api_base_url,
                    model=self.settings.openrouter_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    provider="openrouter",
                )
                self.openrouter_pool.mark_success(slot.name)
                self.last_provider = (
                    f"openrouter-pool:{flow}:{self.settings.openrouter_model}"
                )
                return content
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code not in RECOVERABLE_STATUS_CODES:
                    raise
                self.openrouter_pool.mark_failure(
                    slot.name,
                    status_code,
                    self._retry_after(exc.response),
                )
                failures.append(f"openrouter:{slot.name}:{status_code}")
            except httpx.RequestError:
                self.openrouter_pool.mark_failure(slot.name, None)
                failures.append(f"openrouter:{slot.name}:network")

        if self.settings.groq_api_key:
            try:
                content = await self._request_completion(
                    api_key=self.settings.groq_api_key,
                    base_url=self.settings.groq_api_base_url,
                    model=self.settings.groq_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    provider="groq",
                )
                self.last_provider = f"groq:{self.settings.groq_model}"
                return content
            except httpx.HTTPError as exc:
                status_code = (
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else "network"
                )
                failures.append(f"groq:{status_code}")

        raise RuntimeError(
            "Không có provider khả dụng."
            + (f" ({', '.join(failures)})" if failures else "")
        )

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

    async def build_daily_brief(
        self,
        user: CommunityUser,
        messages: list[DiscordMessage],
        window_hours: int,
    ) -> list[dict] | None:
        if not self.configured or not messages:
            return None
        source_lines: list[str] = []
        for message in messages[:40]:
            channel = channel_record(message.channel_id)
            channel_name = channel.name if channel else message.channel_id
            content = re.sub(r"\s+", " ", message.content).strip()[:420]
            source_lines.append(
                f"id={message.id} | #{channel_name} | {message.author_name} | "
                f"{message.created_at.isoformat()} | {content}"
            )
        system_prompt = """
Bạn là bộ phân loại daily brief cho một lớp học trên Discord.

Đọc các tin nhắn đã được server lọc quyền và quyết định tin nào cần xuất hiện.
Chỉ chọn một trong bốn loại: decision, task, blocker, announcement.
Deadline phải được chép đúng từ tin nguồn; không suy đoán ngày hoặc giờ.
Mỗi item phải trỏ tới đúng một message_id có trong đầu vào.
Không đưa greeting, acknowledgement đơn giản hoặc hội thoại không hành động.
Giới hạn 2 decision, 3 task, 2 blocker và 2 announcement.
Trả về JSON thuần, không Markdown và không giải thích:
{"items":[{"message_id":"...","kind":"task","title":"...",
"owner":null,"deadline":null,"status":"open"}]}
status chỉ nhận open, resolved hoặc unknown.
""".strip()
        user_prompt = (
            f"USER: {user.name} | team:{user.team_id} | group:{user.group_id}\n"
            f"WINDOW_HOURS: {window_hours}\n\n"
            "AUTHORIZED_DISCORD_MESSAGES\n"
            + "\n".join(source_lines)
        )
        try:
            content = await self._complete(
                system_prompt,
                user_prompt,
                flow="brief",
                max_tokens=1400,
            )
            without_thinking = re.sub(
                r"<think>.*?</think>",
                "",
                content,
                flags=re.DOTALL | re.IGNORECASE,
            ).strip()
            without_fence = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                without_thinking,
                flags=re.IGNORECASE,
            )
            start = without_fence.find("{")
            end = without_fence.rfind("}")
            if start < 0 or end <= start:
                raise RuntimeError("Daily brief response không chứa JSON object.")
            payload = json.loads(without_fence[start : end + 1])
            raw_items = payload.get("items")
            if not isinstance(raw_items, list):
                raise RuntimeError("Daily brief response thiếu items.")
            allowed_messages = {message.id: message for message in messages[:40]}
            limits = {"decision": 2, "task": 3, "blocker": 2, "announcement": 2}
            counts = {kind: 0 for kind in limits}
            seen_ids: set[str] = set()
            items: list[dict] = []
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                message_id = str(raw.get("message_id") or "")
                kind = str(raw.get("kind") or "")
                if (
                    message_id not in allowed_messages
                    or message_id in seen_ids
                    or kind not in limits
                    or counts[kind] >= limits[kind]
                ):
                    continue
                status = str(raw.get("status") or "unknown")
                if status not in {"open", "resolved", "unknown"}:
                    status = "unknown"
                title = re.sub(r"\s+", " ", str(raw.get("title") or "")).strip()
                if not title:
                    continue
                source_message = allowed_messages[message_id]
                source_text = re.sub(
                    r"\s+",
                    " ",
                    f"{source_message.author_name} {source_message.content}",
                ).casefold()
                owner = str(raw.get("owner") or "").strip()
                if owner and owner.casefold() not in source_text:
                    owner = ""
                deadline = str(raw.get("deadline") or "").strip()
                if deadline and deadline.casefold() not in source_text:
                    deadline = ""
                seen_ids.add(message_id)
                counts[kind] += 1
                items.append(
                    {
                        "message_id": message_id,
                        "kind": kind,
                        "title": title[:117],
                        "owner": owner[:80] or None,
                        "deadline": deadline[:100] or None,
                        "status": status,
                    }
                )
            self.last_error = None
            self.last_success = True
            return items
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            RuntimeError,
        ) as exc:
            self.last_error = str(exc)
            self.last_success = False
            return None

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
                    self.last_provider
                    or (
                        f"openrouter-pool:{self.settings.openrouter_model}"
                        if self.openrouter_pool.configured
                        else f"groq:{self.settings.groq_model}"
                    )
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
