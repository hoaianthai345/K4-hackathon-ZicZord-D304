import json
from pathlib import Path
from typing import Any

import httpx

from .config import Settings
from .seed import USERS


TELEGRAM_TEXT_LIMIT = 4096
TELEGRAM_SAFE_CHUNK_SIZE = TELEGRAM_TEXT_LIMIT - 196


def load_telegram_user_map(path: Path) -> dict[int, str]:
    """Load an explicit Telegram-user-to-ZicZord-user allowlist."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Telegram user map không phải JSON hợp lệ: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"Không đọc được Telegram user map: {exc}") from exc

    records = payload.get("users") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise RuntimeError("Telegram user map phải có một JSON array tên 'users'.")

    known_user_ids = {user["id"] for user in USERS}
    result: dict[int, str] = {}
    claimed_internal_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or record.get("enabled", True) is False:
            continue
        raw_telegram_id = str(record.get("telegram_user_id") or "").strip()
        internal_user_id = str(record.get("internal_user_id") or "").strip()
        if not raw_telegram_id or not raw_telegram_id.isdigit():
            raise RuntimeError("Mỗi telegram_user_id được bật phải là một chuỗi số.")
        telegram_user_id = int(raw_telegram_id)
        if telegram_user_id <= 0:
            raise RuntimeError("telegram_user_id phải lớn hơn 0.")
        if internal_user_id not in known_user_ids:
            raise RuntimeError(
                f"Telegram user map tham chiếu user không tồn tại: {internal_user_id}."
            )
        if telegram_user_id in result:
            raise RuntimeError(
                f"Telegram user ID {telegram_user_id} bị khai báo nhiều lần."
            )
        if internal_user_id in claimed_internal_ids:
            raise RuntimeError(
                f"Internal user {internal_user_id} bị nối với nhiều Telegram account."
            )
        result[telegram_user_id] = internal_user_id
        claimed_internal_ids.add(internal_user_id)
    return result


def split_telegram_text(text: str) -> list[str]:
    """Split long answers below Telegram's 4096-character text limit."""

    remaining = text.strip()
    if not remaining:
        return []
    chunks: list[str] = []
    while len(remaining) > TELEGRAM_SAFE_CHUNK_SIZE:
        pivot = remaining.rfind("\n", 0, TELEGRAM_SAFE_CHUNK_SIZE + 1)
        if pivot < TELEGRAM_SAFE_CHUNK_SIZE // 2:
            pivot = remaining.rfind(" ", 0, TELEGRAM_SAFE_CHUNK_SIZE + 1)
        if pivot < TELEGRAM_SAFE_CHUNK_SIZE // 2:
            pivot = TELEGRAM_SAFE_CHUNK_SIZE
        chunk = remaining[:pivot].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[pivot:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


class TelegramGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.telegram_bot_token)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        reply_to_message_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.settings.telegram_bot_token:
            raise RuntimeError("Thiếu TELEGRAM_BOT_TOKEN.")

        endpoint = (
            f"{self.settings.telegram_api_base_url.rstrip('/')}/"
            f"bot{self.settings.telegram_bot_token}/sendMessage"
        )
        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for index, chunk in enumerate(split_telegram_text(text)):
                    payload: dict[str, Any] = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "link_preview_options": {"is_disabled": True},
                    }
                    if index == 0 and reply_to_message_id is not None:
                        payload["reply_parameters"] = {
                            "message_id": reply_to_message_id,
                            "allow_sending_without_reply": True,
                        }
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    body = response.json()
                    if not isinstance(body, dict) or body.get("ok") is not True:
                        description = (
                            body.get("description")
                            if isinstance(body, dict)
                            else "response không hợp lệ"
                        )
                        raise RuntimeError(f"Telegram từ chối sendMessage: {description}")
                    result = body.get("result")
                    results.append(result if isinstance(result, dict) else {})
            self.last_error = None
            return results
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.json()
                description = (
                    body.get("description")
                    if isinstance(body, dict)
                    else "request bị từ chối"
                )
            except ValueError:
                description = "request bị từ chối"
            safe_error = RuntimeError(
                f"Telegram API HTTP {exc.response.status_code}: {description}"
            )
            self.last_error = str(safe_error)
            raise safe_error from exc
        except httpx.RequestError as exc:
            safe_error = RuntimeError(
                f"Không kết nối được Telegram API ({type(exc).__name__})."
            )
            self.last_error = str(safe_error)
            raise safe_error from exc
        except (ValueError, RuntimeError) as exc:
            self.last_error = str(exc)
            raise
