import asyncio
from dataclasses import replace
from datetime import UTC, datetime
import json
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.google_calendar import (
    GoogleCalendarGateway,
    GoogleCalendarNotConfigured,
    parse_calendar_event_draft,
)
from app.main import app, database, google_calendar


client = TestClient(app)


def setup_function():
    client.post("/api/reset")


def test_vietnamese_calendar_request_becomes_timed_draft():
    draft = parse_calendar_event_draft(
        "Thêm task hoàn thiện slide vào Google Calendar lúc 20h ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )

    assert draft is not None
    assert draft.summary == "hoàn thiện slide"
    assert draft.all_day is False
    assert draft.start_at.isoformat() == "2026-08-01T20:00:00+07:00"
    assert draft.end_at.isoformat() == "2026-08-01T21:00:00+07:00"


def test_date_without_time_becomes_all_day_draft():
    draft = parse_calendar_event_draft(
        "Tạo việc nộp báo cáo lên lịch ngày 02/08/2026",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )

    assert draft is not None
    assert draft.summary == "nộp báo cáo"
    assert draft.all_day is True
    assert draft.start_date.isoformat() == "2026-08-02"
    assert draft.end_date.isoformat() == "2026-08-03"


def test_calendar_request_without_schedule_asks_for_clarification():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Thêm task hoàn thiện slide vào Google Calendar",
            "channel_id": "bot-commands",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate"] is None
    assert "cần bạn cho biết ngày hoặc giờ cụ thể" in payload["message"]["content"]
    assert payload["tool_calls"] == []


def test_misspelled_calender_request_stays_in_calendar_flow():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "thêm vào calender",
            "channel_id": "bot-commands",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "google-calendar-draft"
    assert payload["candidate"] is None
    assert "cần bạn cho biết ngày hoặc giờ cụ thể" in payload["message"]["content"]
    assert "[no-context]" not in payload["message"]["content"]


def test_misspelled_calender_request_builds_timed_draft():
    draft = parse_calendar_event_draft(
        "Thêm task kiểm tra demo vào calender lúc 9h ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )

    assert draft is not None
    assert draft.summary == "kiểm tra demo"
    assert draft.start_at.isoformat() == "2026-08-01T09:00:00+07:00"


def test_gateway_sends_events_insert_with_deterministic_id(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": body["id"],
                "htmlLink": "https://calendar.google.com/calendar/event?eid=test",
            },
        )

    configured = replace(
        settings,
        google_calendar_auth_mode="service-account",
        google_calendar_id="team@example.com",
        google_calendar_credentials_json="{}",
        google_calendar_delegated_user="organizer@example.com",
    )
    gateway = GoogleCalendarGateway(
        configured,
        transport=httpx.MockTransport(handler),
    )
    monkeypatch.setattr(
        gateway,
        "_access_token",
        AsyncMock(return_value="test-access-token"),
    )
    draft = parse_calendar_event_draft(
        "Thêm task kiểm tra demo vào gg calendar lúc 08:30 ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )
    draft = draft.model_copy(
        update={"attendee_email": "student@example.com"}
    )

    result = asyncio.run(
        gateway.create_event(draft, candidate_id="candidate-calendar-1")
    )

    assert result["event_id"] == gateway.event_id("candidate-calendar-1")
    assert result["start_at"] == "2026-08-01T08:30:00+07:00"
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].url.params["sendUpdates"] == "all"
    assert requests[0].headers["Authorization"] == "Bearer test-access-token"
    payload = json.loads(requests[0].content)
    assert payload["id"] == gateway.event_id("candidate-calendar-1")
    assert payload["start"] == {
        "dateTime": "2026-08-01T08:30:00+07:00",
        "timeZone": "Asia/Ho_Chi_Minh",
    }
    assert payload["attendees"] == [{"email": "student@example.com"}]
    assert payload["extendedProperties"]["private"]["ziczordCandidateId"] == (
        "candidate-calendar-1"
    )


def test_gateway_oauth_invites_without_domain_delegation(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": body["id"],
                "htmlLink": "https://calendar.google.com/calendar/event?eid=oauth",
            },
        )

    authorized_user = json.dumps(
        {
            "token": "expired-access-token",
            "refresh_token": "refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "oauth-client-id",
            "client_secret": "oauth-client-secret",
            "scopes": ["https://www.googleapis.com/auth/calendar.events"],
        }
    )
    configured = replace(
        settings,
        google_calendar_auth_mode="oauth",
        google_calendar_id="primary",
        google_calendar_oauth_token_json=authorized_user,
        google_calendar_oauth_token_file=None,
        google_calendar_delegated_user=None,
    )
    gateway = GoogleCalendarGateway(
        configured,
        transport=httpx.MockTransport(handler),
    )
    monkeypatch.setattr(
        gateway,
        "_access_token",
        AsyncMock(return_value="oauth-access-token"),
    )
    draft = parse_calendar_event_draft(
        "Nhắc tôi kiểm tra demo lúc 08:30 ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    ).model_copy(update={"attendee_email": "student@example.com"})

    result = asyncio.run(
        gateway.create_event(draft, candidate_id="candidate-oauth")
    )

    assert gateway.provider == "google-calendar-oauth"
    assert result["event_id"] == gateway.event_id("candidate-oauth")
    assert len(requests) == 1
    assert requests[0].url.params["sendUpdates"] == "all"
    assert json.loads(requests[0].content)["attendees"] == [
        {"email": "student@example.com"}
    ]


def test_health_marks_oauth_as_not_configured_until_token_exists(monkeypatch):
    oauth_settings = replace(
        google_calendar.settings,
        google_calendar_auth_mode="oauth",
        google_calendar_id="primary",
        google_calendar_oauth_token_json=None,
        google_calendar_oauth_token_file=None,
    )
    monkeypatch.setattr(google_calendar, "settings", oauth_settings)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["google_calendar_configured"] is False
    assert response.json()["google_calendar_provider"] == "not-configured"


def test_gateway_requires_delegation_before_inviting_attendee():
    configured = replace(
        settings,
        google_calendar_auth_mode="service-account",
        google_calendar_id="team@example.com",
        google_calendar_credentials_json="{}",
        google_calendar_delegated_user=None,
    )
    gateway = GoogleCalendarGateway(configured)
    draft = parse_calendar_event_draft(
        "Nhắc tôi kiểm tra demo lúc 08:30 ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    ).model_copy(update={"attendee_email": "student@example.com"})

    with pytest.raises(
        GoogleCalendarNotConfigured,
        match="domain-wide delegation",
    ):
        asyncio.run(
            gateway.create_event(draft, candidate_id="candidate-no-delegation")
        )


def test_chat_asks_for_email_then_sends_authorized_idempotent_invitation(
    monkeypatch,
):
    logged_interactions: list[dict] = []

    async def log_interaction(**values):
        logged_interactions.append(values)
        return True

    async def get_profile(profile_id):
        return {"profile_id": profile_id}

    monkeypatch.setattr(database, "log_chat_interaction", log_interaction)
    monkeypatch.setattr(database, "get_learner_profile", get_profile)
    create_event = AsyncMock(
        return_value={
            "event_id": "task-event-1",
            "html_link": "https://calendar.google.com/calendar/event?eid=test",
            "summary": "hoàn thiện slide",
            "time_zone": "Asia/Ho_Chi_Minh",
            "all_day": False,
            "start_at": "2026-08-01T20:00:00+07:00",
            "end_at": "2026-08-01T21:00:00+07:00",
            "start_date": None,
            "end_date": None,
        }
    )
    monkeypatch.setattr(google_calendar, "create_event", create_event)
    proposal = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Nhắc tôi hoàn thiện slide lúc 20h ngày mai",
            "channel_id": "bot-commands",
            "profile_id": "profile-calendar-test",
        },
    )
    candidate = proposal.json()["candidate"]

    assert proposal.status_code == 200
    assert candidate["calendar_event"]["summary"] == "hoàn thiện slide"
    assert candidate["calendar_event"]["attendee_email"] is None
    assert "Email Google dùng cho Calendar" in proposal.json()["message"]["content"]
    create_event.assert_not_awaited()
    forbidden = client.post(
        f"/api/memory-candidates/{candidate['id']}/google-calendar",
        params={"user_id": "U09999"},
    )
    assert forbidden.status_code == 403

    invalid_email = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "mail-cua-minh",
            "channel_id": "bot-commands",
            "profile_id": "profile-calendar-test",
        },
    )
    assert invalid_email.status_code == 200
    assert invalid_email.json()["candidate"]["id"] == candidate["id"]
    assert "chưa hợp lệ" in invalid_email.json()["message"]["content"]
    create_event.assert_not_awaited()

    sent = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Mail của mình là Student@Example.com",
            "channel_id": "bot-commands",
            "profile_id": "profile-calendar-test",
        },
    )
    repeated = client.post(
        f"/api/memory-candidates/{candidate['id']}/google-calendar",
        params={"user_id": "U01862"},
    )
    forbidden_after_sync = client.post(
        f"/api/memory-candidates/{candidate['id']}/google-calendar",
        params={"user_id": "U09999"},
    )

    assert sent.status_code == 200
    assert sent.json()["candidate"] is None
    assert sent.json()["sensitive_input_consumed"] is True
    assert sent.json()["provider"] == "google-calendar-invitation"
    assert "Đã gửi lời mời" in sent.json()["message"]["content"]
    assert repeated.status_code == 200
    assert forbidden_after_sync.status_code == 403
    assert repeated.json()["event_id"] == "task-event-1"
    assert repeated.json()["memory"]["kind"] == "task"
    create_event.assert_awaited_once()
    created_draft = create_event.await_args.args[0]
    assert created_draft.attendee_email == "student@example.com"

    state = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()
    serialized_state = json.dumps(state, ensure_ascii=False)
    assert "student@example.com" not in serialized_state.casefold()
    assert "[Email Google Calendar đã cung cấp]" in serialized_state
    assert logged_interactions[-1]["question"] == (
        "[Email Google Calendar đã cung cấp]"
    )
    assert "student@example.com" not in json.dumps(
        logged_interactions,
        ensure_ascii=False,
    ).casefold()


