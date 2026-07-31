import asyncio
from datetime import date, datetime, time, timedelta
import hashlib
import json
import re
import unicodedata
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
import httpx

from .config import Settings
from .schemas import (
    CalendarEventDraft,
    CalendarTaskResponse,
    CommunityUser,
    Memory,
)
from .scopes import can_write_scope
from .store import JsonStore


CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"
CALENDAR_TARGET_RE = re.compile(
    r"(?:\b(?:google|gg)\s*calend[ae]r\b|\bcalend[ae]r\b|"
    r"\blịch(?:\s+google)?\b)",
    re.IGNORECASE,
)
CALENDAR_ACTION_RE = re.compile(
    r"\b(?:thêm|tạo|đặt|lên|nhắc|add|create|schedule)\b",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(
    r"(?<![A-Z0-9._%+\-])"
    r"([A-Z0-9._%+\-]+@[A-Z0-9\-]+(?:\.[A-Z0-9\-]+)+)"
    r"(?![A-Z0-9._%+\-])",
    re.IGNORECASE,
)


class GoogleCalendarError(RuntimeError):
    pass


class GoogleCalendarNotConfigured(GoogleCalendarError):
    pass


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def calendar_requested(query: str) -> bool:
    folded = _fold(query)
    reminder = re.search(r"\bnhac\s+(?:toi|minh)\b", folded)
    return bool(
        reminder
        or (CALENDAR_TARGET_RE.search(query) and CALENDAR_ACTION_RE.search(query))
    )


def extract_email(value: str) -> str | None:
    match = EMAIL_RE.search(value.strip())
    return match.group(1).casefold() if match else None


def redact_emails(value: str) -> str:
    return EMAIL_RE.sub("[email Google Calendar]", value)


def _calendar_date(query: str, reference: datetime) -> date | None:
    folded = _fold(query)
    if "ngay kia" in folded:
        return reference.date() + timedelta(days=2)
    if re.search(r"\b(?:ngay mai|mai)\b", folded):
        return reference.date() + timedelta(days=1)
    if "hom nay" in folded:
        return reference.date()

    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", folded)
    if iso_match:
        try:
            return date(*(int(value) for value in iso_match.groups()))
        except ValueError:
            return None

    local_match = re.search(
        r"\b(?:ngay\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b",
        folded,
    )
    if local_match:
        day, month, year = local_match.groups()
        resolved_year = int(year) if year else reference.year
        if resolved_year < 100:
            resolved_year += 2000
        try:
            resolved = date(resolved_year, int(month), int(day))
            if year is None and resolved < reference.date():
                resolved = resolved.replace(year=resolved.year + 1)
            return resolved
        except ValueError:
            return None

    weekday_match = re.search(
        r"\bthu\s+(hai|ba|tu|nam|sau|bay|2|3|4|5|6|7|chu nhat|cn)\b",
        folded,
    )
    if weekday_match:
        weekdays = {
            "hai": 0,
            "2": 0,
            "ba": 1,
            "3": 1,
            "tu": 2,
            "4": 2,
            "nam": 3,
            "5": 3,
            "sau": 4,
            "6": 4,
            "bay": 5,
            "7": 5,
            "chu nhat": 6,
            "cn": 6,
        }
        target = weekdays[weekday_match.group(1)]
        delta = (target - reference.weekday()) % 7
        return reference.date() + timedelta(days=delta or 7)
    return None


def _calendar_time(query: str) -> time | None:
    folded = _fold(query)
    match = re.search(
        r"\b(?:luc|vao|truoc|at)\s+(\d{1,2})(?:[:h](\d{1,2}))?\b",
        folded,
    )
    if not match:
        match = re.search(r"\b(\d{1,2})h(?:(\d{1,2}))?\b", folded)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _calendar_summary(query: str) -> str:
    value = query.strip().rstrip(" .")
    patterns = (
        (
            r"^\s*(?:(?:hãy|vui lòng|giúp mình)\s+)?"
            r"(?:thêm|tạo|đặt|lên|nhắc)\s+"
        ),
        r"^\s*(?:task|việc|sự kiện)\s*[:\-]?\s*",
        (
            r"^\s*(?:vào|lên|trên)\s+"
            r"(?:(?:google|gg)\s*)?(?:calend[ae]r|lịch(?:\s+google)?)\s*"
        ),
        r"^\s*(?:cho\s+)?(?:tôi|mình)\s+",
        r"\s+(?:vào|lên|trên)\s+(?:(?:google|gg)\s*)?calend[ae]r\b",
        r"\s+(?:vào|lên|trên)\s+lịch(?:\s+google)?\b",
        r"\b(?:lúc|vào|trước)\s+\d{1,2}(?::\d{1,2}|h\d{0,2})?\b",
        r"\b\d{1,2}h(?:\d{1,2})?\b",
        r"\b(?:hôm nay|ngày mai|ngày kia)\b",
        r"\bngày\s+\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
        r"\b20\d{2}-\d{1,2}-\d{1,2}\b",
    )
    value = redact_emails(value)
    for pattern in patterns:
        value = re.sub(pattern, " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" ,;:-")
    return (value or "Việc cần làm")[:180]


def parse_calendar_event_draft(
    query: str,
    *,
    reference: datetime,
    time_zone: str = "Asia/Ho_Chi_Minh",
    duration_minutes: int = 60,
) -> CalendarEventDraft | None:
    if not calendar_requested(query):
        return None
    try:
        zone = ZoneInfo(time_zone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Asia/Ho_Chi_Minh")
        time_zone = "Asia/Ho_Chi_Minh"
    local_reference = reference.astimezone(zone)
    event_date = _calendar_date(query, local_reference)
    event_time = _calendar_time(query)
    if event_date is None and event_time is None:
        return None

    summary = _calendar_summary(query)
    description = (
        "Task được Trợ lý ZicZord đề xuất từ yêu cầu:\n"
        f"{redact_emails(query.strip())}"
    )
    if event_time is None:
        start_date = event_date
        if start_date is None:
            return None
        return CalendarEventDraft(
            summary=summary,
            description=description,
            time_zone=time_zone,
            all_day=True,
            start_date=start_date,
            end_date=start_date + timedelta(days=1),
        )

    if event_date is None:
        event_date = local_reference.date()
        tentative = datetime.combine(event_date, event_time, zone)
        if tentative <= local_reference:
            event_date += timedelta(days=1)
    start_at = datetime.combine(event_date, event_time, zone)
    end_at = start_at + timedelta(minutes=max(15, min(duration_minutes, 1440)))
    return CalendarEventDraft(
        summary=summary,
        description=description,
        time_zone=time_zone,
        all_day=False,
        start_at=start_at,
        end_at=end_at,
    )


class GoogleCalendarGateway:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.transport = transport
        self._credentials = None
        self._credential_lock = asyncio.Lock()

    @property
    def auth_mode(self) -> str:
        return self.settings.google_calendar_auth_mode

    @property
    def provider(self) -> str:
        if not self.configured:
            return "not-configured"
        if self.auth_mode == "oauth":
            return "google-calendar-oauth"
        return "google-calendar-service-account"

    @property
    def configured(self) -> bool:
        if not self.settings.google_calendar_id:
            return False
        if self.auth_mode == "oauth":
            token_file = self.settings.google_calendar_oauth_token_file
            return bool(
                self.settings.google_calendar_oauth_token_json
                or (token_file and token_file.is_file())
            )
        if self.auth_mode != "service-account":
            return False
        credential_file = self.settings.google_calendar_credentials_file
        has_credentials = bool(
            self.settings.google_calendar_credentials_json
            or (credential_file and credential_file.is_file())
        )
        return has_credentials

    def _load_credentials(self):
        if self.auth_mode == "oauth":
            raw: dict
            if self.settings.google_calendar_oauth_token_json:
                try:
                    raw = json.loads(
                        self.settings.google_calendar_oauth_token_json
                    )
                except json.JSONDecodeError as exc:
                    raise GoogleCalendarNotConfigured(
                        "GOOGLE_CALENDAR_OAUTH_TOKEN_JSON không phải JSON hợp lệ."
                    ) from exc
            elif (
                self.settings.google_calendar_oauth_token_file
                and self.settings.google_calendar_oauth_token_file.is_file()
            ):
                try:
                    raw = json.loads(
                        self.settings.google_calendar_oauth_token_file.read_text(
                            encoding="utf-8"
                        )
                    )
                except (OSError, json.JSONDecodeError) as exc:
                    raise GoogleCalendarNotConfigured(
                        "Không đọc được OAuth token của Google Calendar."
                    ) from exc
            else:
                raise GoogleCalendarNotConfigured(
                    "Google Calendar OAuth chưa được kết nối với organizer."
                )
            try:
                credentials = UserCredentials.from_authorized_user_info(
                    raw,
                    scopes=[CALENDAR_SCOPE],
                )
            except (KeyError, ValueError) as exc:
                raise GoogleCalendarNotConfigured(
                    "OAuth token Google Calendar cần refresh_token, client_id "
                    "và client_secret hợp lệ."
                ) from exc
            if not credentials.refresh_token:
                raise GoogleCalendarNotConfigured(
                    "OAuth token Google Calendar thiếu refresh_token. "
                    "Hãy chạy lại flow với offline access."
                )
            return credentials

        if self.auth_mode != "service-account":
            raise GoogleCalendarNotConfigured(
                "GOOGLE_CALENDAR_AUTH_MODE chỉ nhận oauth hoặc service-account."
            )
        if self.settings.google_calendar_credentials_json:
            try:
                info = json.loads(self.settings.google_calendar_credentials_json)
            except json.JSONDecodeError as exc:
                raise GoogleCalendarNotConfigured(
                    "GOOGLE_CALENDAR_CREDENTIALS_JSON không phải JSON hợp lệ."
                ) from exc
            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=[CALENDAR_SCOPE],
            )
        elif (
            self.settings.google_calendar_credentials_file
            and self.settings.google_calendar_credentials_file.is_file()
        ):
            credentials = service_account.Credentials.from_service_account_file(
                str(self.settings.google_calendar_credentials_file),
                scopes=[CALENDAR_SCOPE],
            )
        else:
            raise GoogleCalendarNotConfigured(
                "Thiếu service-account credentials cho Google Calendar."
            )
        if self.settings.google_calendar_delegated_user:
            credentials = credentials.with_subject(
                self.settings.google_calendar_delegated_user
            )
        return credentials

    async def _access_token(self) -> str:
        if not self.configured:
            raise GoogleCalendarNotConfigured(
                "Google Calendar chưa được cấu hình ở backend."
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
    def event_id(candidate_id: str) -> str:
        digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:32]
        return f"task{digest}"

    @staticmethod
    def _event_body(
        draft: CalendarEventDraft,
        candidate_id: str,
    ) -> dict:
        if draft.all_day:
            if not draft.start_date or not draft.end_date:
                raise ValueError("Task cả ngày cần start_date và end_date.")
            start = {"date": draft.start_date.isoformat()}
            end = {"date": draft.end_date.isoformat()}
        else:
            if not draft.start_at or not draft.end_at:
                raise ValueError("Task có giờ cần start_at và end_at.")
            if draft.end_at <= draft.start_at:
                raise ValueError("Thời điểm kết thúc phải sau thời điểm bắt đầu.")
            start = {
                "dateTime": draft.start_at.isoformat(),
                "timeZone": draft.time_zone,
            }
            end = {
                "dateTime": draft.end_at.isoformat(),
                "timeZone": draft.time_zone,
            }
        return {
            "id": GoogleCalendarGateway.event_id(candidate_id),
            "summary": draft.summary,
            "description": draft.description,
            "start": start,
            "end": end,
            **(
                {"attendees": [{"email": draft.attendee_email}]}
                if draft.attendee_email
                else {}
            ),
            "reminders": {"useDefault": True},
            "extendedProperties": {
                "private": {
                    "ziczordCandidateId": candidate_id,
                    "ziczordSource": "memory-candidate",
                }
            },
        }

    async def create_event(
        self,
        draft: CalendarEventDraft,
        *,
        candidate_id: str,
    ) -> dict:
        if (
            draft.attendee_email
            and self.auth_mode == "service-account"
            and not self.settings.google_calendar_delegated_user
        ):
            raise GoogleCalendarNotConfigured(
                "Gửi lời mời Calendar bằng service account cần cấu hình "
                "GOOGLE_CALENDAR_DELEGATED_USER và domain-wide delegation."
            )
        if (
            draft.attendee_email
            and self.auth_mode == "oauth"
            and not self.configured
        ):
            raise GoogleCalendarNotConfigured(
                "Google Calendar OAuth chưa được kết nối với organizer. "
                "Hãy chạy python -m app.google_calendar_oauth_setup."
            )
        token = await self._access_token()
        calendar_id = self.settings.google_calendar_id
        if not calendar_id:
            raise GoogleCalendarNotConfigured(
                "Thiếu GOOGLE_CALENDAR_ID ở backend."
            )
        event_id = self.event_id(candidate_id)
        collection_url = (
            f"{self.settings.google_calendar_api_base_url.rstrip('/')}/calendars/"
            f"{quote(calendar_id, safe='')}/events"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            timeout=20.0,
            transport=self.transport,
        ) as client:
            response = await client.post(
                collection_url,
                params={
                    "sendUpdates": "all" if draft.attendee_email else "none"
                },
                headers=headers,
                json=self._event_body(draft, candidate_id),
            )
            if response.status_code == 409:
                response = await client.get(
                    f"{collection_url}/{quote(event_id, safe='')}",
                    headers=headers,
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text[:500]
                raise GoogleCalendarError(
                    f"Google Calendar trả về HTTP {response.status_code}: {detail}"
                ) from exc
            payload = response.json()
        html_link = payload.get("htmlLink")
        if not isinstance(html_link, str) or not html_link:
            raise GoogleCalendarError("Google Calendar không trả về htmlLink.")
        return {
            "event_id": str(payload.get("id") or event_id),
            "html_link": html_link,
            "summary": draft.summary,
            "time_zone": draft.time_zone,
            "all_day": draft.all_day,
            "start_at": draft.start_at.isoformat() if draft.start_at else None,
            "end_at": draft.end_at.isoformat() if draft.end_at else None,
            "start_date": draft.start_date.isoformat() if draft.start_date else None,
            "end_date": draft.end_date.isoformat() if draft.end_date else None,
        }


class CalendarTaskService:
    def __init__(
        self,
        store: JsonStore,
        gateway: GoogleCalendarGateway,
        confirm_candidate,
    ):
        self.store = store
        self.gateway = gateway
        self.confirm_candidate = confirm_candidate

    @staticmethod
    def _authorized_candidate(
        snapshot: dict,
        candidate_id: str,
        user: CommunityUser,
    ) -> dict:
        candidate = next(
            (
                item
                for item in snapshot["candidates"]
                if item["id"] == candidate_id
            ),
            None,
        )
        if not candidate:
            raise KeyError(candidate_id)
        if candidate["created_by"] != user.id or not can_write_scope(
            user,
            candidate["scope_type"],
            candidate["scope_id"],
        ):
            raise PermissionError(candidate_id)
        if candidate["kind"] != "task" or not candidate.get("calendar_event"):
            raise ValueError("Candidate này chưa có lịch ngày/giờ hợp lệ.")
        return candidate

    def _stored_response(
        self,
        snapshot: dict,
        candidate_id: str,
        user: CommunityUser,
    ) -> CalendarTaskResponse | None:
        record = snapshot.get("calendar_events", {}).get(candidate_id)
        if not record:
            return None
        if record.get("created_by") != user.id or not can_write_scope(
            user,
            record.get("scope_type", ""),
            record.get("scope_id", ""),
        ):
            raise PermissionError(candidate_id)
        memory = next(
            (
                Memory.model_validate(item)
                for item in snapshot["memories"]
                if item["id"] == record["memory_id"]
            ),
            None,
        )
        if not memory:
            return None
        event_fields = {
            key: value
            for key, value in record.items()
            if key not in {
                "memory_id",
                "created_by",
                "scope_type",
                "scope_id",
            }
        }
        return CalendarTaskResponse(
            **event_fields,
            memory=memory,
        )

    async def sync_candidate(
        self,
        candidate_id: str,
        user: CommunityUser,
        attendee_email: str | None = None,
    ) -> CalendarTaskResponse:
        snapshot = self.store.snapshot()
        stored = self._stored_response(snapshot, candidate_id, user)
        if stored:
            return stored
        candidate = self._authorized_candidate(snapshot, candidate_id, user)
        draft = CalendarEventDraft.model_validate(candidate["calendar_event"])
        if attendee_email:
            draft = draft.model_copy(
                update={"attendee_email": attendee_email}
            )
        if not draft.attendee_email:
            raise ValueError(
                "Agent đang chờ email Google Calendar của người nhận."
            )
        event = await self.gateway.create_event(
            draft,
            candidate_id=candidate_id,
        )
        memory_id = (
            "mem-"
            + hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:10]
        )

        def remember_event(state: dict):
            state.setdefault("calendar_events", {})[candidate_id] = {
                **event,
                "memory_id": memory_id,
                "created_by": user.id,
                "scope_type": candidate["scope_type"],
                "scope_id": candidate["scope_id"],
            }
            return True

        self.store.mutate(remember_event)
        try:
            memory = await self.confirm_candidate(candidate_id, user)
        except KeyError:
            memory = next(
                (
                    Memory.model_validate(item)
                    for item in self.store.snapshot()["memories"]
                    if item["id"] == memory_id
                ),
                None,
            )
            if not memory:
                raise
        return CalendarTaskResponse(**event, memory=memory)
