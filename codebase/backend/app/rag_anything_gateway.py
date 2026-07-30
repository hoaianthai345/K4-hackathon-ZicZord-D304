from dataclasses import dataclass, field
import re

import httpx

from .config import Settings
from .schemas import CommunityUser
from .scopes import allowed_scope_keys


@dataclass
class RAGAnythingSource:
    source_id: str
    source_type: str
    channel_key: str
    label: str


@dataclass
class RAGAnythingResult:
    answer: str
    sources: list[RAGAnythingSource] = field(default_factory=list)
    scopes_queried: list[str] = field(default_factory=list)
    provider: str = "rag-anything"


class RAGAnythingGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.last_error: str | None = None
        self.last_success = False

    @property
    def configured(self) -> bool:
        return bool(self.settings.rag_enabled and self.settings.rag_anything_url)

    @staticmethod
    def scope_keys(user: CommunityUser) -> list[str]:
        return sorted(f"{scope_type}:{scope_id}" for scope_type, scope_id in allowed_scope_keys(user))

    async def query(self, user: CommunityUser, query: str) -> RAGAnythingResult | None:
        if not self.configured:
            return None
        payload = {
            "query": query,
            "scope_keys": self.scope_keys(user),
            "mode": "hybrid",
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{self.settings.rag_anything_url.rstrip('/')}/query",
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            sources = [RAGAnythingSource(**item) for item in body.get("sources", [])]
            answer = str(body.get("answer", "")).strip()
            scopes_queried = body.get("scopes_queried", [])
            if not answer or not sources or not scopes_queried:
                return None
            self.last_error = None
            self.last_success = True
            return RAGAnythingResult(
                answer=answer,
                sources=sources,
                scopes_queried=scopes_queried,
                provider=body.get("provider", "rag-anything"),
            )
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            self.last_error = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", str(exc))
            self.last_success = False
            return None

    async def status(self) -> dict:
        if not self.configured:
            return {"configured": False, "reachable": None, "indexed_scopes": []}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.settings.rag_anything_url.rstrip('/')}/health"
                )
                response.raise_for_status()
            body = response.json()
            return {
                "configured": True,
                "reachable": True,
                "indexed_scopes": body.get("indexed_scopes", []),
            }
        except httpx.HTTPError:
            return {"configured": True, "reachable": False, "indexed_scopes": []}

    async def index(
        self,
        scope_key: str = "cohort:K4",
        processed_dir: str = "/data/processed",
    ) -> dict:
        if not self.configured:
            raise RuntimeError("RAG-Anything chưa được cấu hình.")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.settings.rag_anything_url.rstrip('/')}/index",
                json={
                    "scope_key": scope_key,
                    "processed_dir": processed_dir,
                },
            )
            response.raise_for_status()
            return response.json()