def test_failed_invitation_clears_email_and_candidate_can_be_dismissed(
    monkeypatch,
):
    monkeypatch.setattr(
        google_calendar,
        "create_event",
        AsyncMock(
            side_effect=GoogleCalendarNotConfigured(
                "Thiếu domain-wide delegation."
            )
        ),
    )
    proposal = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Nhắc tôi nộp báo cáo lúc 9h ngày mai",
            "channel_id": "bot-commands",
        },
    ).json()
    candidate_id = proposal["candidate"]["id"]

    failed = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "student@example.com",
            "channel_id": "bot-commands",
        },
    )

    assert failed.status_code == 200
    payload = failed.json()
    assert payload["provider"] == "google-calendar-invitation-error"
    assert payload["candidate"]["calendar_event"]["attendee_email"] is None
    state = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()
    assert "student@example.com" not in json.dumps(state).casefold()

    dismissed = client.delete(
        f"/api/memory-candidates/{candidate_id}",
        params={"user_id": "U01862"},
    )
    assert dismissed.status_code == 204
    state_after = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()
    assert all(item["id"] != candidate_id for item in state_after["candidates"])

    orphan_email = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "student@example.com",
            "channel_id": "bot-commands",
        },
    )
    assert orphan_email.status_code == 200
    assert orphan_email.json()["provider"] == (
        "google-calendar-no-pending-request"
    )
    final_state = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()
    assert "student@example.com" not in json.dumps(final_state).casefold()
