from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ScopeType = Literal["user", "team", "group", "room", "cohort"]
MemoryKind = Literal["decision", "task", "blocker", "preference", "learning_note"]
CatchupKind = Literal["decision", "task", "blocker", "announcement"]


class CommunityUser(BaseModel):
    id: str
    discord_user_id: str
    name: str
    member_label: str
    role: Literal["student", "mentor"]
    cohort_id: str
    team_id: str | None = None
    group_id: str
    lecture_room_id: str | None = None
    lab_room_id: str | None = None


class ScopeDescriptor(BaseModel):
    type: ScopeType
    id: str
    label: str
    relation: str


class DiscordChannel(BaseModel):
    id: str
    discord_channel_id: str
    name: str
    category: str
    kind: Literal["common", "qa", "share", "announcement", "team", "group", "lecture", "lab"]
    scope_type: ScopeType
    scope_id: str
    unread_count: int = 0


class DiscordMessage(BaseModel):
    id: str
    source_message_id: str
    channel_id: str
    author_id: str
    author_name: str
    content: str
    created_at: datetime
    permalink: str
    source: Literal["demo", "apify"] = "demo"


class Citation(BaseModel):
    message_id: str
    channel_id: str
    channel_name: str
    label: str
    permalink: str


class Memory(BaseModel):
    id: str
    scope_type: ScopeType
    scope_id: str
    kind: MemoryKind
    content: str
    evidence: list[str] = Field(default_factory=list)
    created_by: str
    status: Literal["confirmed"] = "confirmed"
    created_at: datetime
    updated_at: datetime


class MemoryCandidate(BaseModel):
    id: str
    scope_type: ScopeType
    scope_id: str
    kind: MemoryKind
    content: str
    evidence: list[str]
    created_by: str
    status: Literal["proposed"] = "proposed"
    created_at: datetime


class AssistantMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    author_name: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    memory_used: list[str] = Field(default_factory=list)
    created_at: datetime


class IngestionStatus(BaseModel):
    mode: Literal["demo-snapshot", "apify"]
    dataset_id: str | None = None
    last_synced_at: datetime | None = None
    imported_count: int = 0
    skipped_count: int = 0


class DiscordState(BaseModel):
    user: CommunityUser
    users: list[CommunityUser]
    scopes: list[ScopeDescriptor]
    channels: list[DiscordChannel]
    discord_messages: list[DiscordMessage]
    memories: list[Memory]
    candidates: list[MemoryCandidate]
    assistant_messages: list[AssistantMessage]
    suggested_prompts: list[str]
    provider: str
    ingestion: IngestionStatus
    checklist: list["ChecklistItem"] = Field(default_factory=list)


class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1, max_length=1200)
    channel_id: str = "bot-commands"


class ContextToolCall(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    reason: str
    result_count: int = 0


class ChatResponse(BaseModel):
    message: AssistantMessage
    candidate: MemoryCandidate | None = None
    provider: str
    tool_calls: list[ContextToolCall] = Field(default_factory=list)


class CatchupItem(BaseModel):
    id: str
    kind: CatchupKind
    title: str
    detail: str
    owner: str | None = None
    deadline: str | None = None
    status: Literal["open", "resolved", "unknown"] = "open"
    citations: list[Citation] = Field(default_factory=list)


class CatchupBrief(BaseModel):
    id: str
    user_id: str
    window_hours: int
    generated_at: datetime
    source_message_count: int
    channel_count: int
    summary: str
    items: list[CatchupItem]
    acknowledged: bool = False


class CatchupRequest(BaseModel):
    user_id: str
    window_hours: int = Field(default=24, ge=1, le=168)


class ChecklistItem(BaseModel):
    id: str
    user_id: str
    source_brief_id: str
    source_item_id: str
    text: str
    completed: bool = False
    owner: str | None = None
    deadline: str | None = None
    created_at: datetime


class ChecklistUpdate(BaseModel):
    completed: bool


class MemoryUpdate(BaseModel):
    content: str = Field(min_length=3, max_length=500)


class ApifyIngestRequest(BaseModel):
    dataset_id: str | None = Field(default=None, max_length=180)
    max_items: int = Field(default=250, ge=1, le=1000)


class ApifyIngestResponse(BaseModel):
    imported_count: int
    skipped_count: int
    duplicate_count: int
    dataset_id: str
    last_synced_at: datetime


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    memory_provider: str
    hindsight_reachable: bool | None
    ai_provider: str
    ai_reachable: bool | None
    ingestion_mode: Literal["demo-snapshot", "apify"]
    database_reachable: bool | None = None
    database_messages: int = 0
    database_episodes: int = 0
    database_painpoints: int = 0
    database_learning_contexts: int = 0
    rag_reachable: bool | None = None
    rag_indexed_scopes: list[str] = Field(default_factory=list)


class RAGQueryRequest(BaseModel):
    user_id: str
    query: str = Field(min_length=2, max_length=1200)


class RAGSource(BaseModel):
    source_id: str
    source_type: Literal["message", "episode", "painpoint", "lesson"]
    channel_key: str
    citation_url: str
    label: str


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    provider: str
    scopes_queried: list[str]
    sources: list[RAGSource]


class RAGSourceRecord(BaseModel):
    source_id: str
    source_type: Literal["message", "episode", "painpoint", "lesson"]
    channel_key: str
    scope_key: str
    content: str
    created_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class ContextPlanRequest(BaseModel):
    user_id: str
    query: str = Field(min_length=2, max_length=1200)
    channel_id: str = "bot-commands"


class ContextPlanResponse(BaseModel):
    query: str
    filters: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    tool_calls: list[ContextToolCall]
    sources: list[RAGSourceRecord] = Field(default_factory=list)


class AdminContextItem(BaseModel):
    source_id: str
    source_type: Literal["message", "episode", "painpoint", "lesson"]
    source_kind: str
    title: str
    channel_key: str
    scope_key: str
    day_code: str | None = None
    page_number: int | None = None
    created_at: datetime | None = None
    content: str
    is_enabled: bool


class AdminContextList(BaseModel):
    items: list[AdminContextItem]
    total: int
    limit: int
    offset: int


class AdminContextUpdate(BaseModel):
    is_enabled: bool


class AdminMemoryCreate(BaseModel):
    scope_type: ScopeType
    scope_id: str = Field(min_length=1, max_length=80)
    kind: MemoryKind
    content: str = Field(min_length=3, max_length=500)
    evidence: list[str] = Field(default_factory=list, max_length=20)
    created_by: str = Field(default="admin", max_length=80)


class AdminMemoryUpdate(BaseModel):
    scope_type: ScopeType | None = None
    scope_id: str | None = Field(default=None, min_length=1, max_length=80)
    kind: MemoryKind | None = None
    content: str | None = Field(default=None, min_length=3, max_length=500)
    evidence: list[str] | None = Field(default=None, max_length=20)


class AdminOverview(BaseModel):
    context_total: int
    context_enabled: int
    context_by_type: dict[str, int] = Field(default_factory=dict)
    context_by_scope: dict[str, int] = Field(default_factory=dict)
    memory_total: int
    memory_by_scope: dict[str, int] = Field(default_factory=dict)
    rag_reachable: bool | None = None
    rag_indexed_scopes: list[str] = Field(default_factory=list)
    admin_auth_required: bool = False
