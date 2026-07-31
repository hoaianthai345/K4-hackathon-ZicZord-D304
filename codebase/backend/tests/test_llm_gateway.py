import asyncio
from datetime import UTC, datetime

import httpx

from app.config import Settings
from app.llm_gateway import LLMGateway
from app.schemas import CommunityUser, DiscordMessage


def configured_settings() -> Settings:
    return Settings(
        openrouter_api_key=None,
        openrouter_api_key_phuc="brief-key",
        openrouter_api_key_khang="chat-key",
        openrouter_api_key_trinh="rag-key",
        groq_api_key=None,
    )


def test_chat_flow_fails_over_from_rate_limited_khang_to_trinh(monkeypatch):
    gateway = LLMGateway(configured_settings())
    calls: list[str] = []

    async def fake_request(**kwargs):
        calls.append(kwargs["api_key"])
        if kwargs["api_key"] == "chat-key":
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(
                429,
                headers={"Retry-After": "60"},
                request=request,
            )
            raise httpx.HTTPStatusError(
                "rate limited",
                request=request,
                response=response,
            )
        return "Câu trả lời [S1]"

    monkeypatch.setattr(gateway, "_request_completion", fake_request)

    result = asyncio.run(gateway._complete("system", "user", flow="chat"))

    assert result == "Câu trả lời [S1]"
    assert calls == ["chat-key", "rag-key"]
    assert gateway.openrouter_pool.state()["khang"]["available"] is False
    assert gateway.last_provider == "openrouter-pool:chat:qwen/qwen3.6-27b"


def test_daily_brief_rejects_hallucinated_owner_and_deadline(monkeypatch):
    gateway = LLMGateway(configured_settings())
    user = CommunityUser(
        id="U1",
        discord_user_id="discord-u1",
        name="An",
        member_label="T001",
        role="student",
        cohort_id="K4",
        team_id="T001",
        group_id="G1",
    )
    message = DiscordMessage(
        id="m1",
        source_message_id="m1",
        channel_id="general",
        author_id="U2",
        author_name="Lan",
        content="Team chốt làm demo memory trước 18h.",
        created_at=datetime(2026, 7, 31, tzinfo=UTC),
        permalink="https://discord.test/m1",
    )

    async def fake_complete(*args, **kwargs):
        gateway.last_provider = "openrouter-pool:brief:qwen/qwen3.6-27b"
        return """
        {"items":[{
          "message_id":"m1",
          "kind":"task",
          "title":"Hoàn thiện demo memory",
          "owner":"Người không có trong nguồn",
          "deadline":"20h",
          "status":"open"
        }]}
        """

    monkeypatch.setattr(gateway, "_complete", fake_complete)

    items = asyncio.run(gateway.build_daily_brief(user, [message], 24))

    assert items is not None
    assert items[0]["owner"] is None
    assert items[0]["deadline"] is None
    assert items[0]["message_id"] == "m1"
