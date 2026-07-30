from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Settings
from .schemas import DiscordMessage
from .seed import CHANNELS, USERS


def _nested(item: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value: Any = item
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value not in (None, ""):
            return value
    return None


def normalize_apify_item(item: dict[str, Any]) -> DiscordMessage | None:
    source_message_id = str(
        _nested(item, "id", "messageId", "message_id", "message.id") or ""
    ).strip()
    discord_channel_id = str(
        _nested(item, "channelId", "channel_id", "channel.id") or ""
    ).strip()
    channel_name = str(
        _nested(item, "channelName", "channel_name", "channel.name") or ""
    ).strip()
    content = str(_nested(item, "content", "message.content", "text") or "").strip()
    discord_author_id = str(
        _nested(item, "author.id", "authorId", "author_id", "user.id") or ""
    ).strip()
    author_name = str(
        _nested(
            item,
            "author.globalName",
            "author.displayName",
            "author.username",
            "authorName",
            "username",
        )
        or "Thành viên Discord"
    ).strip()
    timestamp = _nested(item, "timestamp", "createdAt", "created_at", "message.timestamp")

    if not source_message_id or not content or not timestamp:
        return None

    channel = next(
        (
            value
            for value in CHANNELS
            if value["discord_channel_id"] == discord_channel_id
            or value["name"].casefold() == channel_name.casefold()
        ),
        None,
    )
    if not channel:
        # Unknown channels fail closed instead of being silently treated as public.
        return None

    author = next(
        (value for value in USERS if value["discord_user_id"] == discord_author_id),
        None,
    )
    author_id = author["id"] if author else f"discord:{discord_author_id or 'unknown'}"
    canonical_name = author["member_label"] if author else author_name
    permalink = str(_nested(item, "url", "permalink", "messageUrl") or "").strip()
    if not permalink:
        permalink = (
            f"https://discord.com/channels/imported/"
            f"{channel['discord_channel_id']}/{source_message_id}"
        )

    try:
        created_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    return DiscordMessage(
        id=f"apify-{source_message_id}",
        source_message_id=source_message_id,
        channel_id=channel["id"],
        author_id=author_id,
        author_name=canonical_name,
        content=content,
        created_at=created_at,
        permalink=permalink,
        source="apify",
    )


class ApifyGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.apify_token and self.settings.apify_dataset_id)

    async def fetch_items(self, dataset_id: str, max_items: int) -> list[dict[str, Any]]:
        if not self.settings.apify_token:
            raise RuntimeError("Thiếu APIFY_TOKEN.")

        items: list[dict[str, Any]] = []
        offset = 0
        page_size = min(250, max_items)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.apify_token}",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(items) < max_items:
                response = await client.get(
                    (
                        f"{self.settings.apify_api_base_url.rstrip('/')}/datasets/"
                        f"{dataset_id}/items"
                    ),
                    headers=headers,
                    params={
                        "format": "json",
                        "clean": "1",
                        "offset": offset,
                        "limit": min(page_size, max_items - len(items)),
                    },
                )
                response.raise_for_status()
                page = response.json()
                if not isinstance(page, list):
                    raise RuntimeError("Apify Dataset API không trả về một JSON array.")
                items.extend(value for value in page if isinstance(value, dict))
                if len(page) < page_size:
                    break
                offset += len(page)
        return items[:max_items]
