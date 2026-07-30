import asyncio
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .schemas import Memory


@dataclass
class ProviderStatus:
    name: str
    reachable: bool | None


class HindsightGateway:
    """Optional Hindsight mirror with one bank per authorization scope."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.memory_provider == "hindsight"
        self.client: Any | None = None
        self.last_error: str | None = None

        if self.enabled:
            try:
                from hindsight_client import Hindsight

                arguments: dict[str, Any] = {
                    "base_url": settings.hindsight_base_url,
                    "timeout": 20.0,
                }
                if settings.hindsight_api_key:
                    arguments["api_key"] = settings.hindsight_api_key
                self.client = Hindsight(**arguments)
            except Exception as exc:
                self.last_error = str(exc)

    @staticmethod
    def _bank_id(scope_type: str, scope_id: str) -> str:
        safe_scope = scope_id.lower().replace("_", "-")
        return f"kute-{scope_type}-{safe_scope}"

    async def retain_evidence(
        self,
        turn_id: str,
        content: str,
        scope_type: str,
        scope_id: str,
    ) -> None:
        if not self.client:
            return
        try:
            await asyncio.to_thread(
                self.client.retain,
                bank_id=self._bank_id(scope_type, scope_id),
                content=content,
                context="Discord Copilot chat evidence",
                document_id=f"evidence-{turn_id}",
                tags=[
                    f"scope_type:{scope_type}",
                    f"scope_id:{scope_id}",
                    "layer:evidence",
                ],
                metadata={"source": "kute-chat", "turn_id": turn_id},
            )
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)

    async def retain_confirmed(self, memory: Memory) -> None:
        if not self.client:
            return
        try:
            await asyncio.to_thread(
                self.client.retain,
                bank_id=self._bank_id(memory.scope_type, memory.scope_id),
                content=memory.content,
                context=f"Confirmed Discord {memory.kind}",
                document_id=memory.id,
                update_mode="replace",
                tags=[
                    f"scope_type:{memory.scope_type}",
                    f"scope_id:{memory.scope_id}",
                    "layer:canonical",
                    "status:confirmed",
                    f"kind:{memory.kind}",
                ],
                metadata={
                    "source": "kute-memory-confirmation",
                    "memory_id": memory.id,
                },
            )
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)

    async def _recall_bank(
        self,
        scope_type: str,
        scope_id: str,
        query: str,
    ) -> list[str]:
        if not self.client:
            return []
        response = await asyncio.to_thread(
            self.client.recall,
            bank_id=self._bank_id(scope_type, scope_id),
            query=query,
            tags=[
                f"scope_type:{scope_type}",
                f"scope_id:{scope_id}",
                "layer:canonical",
                "status:confirmed",
            ],
            tags_match="all_strict",
            budget="low",
        )
        values: list[str] = []
        for result in getattr(response, "results", []):
            text = getattr(result, "text", None) or getattr(result, "content", None)
            if text:
                values.append(str(text))
        return values[:2]

    async def recall_confirmed(
        self,
        scopes: list[tuple[str, str]],
        query: str,
    ) -> list[str]:
        if not self.client:
            return []
        try:
            responses = await asyncio.gather(
                *(self._recall_bank(scope_type, scope_id, query) for scope_type, scope_id in scopes)
            )
            self.last_error = None
            merged: list[str] = []
            for values in responses:
                for value in values:
                    if value not in merged:
                        merged.append(value)
            return merged[:4]
        except Exception as exc:
            self.last_error = str(exc)
            return []

    async def delete_confirmed(self, memory: Memory) -> None:
        if not self.client:
            return
        try:
            await asyncio.to_thread(
                self.client.documents.delete_document,
                bank_id=self._bank_id(memory.scope_type, memory.scope_id),
                document_id=memory.id,
            )
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)

    def status(self) -> ProviderStatus:
        if not self.enabled:
            return ProviderStatus(name="local-demo", reachable=None)
        return ProviderStatus(
            name="hindsight" if self.client and not self.last_error else "hindsight-fallback",
            reachable=bool(self.client and not self.last_error),
        )
