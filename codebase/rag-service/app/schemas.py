from typing import Literal

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    scope_key: str = Field(default="cohort:K4", pattern=r"^[a-z]+:[A-Za-z0-9_-]+$")
    processed_dir: str = "/data/processed"


class IndexResponse(BaseModel):
    scope_key: str
    indexed: bool
    document_id: str
    content_blocks: int
    source_counts: dict[str, int]
    vector_chunks: int


class QueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1200)
    scope_keys: list[str] = Field(min_length=1, max_length=8)
    mode: Literal["local", "global", "hybrid", "naive", "mix"] = "hybrid"


class SourceRef(BaseModel):
    source_id: str
    source_type: Literal["message", "episode", "painpoint"]
    channel_key: str
    label: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    scopes_queried: list[str]
    provider: str
    context_excerpt: str
