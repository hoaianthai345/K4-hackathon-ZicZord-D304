from datetime import UTC, datetime
import hmac
import re
from uuid import uuid4

from .chat_service import ChatService
from .config import Settings
from .database import Database
from .schemas import ChatResponse, CommunityUser, TelegramUpdate
from .scopes import scope_descriptors, user_record
from .store import JsonStore
from .telegram_gateway import TelegramGateway, load_telegram_user_map


MAX_TRACKED_TELEGRAM_EVENTS = 500
MAX_TELEGRAM_QUERY_LENGTH = 1200


def normalize_webhook_secret(value: str | None) -> str:
    """Normalize an existing secret to Telegram's documented character set."""

    if not value:
        return ""
    return re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())[:256]


class TelegramService:
    def __init__(
        self,
        settings: Settings,
        store: JsonStore,
        chat_service: ChatService,
        gateway: TelegramGateway,
        database: Database,
    ):
        self.settings = settings
        self.store = store
        self.chat_service = chat_service
        self.gateway = gateway
        self.database = database

    @property
    def configured(self) -> bool:
        return bool(self.gateway.configured and self.settings.telegram_webhook_secret)

    def verify_webhook_secret(self, provided: str | None) -> bool:
        expected = normalize_webhook_secret(self.settings.telegram_webhook_secret)
        return bool(
            expected
            and provided
            and hmac.compare_digest(expected.encode(), provided.encode())
        )

    def claim_update(self, update_id: int) -> bool:
        timestamp = datetime.now(UTC).isoformat()

        def operation(state: dict) -> bool:
            connector_events = state.setdefault("connector_events", {})
            telegram_events = connector_events.setdefault("telegram", {})
            key = str(update_id)
            current = telegram_events.get(key)
            if current and current.get("status") in {"processing", "completed"}:
                return False
            telegram_events[key] = {
                "status": "processing",
                "received_at": timestamp,
                "error": None,
            }
            while len(telegram_events) > MAX_TRACKED_TELEGRAM_EVENTS:
                telegram_events.pop(next(iter(telegram_events)), None)
            return True

        return bool(self.store.mutate(operation))

    def _finish_update(
        self,
        update_id: int,
        *,
        status: str,
        error: str | None = None,
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()

        def operation(state: dict) -> bool:
            events = state.setdefault("connector_events", {}).setdefault(
                "telegram", {}
            )
            record = events.setdefault(str(update_id), {})
            record.update(
                {
                    "status": status,
                    "finished_at": timestamp,
                    "error": error[:300] if error else None,
                }
            )
            return True

        self.store.mutate(operation)

    @staticmethod
    def _command(text: str) -> str | None:
        first_token = text.strip().split(maxsplit=1)[0]
        if not first_token.startswith("/"):
            return None
        return first_token.split("@", maxsplit=1)[0].casefold()

    @staticmethod
    def _unlinked_text(telegram_user_id: int) -> str:
        return (
            "Telegram của bạn chưa được liên kết với ZicZord.\n\n"
            f"Telegram user ID: {telegram_user_id}\n"
            "Gửi ID này cho quản trị viên để thêm vào allowlist. "
            "Bot sẽ không đọc dữ liệu lớp/team trước khi liên kết."
        )

    @staticmethod
    def _help_text(user: CommunityUser) -> str:
        return (
            f"Chào {user.name}. Bạn có thể hỏi:\n"
            "• Bắt kịp Discord trong 24 giờ qua\n"
            "• Workshop hôm qua có nội dung gì?\n"
            "• Team mình đang chốt gì và còn blocker nào?\n"
            "• Mentor group mình dặn gì trước check-in?\n\n"
            "ZicZord chỉ dùng các scope mà tài khoản của bạn được phép xem."
        )

    @staticmethod
    def _identity_text(user: CommunityUser, telegram_user_id: int) -> str:
        scopes = ", ".join(
            f"{scope.type}:{scope.id}" for scope in scope_descriptors(user)
        )
        return (
            f"Telegram user ID: {telegram_user_id}\n"
            f"ZicZord user: {user.id} — {user.name}\n"
            f"Allowed scopes: {scopes}"
        )

    @staticmethod
    def _public_demo_identity_text() -> str:
        return (
            "Bạn đang dùng bản demo công khai của ZicZord 👋\n"
            "Không cần đăng ký hoặc liên kết tài khoản. "
            "Bạn cứ hỏi về bài giảng, workshop, tiến độ team hoặc deadline."
        )

    @staticmethod
    def _format_answer(response: ChatResponse) -> str:
        answer = response.message.content.strip()
        if not response.message.citations:
            return answer
        sources: list[str] = []
        seen_urls: set[str] = set()
        for citation in response.message.citations:
            if citation.permalink in seen_urls:
                continue
            seen_urls.add(citation.permalink)
            sources.append(
                f"{len(sources) + 1}. #{citation.channel_name} — {citation.permalink}"
            )
        return f"{answer}\n\nNguồn Discord:\n" + "\n".join(sources)

    async def process_update(self, update: TelegramUpdate) -> None:
        try:
            await self._process_update(update)
            self._finish_update(update.update_id, status="completed")
        except Exception as exc:
            self._finish_update(update.update_id, status="failed", error=str(exc))

    async def _process_update(self, update: TelegramUpdate) -> None:
        message = update.message
        if not message or not message.from_user or message.from_user.is_bot:
            return

        sender = message.from_user
        if message.chat.type != "private":
            await self.gateway.send_message(
                message.chat.id,
                (
                    "Để bảo vệ context cá nhân và team, ZicZord chỉ trả lời "
                    "trong chat riêng với bot."
                ),
                reply_to_message_id=message.message_id,
            )
            return

        try:
            user_map = load_telegram_user_map(self.settings.telegram_user_map_path)
        except RuntimeError:
            await self.gateway.send_message(
                message.chat.id,
                "Connector Telegram đang sai cấu hình allowlist. Vui lòng báo quản trị viên.",
                reply_to_message_id=message.message_id,
            )
            return

        mapped_user_id = user_map.get(sender.id)
        is_public_guest = bool(
            not mapped_user_id and self.settings.telegram_public_user_id
        )
        internal_user_id = mapped_user_id or self.settings.telegram_public_user_id
        user = user_record(internal_user_id) if internal_user_id else None
        text = (message.text or "").strip()
        command = self._command(text) if text else None

        if internal_user_id and not user:
            await self.gateway.send_message(
                message.chat.id,
                "Connector Telegram đang sai cấu hình tài khoản demo.",
                reply_to_message_id=message.message_id,
            )
            return

        if command == "/whoami":
            reply = (
                self._public_demo_identity_text()
                if is_public_guest
                else self._identity_text(user, sender.id)
                if user
                else self._unlinked_text(sender.id)
            )
            await self.gateway.send_message(
                message.chat.id,
                reply,
                reply_to_message_id=message.message_id,
            )
            return

        if not user:
            await self.gateway.send_message(
                message.chat.id,
                self._unlinked_text(sender.id),
                reply_to_message_id=message.message_id,
            )
            return

        if is_public_guest:
            user = user.model_copy(update={"name": "bạn"})

        if command in {"/start", "/help"}:
            await self.gateway.send_message(
                message.chat.id,
                self._help_text(user),
                reply_to_message_id=message.message_id,
            )
            return

        if not text:
            await self.gateway.send_message(
                message.chat.id,
                "Hiện tại bot chỉ hỗ trợ câu hỏi dạng văn bản.",
                reply_to_message_id=message.message_id,
            )
            return
        if len(text) > MAX_TELEGRAM_QUERY_LENGTH:
            await self.gateway.send_message(
                message.chat.id,
                (
                    "Câu hỏi quá dài. Vui lòng rút gọn còn tối đa "
                    f"{MAX_TELEGRAM_QUERY_LENGTH} ký tự."
                ),
                reply_to_message_id=message.message_id,
            )
            return

        response = await self.chat_service.chat(user, text, "bot-commands")
        await self.gateway.send_message(
            message.chat.id,
            self._format_answer(response),
            reply_to_message_id=message.message_id,
        )
        await self.database.log_chat_interaction(
            interaction_id=f"telegram-{update.update_id}-{uuid4().hex}",
            profile_id=None,
            demo_user_id=user.id,
            channel_id="telegram-private",
            source="telegram",
            external_user_id=str(sender.id),
            question=text,
            answer=response.message.content,
            provider=response.provider,
            citations=[
                citation.model_dump(mode="json")
                for citation in response.message.citations
            ],
            tool_calls=[
                tool_call.model_dump(mode="json")
                for tool_call in response.tool_calls
            ],
        )
