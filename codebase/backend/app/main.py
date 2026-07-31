from contextlib import asynccontextmanager
from datetime import UTC, datetime
import hmac
import json
from typing import Literal
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from .apify_gateway import ApifyGateway, normalize_apify_item
from .chat_service import ChatService
from .catchup_service import CatchupService
from .config import settings
from .context_tools import ContextToolService
from .database import Database
from .evaluation_service import EvaluationService
from .hindsight_gateway import HindsightGateway
from .llm_gateway import LLMGateway
from .rag_anything_gateway import RAGAnythingGateway
from .schemas import (
    AdminContextList,
    AdminContextUpdate,
    AdminMemoryCreate,
    AdminMemoryUpdate,
    AdminOverview,
    ApifyIngestRequest,
    ApifyIngestResponse,
    ChatRequest,
    ChatResponse,
    CatchupBrief,
    CatchupRequest,
    ChecklistItem,
    ChecklistUpdate,
    CommunityUser,
    ContextPlanRequest,
    ContextPlanResponse,
    ContextToolCall,
    DiscordMessage,
    DiscordState,
    HealthResponse,
    IngestionStatus,
    LearnerProfile,
    LearnerProfileCreate,
    Memory,
    MemoryUpdate,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSource,
    RAGSourceRecord,
    TelegramUpdate,
    TelegramWebhookAck,
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
from .telegram_gateway import TelegramGateway
from .telegram_service import TelegramService


store = JsonStore(settings.state_path)
hindsight = HindsightGateway(settings)
apify = ApifyGateway(settings)
llm = LLMGateway(settings)
database = Database(settings)
rag = RAGAnythingGateway(settings)
context_tools = ContextToolService(database)
chat_service = ChatService(store, hindsight, llm, rag, context_tools)
catchup_service = CatchupService(
    store,
    llm,
    database,
    settings.api_public_url,
)
evaluation = EvaluationService(settings, chat_service)
telegram_gateway = TelegramGateway(settings)
telegram_service = TelegramService(
    settings,
    store,
    chat_service,
    telegram_gateway,
    database,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.state_path.parent.mkdir(parents=True, exist_ok=True)
    if database.configured:
        try:
            await database.ensure_schema()
        except Exception:
            # Keep the existing demo API available while PostgreSQL is recovering.
            pass
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Discord catch-up copilot that turns authorized messages into decisions, "
        "tasks, deadlines and blockers with verifiable citations."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
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


def require_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None),
) -> None:
    if not settings.admin_api_key:
        if request.url.hostname in {"localhost", "127.0.0.1", "testserver"}:
            return
        raise HTTPException(
            status_code=503,
            detail="Admin public đang tắt. Hãy cấu hình ADMIN_API_KEY ở backend.",
        )
    if not x_admin_key or not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=401,
            detail="Admin key không hợp lệ.",
            headers={"WWW-Authenticate": "X-Admin-Key"},
        )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    provider = hindsight.status()
    ai = llm.status()
    database_status = await database.status()
    rag_status = await rag.status()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        memory_provider=provider.name,
        hindsight_reachable=provider.reachable,
        ai_provider=ai.name,
        ai_reachable=ai.reachable,
        ingestion_mode="apify" if apify.configured else "demo-snapshot",
        database_reachable=database_status.reachable,
        database_messages=database_status.messages,
        database_episodes=database_status.episodes,
        database_painpoints=database_status.painpoints,
        database_learning_contexts=database_status.learning_contexts,
        rag_reachable=rag_status["reachable"],
        rag_indexed_scopes=rag_status["indexed_scopes"],
        telegram_configured=telegram_service.configured,
    )


@app.get("/api/users", response_model=list[CommunityUser])
def list_users() -> list[CommunityUser]:
    return [CommunityUser.model_validate(user) for user in USERS]


@app.get("/api/learner-profiles/{profile_id}", response_model=LearnerProfile)
async def get_learner_profile(profile_id: str) -> LearnerProfile:
    profile = await database.get_learner_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ học viên.")
    return LearnerProfile.model_validate(profile)


