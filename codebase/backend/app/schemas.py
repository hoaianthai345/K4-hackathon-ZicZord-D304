from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ScopeType = Literal["user", "team", "group", "room", "cohort"]
MemoryKind = Literal["decision", "task", "blocker", "preference", "learning_note"]


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


class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1, max_length=1200)
    channel_id: str = "bot-commands"


class ChatResponse(BaseModel):
    message: AssistantMessage
    candidate: MemoryCandidate | None = None
    provider: str


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
