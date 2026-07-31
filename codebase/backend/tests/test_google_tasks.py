from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.google_tasks import deadline_due
from app.main import app


client = TestClient(app)


def setup_function():
    client.post("/api/reset")


def test_vietnamese_deadline_becomes_google_tasks_date():
    due = deadline_due(
        "trước 20h ngày mai",
        reference=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
        time_zone="Asia/Ho_Chi_Minh",
    )

    assert due is not None
    assert due.isoformat() == "2026-08-01T00:00:00+00:00"


def test_pitch_loader_is_idempotent_and_preserves_every_non_team_context():
    before = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()["discord_messages"]
    before_non_team = [
        message
        for message in before
        if message["channel_id"] != "team-t004"
    ]

    first = client.post(
        "/api/pitch/t004/context",
        params={"user_id": "U01862"},
    )
    second = client.post(
        "/api/pitch/t004/context",
        params={"user_id": "U01862"},
    )
    after = client.get(
        "/api/discord-state",
        params={"user_id": "U01862"},
    ).json()["discord_messages"]
    after_non_team = [
        message
        for message in after
        if message["channel_id"] != "team-t004"
    ]
    pitch_ids = [
        message["id"]
        for message in after
        if message["id"].startswith("pitch-t004-")
    ]

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["imported_count"] == 7
    assert before_non_team == after_non_team
    assert len(pitch_ids) == len(set(pitch_ids)) == 7
    forbidden = client.post(
        "/api/pitch/t004/context",
        params={"user_id": "U09999"},
    )
    assert forbidden.status_code == 403


def test_team_brief_and_google_task_are_locked_to_t004():
    loaded = client.post(
        "/api/pitch/t004/context",
        params={"user_id": "U01862"},
    )
    assert loaded.status_code == 200

    brief_response = client.post(
        "/api/pitch/t004/brief",
        params={"user_id": "U01862"},
    )
    assert brief_response.status_code == 200
    brief = brief_response.json()
    assert brief["scope_key"] == "team:T004"
    assert brief["items"]
    assert all(
        citation["channel_id"] == "team-t004"
        for item in brief["items"]
        for citation in item["citations"]
    )
    assert all(
        citation["message_id"].startswith("pitch-t004-")
        for item in brief["items"]
        for citation in item["citations"]
    )
    assert all(
        "ăn phở" not in item["detail"]
        for item in brief["items"]
    )

    actionable = next(
        item
        for item in brief["items"]
        if item["kind"] == "task"
    )
    endpoint = (
        f"/api/catch-up/{brief['id']}/items/"
        f"{actionable['id']}/google-task"
    )
    first = client.post(endpoint, params={"user_id": "U01862"})
    repeated = client.post(endpoint, params={"user_id": "U01862"})
    forbidden = client.post(endpoint, params={"user_id": "U09999"})

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert forbidden.status_code == 403
    task = first.json()
    assert task["scope_key"] == "team:T004"
    assert task["provider"] == "pitch-mock"
    assert task["title"].startswith("[T004]")
    assert repeated.json()["task_id"] == task["task_id"]
