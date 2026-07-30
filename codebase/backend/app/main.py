from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .apify_gateway import ApifyGateway, normalize_apify_item
from .chat_service import ChatService
from .config import settings
from .hindsight_gateway import HindsightGateway
from .llm_gateway import LLMGateway
from .schemas import (
    ApifyIngestRequest,
    ApifyIngestResponse,
    ChatRequest,
    ChatResponse,
    CommunityUser,
    DiscordMessage,
    DiscordState,
    HealthResponse,
    IngestionStatus,
    Memory,
    MemoryUpdate,
)
from .scopes import (
    allowed_scope_keys,
    can_access_channel,
    channel_record,
    scope_descriptors,
    user_record,
    visible_channels,
)
from .seed import USERS
from .store import JsonStore


store = JsonStore(settings.state_path)
hindsight = HindsightGateway(settings)
apify = ApifyGateway(settings)
llm = LLMGateway(settings)
chat_service = ChatService(store, hindsight, llm)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.state_path.parent.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Discord learning copilot with authorization-aware user, team, group, "
        "classroom and cohort memory."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user(user_id: str) -> CommunityUser:
    user = user_record(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên demo.")
    return user


def _permission_error() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail="Tài khoản này không có quyền thay đổi memory của scope đó.",
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    provider = hindsight.status()
    ai = llm.status()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        memory_provider=provider.name,
        hindsight_reachable=provider.reachable,
        ai_provider=ai.name,
        ai_reachable=ai.reachable,
        ingestion_mode="apify" if apify.configured else "demo-snapshot",
    )


@app.get("/api/users", response_model=list[CommunityUser])
def list_users() -> list[CommunityUser]:
    return [CommunityUser.model_validate(user) for user in USERS]


@app.get("/api/discord-state", response_model=DiscordState)
def discord_state(user_id: str = Query(default="U01862")) -> DiscordState:
    user = get_user(user_id)
    snapshot = store.snapshot()
    allowed = allowed_scope_keys(user)
    channels = visible_channels(user)
    visible_channel_ids = {channel.id for channel in channels}
    messages = [
        DiscordMessage.model_validate(item)
        for item in snapshot["discord_messages"]
        if item["channel_id"] in visible_channel_ids
    ]
    memories = [
        item
        for item in snapshot["memories"]
        if (item["scope_type"], item["scope_id"]) in allowed
    ]
    candidates = [
        item
        for item in snapshot["candidates"]
        if item["created_by"] == user_id
        and (item["scope_type"], item["scope_id"]) in allowed
    ]
    return DiscordState(
        user=user,
        users=[CommunityUser.model_validate(item) for item in USERS],
        scopes=scope_descriptors(user),
        channels=channels,
        discord_messages=sorted(messages, key=lambda item: item.created_at),
        memories=memories,
        candidates=candidates,
        assistant_messages=snapshot["assistant_messages"].get(user_id, []),
        suggested_prompts=[
            "Tóm tắt nội dung bài giảng ngày hôm qua",
            "Team mình đang chốt gì và còn blocker nào?",
            "Mentor G10 dặn gì trước buổi check-in?",
            "Tóm tắt kênh chat chính hôm nay",
        ],
        provider=llm.status().name,
        ingestion=IngestionStatus.model_validate(snapshot["ingestion"]),
    )


# Compatibility alias for older demo links.
@app.get("/api/demo-state", response_model=DiscordState)
def demo_state_alias(user_id: str = Query(default="U01862")) -> DiscordState:
    return discord_state(user_id)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    user = get_user(payload.user_id)
    channel = channel_record(payload.channel_id)
    if channel and not can_access_channel(user, channel):
        raise HTTPException(status_code=403, detail="Bạn không có quyền dùng channel này.")
    return await chat_service.chat(user, payload.message, payload.channel_id)


@app.post("/api/memory-candidates/{candidate_id}/confirm", response_model=Memory)
async def confirm_candidate(
    candidate_id: str,
    user_id: str = Query(default="U01862"),
) -> Memory:
    user = get_user(user_id)
    try:
        return await chat_service.confirm_candidate(candidate_id, user)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Gợi ý ghi nhớ không còn tồn tại.",
        ) from exc
    except PermissionError as exc:
        raise _permission_error() from exc


@app.patch("/api/memories/{memory_id}", response_model=Memory)
async def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    user_id: str = Query(default="U01862"),
) -> Memory:
    user = get_user(user_id)
    try:
        return await chat_service.update_memory(memory_id, payload.content, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy memory.") from exc
    except PermissionError as exc:
        raise _permission_error() from exc


@app.delete("/api/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    user_id: str = Query(default="U01862"),
) -> Response:
    user = get_user(user_id)
    try:
        await chat_service.delete_memory(memory_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy memory.") from exc
    except PermissionError as exc:
        raise _permission_error() from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/ingest/apify", response_model=ApifyIngestResponse)
async def ingest_apify(payload: ApifyIngestRequest) -> ApifyIngestResponse:
    dataset_id = payload.dataset_id or settings.apify_dataset_id
    if not dataset_id:
        raise HTTPException(
            status_code=409,
            detail="Thiếu APIFY_DATASET_ID. Demo hiện đang dùng snapshot cục bộ.",
        )
    try:
        raw_items = await apify.fetch_items(dataset_id, payload.max_items)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Apify trả về lỗi HTTP {exc.response.status_code}.",
        ) from exc
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    normalized = [value for item in raw_items if (value := normalize_apify_item(item))]
    counters = {"imported": 0, "duplicates": 0}
    synced_at = datetime.now(UTC)

    def operation(state: dict):
        existing = {
            item["source_message_id"] for item in state["discord_messages"]
        }
        for message in normalized:
            if message.source_message_id in existing:
                counters["duplicates"] += 1
                continue
            state["discord_messages"].append(message.model_dump(mode="json"))
            existing.add(message.source_message_id)
            counters["imported"] += 1
        state["ingestion"] = {
            "mode": "apify",
            "dataset_id": dataset_id,
            "last_synced_at": synced_at.isoformat(),
            "imported_count": counters["imported"],
            "skipped_count": len(raw_items) - len(normalized),
        }
        return state["ingestion"]

    store.mutate(operation)
    return ApifyIngestResponse(
        imported_count=counters["imported"],
        skipped_count=len(raw_items) - len(normalized),
        duplicate_count=counters["duplicates"],
        dataset_id=dataset_id,
        last_synced_at=synced_at,
    )


@app.post("/api/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_demo() -> Response:
    store.reset()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
