from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, database, telegram_gateway, telegram_service
from app.telegram_gateway import load_telegram_user_map, split_telegram_text
from app.telegram_service import normalize_webhook_secret


client = TestClient(app)
TEST_WEBHOOK_SECRET = "telegram_test_secret"


def setup_function():
    client.post("/api/reset")


def telegram_update(
    update_id: int,
    *,
    telegram_user_id: int = 111222333,
    text: str | None = "Team mình đang chốt gì và còn blocker nào?",
    chat_type: str = "private",
) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id + 100,
            "from": {
                "id": telegram_user_id,
                "is_bot": False,
                "first_name": "An",
                "username": "an_test",
            },
            "chat": {
                "id": telegram_user_id if chat_type == "private" else -100987654,
                "type": chat_type,
                "title": None if chat_type == "private" else "Test group",
            },
            "text": text,
        },
    }


@pytest.fixture
def configured_telegram(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    user_map_path = tmp_path / "telegram-users.json"
    user_map_path.write_text(
        """
        {
          "users": [
            {
              "telegram_user_id": "111222333",
              "internal_user_id": "U01862",
              "enabled": true
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    telegram_settings = replace(
        settings,
        telegram_bot_token="123456:test-token",
        telegram_webhook_secret=TEST_WEBHOOK_SECRET,
        telegram_user_map_path=user_map_path,
        telegram_public_user_id=None,
    )
    monkeypatch.setattr(telegram_gateway, "settings", telegram_settings)
    monkeypatch.setattr(telegram_service, "settings", telegram_settings)
    send_mock = AsyncMock(return_value=[{"message_id": 9001}])
    log_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(telegram_gateway, "send_message", send_mock)
    monkeypatch.setattr(database, "log_chat_interaction", log_mock)
    return send_mock, log_mock


def post_update(payload: dict, secret: str = TEST_WEBHOOK_SECRET):
    return client.post(
        "/api/connectors/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json=payload,
    )


def test_health_reports_configured_telegram(configured_telegram):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["telegram_configured"] is True


def test_webhook_rejects_wrong_secret(configured_telegram):
    send_mock, _ = configured_telegram
    response = post_update(telegram_update(1001), secret="wrong-secret")
    assert response.status_code == 403
    send_mock.assert_not_awaited()


def test_private_question_is_answered_and_logged(configured_telegram):
    send_mock, log_mock = configured_telegram
    response = post_update(telegram_update(1002))

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    send_mock.assert_awaited_once()
    log_mock.assert_awaited_once()
    logged = log_mock.await_args.kwargs
    assert logged["source"] == "telegram"
    assert logged["external_user_id"] == "111222333"
    assert logged["demo_user_id"] == "U01862"
    assert logged["profile_id"] is None
    assert logged["question"] == "Team mình đang chốt gì và còn blocker nào?"


def test_duplicate_update_does_not_reply_twice(configured_telegram):
    send_mock, _ = configured_telegram
    payload = telegram_update(1003)
    assert post_update(payload).json()["accepted"] is True
    assert post_update(payload).json() == {
        "ok": True,
        "accepted": False,
        "reason": "duplicate",
    }
    send_mock.assert_awaited_once()


def test_unlinked_user_fails_closed(configured_telegram):
    send_mock, log_mock = configured_telegram
    response = post_update(telegram_update(1004, telegram_user_id=999888777))
    assert response.status_code == 200
    assert "chưa được liên kết" in send_mock.await_args.args[1]
    assert "999888777" in send_mock.await_args.args[1]
    log_mock.assert_not_awaited()


def test_group_chat_never_uses_private_context(configured_telegram):
    send_mock, log_mock = configured_telegram
    response = post_update(telegram_update(1005, chat_type="supergroup"))
    assert response.status_code == 200
    assert "chỉ trả lời trong chat riêng" in send_mock.await_args.args[1]
    log_mock.assert_not_awaited()


def test_user_map_rejects_duplicate_internal_identity(tmp_path: Path):
    path = tmp_path / "duplicate-map.json"
    path.write_text(
        """
        {
          "users": [
            {"telegram_user_id": "101", "internal_user_id": "U01862"},
            {"telegram_user_id": "202", "internal_user_id": "U01862"}
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="nhiều Telegram account"):
        load_telegram_user_map(path)


def test_long_answer_is_split_below_telegram_limit():
    chunks = split_telegram_text(("Đoạn trả lời có citation. " * 400).strip())
    assert len(chunks) > 1
    assert all(1 <= len(chunk) <= 4096 for chunk in chunks)


def test_webhook_secret_is_normalized_for_telegram():
    assert normalize_webhook_secret("legacy secret.with:punctuation") == (
        "legacy_secret_with_punctuation"
    )
