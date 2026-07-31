import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .engine import EngineRegistry, parse_sources
from .schemas import IndexRequest, IndexResponse, QueryRequest, QueryResponse


registry = EngineRegistry()
app = FastAPI(title="ZicZord RAG-Anything Service", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "engine": "HKUDS/RAG-Anything",
        "llm_model": registry.llm_model,
        "embedding_model": registry.embedding_model,
        "indexed_scopes": registry.indexed_scopes(),
    }


@app.post("/index", response_model=IndexResponse)
async def index_dataset(payload: IndexRequest) -> IndexResponse:
    try:
        result = await registry.index(payload.scope_key, Path(payload.processed_dir))
        return IndexResponse.model_validate(result)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest) -> QueryResponse:
    indexed = set(registry.indexed_scopes())
    allowed = [scope for scope in payload.scope_keys if scope in indexed]
    if not allowed:
        return QueryResponse(
            answer="Knowledge base chưa có dữ liệu cho các scope được cấp quyền.",
            sources=[],
            scopes_queried=[],
            provider="HKUDS/RAG-Anything",
            context_excerpt="",
        )
    results = await asyncio.gather(
        *(registry.query_scope(scope, payload.query, payload.mode) for scope in allowed),
        return_exceptions=True,
    )
    answers: list[str] = []
    contexts: list[str] = []
    scopes_queried: list[str] = []
    for scope, result in zip(allowed, results):
        if isinstance(result, Exception):
            continue
        answer, context = result
        answers.append(answer)
        contexts.append(context)
        scopes_queried.append(scope)
    combined_answer = "\n\n".join(answers) or "Không truy xuất được context phù hợp."
    combined_context = "\n\n".join(contexts)
    # Prefer sources the model actually cited. Context markers are only a fallback
    # for provider responses that omit markers despite receiving grounded chunks.
    sources = parse_sources(combined_answer)
    if not sources:
        sources = parse_sources(combined_context)
    sources = sources[:8]
    return QueryResponse(
        answer=combined_answer,
        sources=sources,
        scopes_queried=scopes_queried,
        provider="HKUDS/RAG-Anything@65b7ffd",
        context_excerpt=combined_context[:12000],
    )