@app.post("/api/learner-profiles", response_model=LearnerProfile)
async def create_learner_profile(
    payload: LearnerProfileCreate,
) -> LearnerProfile:
    get_user(payload.demo_user_id)
    full_name = " ".join(payload.full_name.split())
    if len(full_name) < 2:
        raise HTTPException(status_code=422, detail="Họ tên chưa hợp lệ.")
    try:
        profile = await database.upsert_learner_profile(
            profile_id=f"profile-{uuid4().hex}",
            full_name=full_name,
            student_id_last5=payload.student_id_last5,
            demo_user_id=payload.demo_user_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Chưa kết nối được database hồ sơ.",
        ) from exc
    return LearnerProfile.model_validate(profile)


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
            "Bắt kịp 24 giờ qua",
            "Quyết định nào mới được chốt?",
            "Việc nào đang giao cho mình?",
            "Deadline và blocker hiện tại là gì?",
            "Mentor G10 có thông báo quan trọng nào?",
            "Giảng viên giải thích Transformer và attention như thế nào?",
        ],
        provider=llm.status().name,
        ingestion=IngestionStatus.model_validate(snapshot["ingestion"]),
        checklist=snapshot["checklists"].get(user_id, []),
    )


# Compatibility alias for older demo links.
@app.get("/api/demo-state", response_model=DiscordState)
def demo_state_alias(user_id: str = Query(default="U01862")) -> DiscordState:
    return discord_state(user_id)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    user = get_user(payload.user_id)
    if payload.profile_id and database.configured:
        profile = await database.get_learner_profile(payload.profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Hồ sơ học viên không còn tồn tại.")
    channel = channel_record(payload.channel_id)
    if channel and not can_access_channel(user, channel):
        raise HTTPException(status_code=403, detail="Bạn không có quyền dùng channel này.")
    response = await chat_service.chat(user, payload.message, payload.channel_id)
    if payload.profile_id:
        await database.log_chat_interaction(
            interaction_id=f"chat-{uuid4().hex}",
            profile_id=payload.profile_id,
            demo_user_id=user.id,
            channel_id=payload.channel_id,
            source="web",
            question=payload.message,
            answer=response.message.content,
            provider=response.provider,
            citations=[
                citation.model_dump(mode="json")
                for citation in response.message.citations
            ],
            tool_calls=[
                tool_call.model_dump(mode="json")
                for tool_call in response.tool_calls
            ],
        )
    return response


@app.post(
    "/api/connectors/telegram/webhook",
    response_model=TelegramWebhookAck,
)
async def telegram_webhook(
    payload: TelegramUpdate,
    background_tasks: BackgroundTasks,
    webhook_secret: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> TelegramWebhookAck:
    if not telegram_service.configured:
        raise HTTPException(
            status_code=503,
            detail="Connector Telegram chưa được cấu hình.",
        )
    if not telegram_service.verify_webhook_secret(webhook_secret):
        raise HTTPException(status_code=403, detail="Telegram webhook secret sai.")
    if not telegram_service.claim_update(payload.update_id):
        return TelegramWebhookAck(accepted=False, reason="duplicate")
    background_tasks.add_task(telegram_service.process_update, payload)
    return TelegramWebhookAck(accepted=True, reason="accepted")


@app.post("/api/rag/query", response_model=RAGQueryResponse)
async def query_rag(payload: RAGQueryRequest) -> RAGQueryResponse:
    user = get_user(payload.user_id)
    result = await rag.query(user, payload.query)
    if not result:
        raise HTTPException(
            status_code=503,
            detail="RAG-Anything chưa sẵn sàng hoặc chưa index scope của user.",
        )
    sources = [
        RAGSource(
            source_id=source.source_id,
            source_type=source.source_type,
            channel_key=source.channel_key,
            label=source.label,
            citation_url=(
                f"{settings.api_public_url}/api/rag/sources/"
                f"{quote(source.source_type, safe='')}/"
                f"{quote(source.source_id, safe='')}?"
                f"user_id={quote(user.id, safe='')}"
            ),
        )
        for source in result.sources
    ]
    return RAGQueryResponse(
        query=payload.query,
        answer=result.answer,
        provider=result.provider,
        scopes_queried=result.scopes_queried,
        sources=sources,
    )


@app.get(
    "/api/rag/sources/{source_type}/{source_id}",
    response_model=RAGSourceRecord,
)
async def rag_source(
    source_type: Literal["message", "episode", "painpoint", "lesson"],
    source_id: str,
    user_id: str = Query(default="U01862"),
) -> RAGSourceRecord:
    user = get_user(user_id)
    record = await database.source(source_type, source_id)
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy RAG source.")
    allowed = {
        f"{scope_type}:{scope_id}"
        for scope_type, scope_id in allowed_scope_keys(user)
    }
    if record["scope_key"] not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản này không có quyền xem source đó.",
        )
    return RAGSourceRecord.model_validate(record)


@app.get("/api/admin/overview", response_model=AdminOverview)
async def admin_overview(
    _: None = Depends(require_admin),
) -> AdminOverview:
    context = await database.admin_context_overview()
    snapshot = store.snapshot()
    memory_by_scope: dict[str, int] = {}
    for memory in snapshot["memories"]:
        scope_key = f"{memory['scope_type']}:{memory['scope_id']}"
        memory_by_scope[scope_key] = memory_by_scope.get(scope_key, 0) + 1
    rag_status = await rag.status()
    return AdminOverview(
        context_total=context["total"],
        context_enabled=context["enabled"],
        context_by_type={
            key: int(value) for key, value in context["by_type"].items()
        },
        context_by_scope=context["by_scope"],
        memory_total=len(snapshot["memories"]),
        memory_by_scope=memory_by_scope,
        rag_reachable=rag_status["reachable"],
        rag_indexed_scopes=rag_status["indexed_scopes"],
        admin_auth_required=bool(settings.admin_api_key),
    )


@app.get("/api/admin/evaluation")
def admin_evaluation(
    _: None = Depends(require_admin),
) -> dict:
    try:
        return evaluation.overview()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/admin/evaluation/run", status_code=status.HTTP_202_ACCEPTED)
async def admin_run_evaluation(
    save_as_baseline: bool = Query(default=False),
    _: None = Depends(require_admin),
) -> dict:
    try:
        evaluation.load_suite()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return evaluation.start(save_as_baseline=save_as_baseline)


@app.post("/api/admin/evaluation/cases/{case_id}/run")
async def admin_run_evaluation_case(
    case_id: str,
    _: None = Depends(require_admin),
) -> dict:
    try:
        return await evaluation.execute_case_by_id(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy eval case.") from exc
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/admin/context", response_model=AdminContextList)
async def admin_context(
    search: str = Query(default="", max_length=200),
    source_type: Literal["message", "episode", "painpoint", "lesson"] | None = None,
    scope_key: str | None = Query(default=None, max_length=100),
    enabled: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin),
) -> AdminContextList:
    items, total = await database.admin_list_context(
        search=search,
        source_type=source_type,
        scope_key=scope_key,
        enabled=enabled,
        limit=limit,
        offset=offset,
    )
    return AdminContextList(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.patch(
    "/api/admin/context/{source_type}/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_update_context(
    source_type: Literal["message", "episode", "painpoint", "lesson"],
    source_id: str,
    payload: AdminContextUpdate,
    _: None = Depends(require_admin),
) -> Response:
    updated = await database.admin_set_context_enabled(
        source_type,
        source_id,
        payload.is_enabled,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy context record.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/admin/context/plan", response_model=ContextPlanResponse)
async def admin_context_plan(
    payload: ContextPlanRequest,
    _: None = Depends(require_admin),
) -> ContextPlanResponse:
    user = get_user(payload.user_id)
    retrieval = await context_tools.retrieve(
        user,
        payload.query,
        payload.channel_id,
    )
    sources = []
    for source in retrieval.sources:
        metadata = {
            **(source.get("metadata") or {}),
            "source_kind": source.get("source_kind"),
            "source_ref": source.get("source_ref"),
            "title": source.get("title"),
            "day_code": source.get("day_code"),
            "sequence_number": source.get("sequence_number"),
            "page_number": source.get("page_number"),
        }
        sources.append(
            RAGSourceRecord(
                source_id=str(source["source_id"]),
                source_type=source["source_type"],
                channel_key=str(source["channel_key"]),
                scope_key=str(source["scope_key"]),
                content=str(source["content"]),
                created_at=source.get("created_at"),
                metadata={key: value for key, value in metadata.items() if value is not None},
            )
        )
    return ContextPlanResponse(
        query=payload.query,
        filters={
            "channels": retrieval.plan.channel_keys,
            "day_codes": retrieval.plan.day_codes,
            "source_kinds": retrieval.plan.source_kinds,
            "start_time": (
                retrieval.plan.start_time.isoformat()
                if retrieval.plan.start_time
                else None
            ),
            "end_time": (
                retrieval.plan.end_time.isoformat()
                if retrieval.plan.end_time
                else None
            ),
            "time_label": retrieval.plan.time_label,
            "current_date": retrieval.temporal_context.get("current_date"),
            "requested_date": retrieval.temporal_context.get("requested_date"),
            "context_start": retrieval.temporal_context.get("context_start"),
            "context_end": retrieval.temporal_context.get("context_end"),
            "lesson_intent": retrieval.plan.lesson_intent,
            "use_rag": retrieval.plan.use_rag,
            "use_memory": retrieval.plan.use_memory,
        },
        notes=retrieval.plan.notes,
        tool_calls=[
            ContextToolCall(
                name=call.name,
                arguments=call.arguments,
                reason=call.reason,
                result_count=call.result_count,
            )
            for call in retrieval.calls
        ],
        sources=sources,
    )


@app.post("/api/admin/context/reindex")
async def admin_reindex_context(
    _: None = Depends(require_admin),
) -> dict:
    try:
        return await rag.index()
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/admin/memories", response_model=list[Memory])
def admin_memories(
    scope_type: str | None = Query(default=None, max_length=20),
    scope_id: str | None = Query(default=None, max_length=80),
    _: None = Depends(require_admin),
) -> list[Memory]:
    values = store.snapshot()["memories"]
    return [
        Memory.model_validate(memory)
        for memory in values
        if (scope_type is None or memory["scope_type"] == scope_type)
        and (scope_id is None or memory["scope_id"] == scope_id)
    ]


@app.post("/api/admin/memories", response_model=Memory)
async def admin_create_memory(
    payload: AdminMemoryCreate,
    _: None = Depends(require_admin),
) -> Memory:
    timestamp = datetime.now(UTC)
    memory = Memory(
        id=f"mem-admin-{uuid4().hex[:10]}",
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        kind=payload.kind,
        content=payload.content.strip(),
        evidence=payload.evidence,
        created_by=payload.created_by,
        created_at=timestamp,
        updated_at=timestamp,
    )

    def operation(state: dict):
        state["memories"].append(memory.model_dump(mode="json"))
        return True

    store.mutate(operation)
    await hindsight.retain_confirmed(memory)
    return memory


@app.patch("/api/admin/memories/{memory_id}", response_model=Memory)
async def admin_update_memory(
    memory_id: str,
    payload: AdminMemoryUpdate,
    _: None = Depends(require_admin),
) -> Memory:
    updated: dict = {}

    def operation(state: dict):
        memory = next(
            (item for item in state["memories"] if item["id"] == memory_id),
            None,
        )
        if not memory:
            raise KeyError(memory_id)
        changes = payload.model_dump(exclude_none=True)
        for key, value in changes.items():
            memory[key] = value.strip() if key == "content" else value
        memory["updated_at"] = datetime.now(UTC).isoformat()
        updated.update(memory)
        return True

    try:
        store.mutate(operation)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy memory.") from exc
    memory = Memory.model_validate(updated)
    await hindsight.retain_confirmed(memory)
    return memory


@app.delete(
    "/api/admin/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_memory(
    memory_id: str,
    _: None = Depends(require_admin),
) -> Response:
    deleted: dict = {}

    def operation(state: dict):
        memory = next(
            (item for item in state["memories"] if item["id"] == memory_id),
            None,
        )
        if not memory:
            raise KeyError(memory_id)
        deleted.update(memory)
        state["memories"] = [
            item for item in state["memories"] if item["id"] != memory_id
        ]
        return True

    try:
        store.mutate(operation)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy memory.") from exc
    await hindsight.delete_confirmed(Memory.model_validate(deleted))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/catch-up", response_model=CatchupBrief)
async def create_catchup(payload: CatchupRequest) -> CatchupBrief:
    user = get_user(payload.user_id)
    try:
        return await catchup_service.generate(
            user,
            payload.window_hours,
            payload.scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/api/catch-up/{brief_id}/checklist",
    response_model=list[ChecklistItem],
)
def create_checklist(
    brief_id: str,
    user_id: str = Query(default="U01862"),
) -> list[ChecklistItem]:
    user = get_user(user_id)
    try:
        return catchup_service.create_checklist(brief_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy catch-up brief.") from exc


@app.post(
    "/api/catch-up/{brief_id}/acknowledge",
    status_code=status.HTTP_204_NO_CONTENT,
)
def acknowledge_catchup(
    brief_id: str,
    user_id: str = Query(default="U01862"),
) -> Response:
    user = get_user(user_id)
    try:
        catchup_service.acknowledge(brief_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy catch-up brief.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/api/checklist/{item_id}", response_model=ChecklistItem)
def update_checklist_item(
    item_id: str,
    payload: ChecklistUpdate,
    user_id: str = Query(default="U01862"),
) -> ChecklistItem:
    user = get_user(user_id)
    try:
        return catchup_service.update_checklist(item_id, payload.completed, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy checklist item.") from exc


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
