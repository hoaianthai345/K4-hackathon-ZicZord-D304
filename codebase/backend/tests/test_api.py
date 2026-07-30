import os
from pathlib import Path

os.environ["MEMORY_PROVIDER"] = "local"
os.environ["STATE_PATH"] = str(Path("/tmp") / "kute-discord-test.json")

from fastapi.testclient import TestClient

from app.apify_gateway import normalize_apify_item
from app.main import app


client = TestClient(app)


def setup_function():
    client.post("/api/reset")


def test_health_and_discord_state_expose_hierarchy():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["memory_provider"] == "local-demo"

    response = client.get("/api/discord-state", params={"user_id": "U01862"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["team_id"] == "T004"
    assert {(scope["type"], scope["id"]) for scope in payload["scopes"]} == {
        ("user", "U01862"),
        ("team", "T004"),
        ("group", "G10"),
        ("room", "LEC-D302"),
        ("room", "LAB-D304"),
        ("cohort", "K4"),
    }
    assert "team-t009" not in {channel["id"] for channel in payload["channels"]}


def test_team_memory_and_messages_are_isolated():
    thai = client.get("/api/discord-state", params={"user_id": "U01862"}).json()
    lan = client.get("/api/discord-state", params={"user_id": "U09999"}).json()

    thai_memories = {memory["id"] for memory in thai["memories"]}
    lan_memories = {memory["id"] for memory in lan["memories"]}
    assert "mem-team-t004-stack" in thai_memories
    assert "mem-team-t009-private" not in thai_memories
    assert "mem-team-t009-private" in lan_memories
    assert "mem-team-t004-stack" not in lan_memories

    thai_channels = {message["channel_id"] for message in thai["discord_messages"]}
    lan_channels = {message["channel_id"] for message in lan["discord_messages"]}
    assert "team-t009" not in thai_channels
    assert "team-t004" not in lan_channels


def test_chat_summary_has_discord_citations():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Team mình đang chốt gì và còn blocker nào?",
            "channel_id": "bot-commands",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["message"]["citations"]) >= 2
    assert all(
        citation["channel_id"] == "team-t004"
        for citation in payload["message"]["citations"]
    )
    assert "T009" not in payload["message"]["content"]


def test_candidate_can_be_confirmed_only_by_creator_scope():
    response = client.post(
        "/api/chat",
        json={
            "user_id": "U01862",
            "message": "Team mình chốt demo scope memory trước 18h.",
            "channel_id": "team-t004",
        },
    )
    assert response.status_code == 200
    candidate = response.json()["candidate"]
    assert candidate["scope_type"] == "team"
    assert candidate["scope_id"] == "T004"

    forbidden = client.post(
        f"/api/memory-candidates/{candidate['id']}/confirm",
        params={"user_id": "U09999"},
    )
    assert forbidden.status_code == 403

    confirmed = client.post(
        f"/api/memory-candidates/{candidate['id']}/confirm",
        params={"user_id": "U01862"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["scope_id"] == "T004"


def test_apify_item_normalizer_fails_closed_for_unknown_channel():
    item = {
        "messageId": "123",
        "channelId": "dc-team-t004",
        "author": {"id": "discord-01862", "username": "an"},
        "content": "Team chốt API contract.",
        "timestamp": "2026-07-30T08:00:00Z",
        "url": "https://discord.com/channels/demo/dc-team-t004/123",
    }
    normalized = normalize_apify_item(item)
    assert normalized is not None
    assert normalized.channel_id == "team-t004"
    assert normalized.author_id == "U01862"

    item["channelId"] = "private-unknown-channel"
    assert normalize_apify_item(item) is None


def test_ingest_endpoint_requires_configured_dataset():
    response = client.post("/api/ingest/apify", json={"max_items": 20})
    assert response.status_code == 409
