import asyncio
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import re
import unicodedata
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
import httpx

from .config import Settings
from .schemas import CommunityUser, GoogleTaskResponse
from .store import JsonStore


TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"
PITCH_SCOPE_KEY = "team:T004"
PITCH_CHANNEL_ID = "team-t004"


class GoogleTasksError(RuntimeError):
    pass


class GoogleTasksNotConfigured(GoogleTasksError):
    pass


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def deadline_due(
    deadline: str | None,
    *,
    reference: datetime,
    time_zone: str,
) -> datetime | None:
    """Convert a Vietnamese deadline label to Google Tasks' date-only due value."""
    if not deadline:
        return None
    try:
        zone = ZoneInfo(time_zone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Asia/Ho_Chi_Minh")
    local_reference = reference.astimezone(zone)
    folded = _fold(deadline)
    due_date: date | None = None

    if "ngay kia" in folded:
        due_date = local_reference.date() + timedelta(days=2)
    elif re.search(r"\b(?:ngay mai|mai)\b", folded):
        due_date = local_reference.date() + timedelta(days=1)
    elif "hom nay" in folded:
        due_date = local_reference.date()

    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", folded)
    if iso_match:
        try:
            due_date = date(*(int(value) for value in iso_match.groups()))
        except ValueError:
            due_date = None

    local_match = re.search(
        r"\b(?:ngay\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",
        folded,
    )
    if local_match:
        day, month, year = local_match.groups()
        resolved_year = int(year) if year else local_reference.year
        if resolved_year < 100:
            resolved_year += 2000
        try:
            due_date = date(resolved_year, int(month), int(day))
        except ValueError:
            due_date = None

    if due_date is None:
        return None
    # Google Tasks stores only the date portion of due; midnight UTC is canonical.
    return datetime.combine(due_date, datetime.min.time(), tzinfo=UTC)


class GoogleTasksGateway:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.transport = transport
        self._credentials: Credentials | None = None
        self._credential_lock = asyncio.Lock()

    @property
    def provider(self) -> str:
        if self.settings.google_tasks_mode == "mock":
            return "pitch-mock"
        if self.settings.google_tasks_mode == "live" and self.configured:
            return "google-tasks"
        return "not-configured"

    @property
    def configured(self) -> bool:
        credential_file = self.settings.google_tasks_credentials_file
        return bool(
            self.settings.google_tasks_access_token
            or self.settings.google_tasks_credentials_json
            or (credential_file and credential_file.is_file())
        )

    def _load_credentials(self) -> Credentials:
        raw: dict
        if self.settings.google_tasks_credentials_json:
            try:
                raw = json.loads(self.settings.google_tasks_credentials_json)
            except json.JSONDecodeError as exc:
                raise GoogleTasksNotConfigured(
                    "GOOGLE_TASKS_CREDENTIALS_JSON không phải JSON hợp lệ."
                ) from exc
        elif (
            self.settings.google_tasks_credentials_file
            and self.settings.google_tasks_credentials_file.is_file()
        ):
            try:
                raw = json.loads(
                    self.settings.google_tasks_credentials_file.read_text(
                        encoding="utf-8"
                    )
                )
            except (OSError, json.JSONDecodeError) as exc:
                raise GoogleTasksNotConfigured(
                    "Không đọc được OAuth credentials của Google Tasks."
                ) from exc
        else:
            raise GoogleTasksNotConfigured(
                "Thiếu OAuth authorized-user credentials cho Google Tasks."
            )
        try:
            return Credentials.from_authorized_user_info(
                raw,
                scopes=[TASKS_SCOPE],
            )
        except (KeyError, ValueError) as exc:
            raise GoogleTasksNotConfigured(
                "Google Tasks cần authorized-user JSON có refresh_token, "
                "client_id và client_secret."
            ) from exc

    async def _access_token(self) -> str:
        if self.settings.google_tasks_access_token:
            return self.settings.google_tasks_access_token
        if not self.configured:
            raise GoogleTasksNotConfigured(
                "Google Tasks live chưa có access token hoặc OAuth credentials."
            )
        async with self._credential_lock:
            if self._credentials is None:
                self._credentials = self._load_credentials()
            if not self._credentials.valid or not self._credentials.token:
                await asyncio.to_thread(
                    self._credentials.refresh,
                    GoogleAuthRequest(),
                )
            return str(self._credentials.token)

    @staticmethod
    def mock_task_id(source_item_id: str) -> str:
        digest = hashlib.sha256(source_item_id.encode("utf-8")).hexdigest()[:18]
        return f"mock-{digest}"

    async def create_task(
        self,
        *,
        title: str,
        notes: str,
        due: datetime | None,
        source_item_id: str,
    ) -> dict:
        provider = self.provider
        if provider == "pitch-mock":
            return {
                "task_id": self.mock_task_id(source_item_id),
                "tasklist_id": self.settings.google_tasks_tasklist_id,
                "title": title,
                "notes": notes,
                "due": due.isoformat() if due else None,
                "status": "needsAction",
                "html_link": "https://tasks.google.com/",
                "provider": provider,
            }
        if provider != "google-tasks":
            raise GoogleTasksNotConfigured(
                "GOOGLE_TASKS_MODE=live nhưng OAuth Google Tasks chưa được cấu hình."
            )

        token = await self._access_token()
        tasklist_id = self.settings.google_tasks_tasklist_id or "@default"
        url = (
            f"{self.settings.google_tasks_api_base_url.rstrip('/')}/lists/"
            f"{quote(tasklist_id, safe='')}/tasks"
        )
        body = {
            "title": title,
            "notes": notes,
            "status": "needsAction",
        }
        if due:
            body["due"] = due.isoformat().replace("+00:00", "Z")
        async with httpx.AsyncClient(
            timeout=20.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise GoogleTasksError(
                    f"Google Tasks trả về HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                ) from exc
            payload = response.json()
        task_id = str(payload.get("id") or "")
        if not task_id:
            raise GoogleTasksError("Google Tasks không trả về task id.")
        return {
            "task_id": task_id,
            "tasklist_id": tasklist_id,
            "title": str(payload.get("title") or title),
            "notes": str(payload.get("notes") or notes),
            "due": payload.get("due") or (due.isoformat() if due else None),
            "status": (
                "completed"
                if payload.get("status") == "completed"
                else "needsAction"
            ),
            "html_link": "https://tasks.google.com/",
            "provider": provider,
        }


class GoogleTaskService:
    def __init__(self, store: JsonStore, gateway: GoogleTasksGateway):
        self.store = store
        self.gateway = gateway

    @staticmethod
    def _authorized_item(
        snapshot: dict,
        brief_id: str,
        item_id: str,
        user: CommunityUser,
    ) -> tuple[dict, dict]:
        if user.team_id != "T004":
            raise PermissionError(item_id)
        brief = next(
            (
                value
                for value in snapshot["catchup_briefs"].get(user.id, [])
                if value["id"] == brief_id
            ),
            None,
        )
        if not brief:
            raise KeyError(brief_id)
        if (
            brief.get("user_id") != user.id
            or brief.get("scope_key") != PITCH_SCOPE_KEY
        ):
            raise PermissionError(brief_id)
        item = next(
            (value for value in brief["items"] if value["id"] == item_id),
            None,
        )
        if not item:
            raise KeyError(item_id)
        citations = item.get("citations") or []
        if not citations or any(
            citation.get("channel_id") != PITCH_CHANNEL_ID
            for citation in citations
        ):
            raise PermissionError(item_id)
        if item.get("kind") not in {"task", "blocker"} and not item.get("deadline"):
            raise ValueError("Chỉ task, blocker hoặc item có deadline mới được đồng bộ.")
        return brief, item

    @staticmethod
    def _stored_response(
        snapshot: dict,
        item_id: str,
        user: CommunityUser,
    ) -> GoogleTaskResponse | None:
        record = snapshot.get("google_tasks", {}).get(item_id)
        if not record:
            return None
        if (
            record.get("created_by") != user.id
            or record.get("scope_key") != PITCH_SCOPE_KEY
        ):
            raise PermissionError(item_id)
        response_fields = {
            key: value
            for key, value in record.items()
            if key != "created_by"
        }
        return GoogleTaskResponse.model_validate(response_fields)

    async def sync_brief_item(
        self,
        brief_id: str,
        item_id: str,
        user: CommunityUser,
    ) -> GoogleTaskResponse:
        snapshot = self.store.snapshot()
        stored = self._stored_response(snapshot, item_id, user)
        if stored:
            return stored
        _, item = self._authorized_item(snapshot, brief_id, item_id, user)
        citation_links = "\n".join(
            f"- {citation['label']}: {citation['permalink']}"
            for citation in item["citations"]
        )
        owner = item.get("owner") or "Chưa xác định"
        deadline = item.get("deadline") or "Chưa có"
        notes = (
            f"Scope: {PITCH_SCOPE_KEY}\n"
            f"Owner: {owner}\n"
            f"Deadline nguồn: {deadline}\n\n"
            f"Tin nhắn gốc:\n{item['detail']}\n\n"
            f"Nguồn Discord:\n{citation_links}\n\n"
            f"ZicZord source_item_id={item_id}"
        )
        prefix = "[T004][Blocker]" if item["kind"] == "blocker" else "[T004]"
        title = f"{prefix} {item['title']}"[:1024]
        due = deadline_due(
            item.get("deadline"),
            reference=datetime.now(UTC),
            time_zone=self.gateway.settings.google_tasks_timezone,
        )
        task = await self.gateway.create_task(
            title=title,
            notes=notes,
            due=due,
            source_item_id=item_id,
        )
        response = GoogleTaskResponse(
            **task,
            source_brief_id=brief_id,
            source_item_id=item_id,
            scope_key=PITCH_SCOPE_KEY,
        )

        def remember(state: dict):
            state.setdefault("google_tasks", {})[item_id] = {
                **response.model_dump(mode="json"),
                "created_by": user.id,
            }
            return True

        self.store.mutate(remember)
        return response
