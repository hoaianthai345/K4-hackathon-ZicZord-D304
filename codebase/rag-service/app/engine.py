import asyncio
import hashlib
import json
import os
from pathlib import Path
import re

import httpx
import numpy as np
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from raganything import RAGAnything, RAGAnythingConfig

from .key_pool import OpenRouterKeyPool, RECOVERABLE_STATUS_CODES


SCOPE_RE = re.compile(r"^[a-z]+:[A-Za-z0-9_-]+$")
SOURCE_RE = re.compile(
    r"SOURCE_ID=(?P<id>[A-Za-z0-9_-]+)\|TYPE=(?P<type>message|episode|painpoint)"
    r"\|CHANNEL=(?P<channel>[A-Za-z0-9_-]+)"
)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def safe_scope(scope_key: str) -> str:
    if not SCOPE_RE.fullmatch(scope_key):
        raise ValueError("Scope key không hợp lệ.")
    return scope_key.casefold().replace(":", "-")


def source_marker(source_id: str, source_type: str, channel: str) -> str:
    return f"[SOURCE_ID={source_id}|TYPE={source_type}|CHANNEL={channel}]"


def build_blocks(processed_dir: Path) -> tuple[list[dict], dict[str, int]]:
    messages = read_jsonl(processed_dir / "messages_clean.jsonl")
    episodes = read_jsonl(processed_dir / "issue_episodes.jsonl")
    painpoints = read_jsonl(processed_dir / "painpoint_summary.jsonl")
    blocks: list[dict] = []
    max_messages = int(os.getenv("RAG_MAX_MESSAGES", "8"))
    max_episodes = int(os.getenv("RAG_MAX_EPISODES", "12"))
    max_painpoints = int(os.getenv("RAG_MAX_PAINPOINTS", "24"))
    painpoint_counts = {
        row["painpoint_cluster_id"]: row["episode_count"]
        for row in painpoints
    }

    selected_messages = sorted(
        (
            row
            for row in messages
            if not row["is_bot"]
            and not row["is_dot_noise"]
            and not row["is_greeting"]
            and (row["is_question"] or row["is_problem"] or row["has_attachment"])
        ),
        key=lambda row: (
            row["reaction_count"],
            row["has_attachment"],
            len(row["content_model"]),
        ),
        reverse=True,
    )[:max_messages]
    selected_episodes = sorted(
        (row for row in episodes if row["confidence"] >= 0.8),
        key=lambda row: (
            painpoint_counts.get(row.get("painpoint_cluster_id"), 0),
            row["reaction_count"],
            row["confidence"],
        ),
        reverse=True,
    )[:max_episodes]
    selected_painpoints = sorted(
        (row for row in painpoints if row["episode_count"] >= 2),
        key=lambda row: (row["episode_count"], row["unique_reporters"]),
        reverse=True,
    )[:max_painpoints]

    for row in selected_messages:
        text = (
            f"{source_marker(row['message_key'], 'message', row['channel_key'])}\n"
            f"Tin nhắn Discord lúc {row['created_at']}: {row['content_model']}\n"
            f"Reaction: {row['reaction_count']}; attachment: {row['has_attachment']}."
        )
        blocks.append({"type": "text", "text": text, "page_idx": len(blocks)})

    for row in selected_episodes:
        answer = row.get("answer_summary") or "Chưa có câu trả lời rõ ràng."
        text = (
            f"{source_marker(row['episode_id'], 'episode', row['channel_key'])}\n"
            f"Vấn đề: {row['canonical_problem']}\n"
            f"Khu vực: {row['product_area']}; thực thể: {', '.join(row['entities']) or 'không rõ'}.\n"
            f"Trạng thái: {row['resolution_status']}. Câu trả lời đã thấy: {answer}"
        )
        blocks.append({"type": "text", "text": text, "page_idx": len(blocks)})

    for row in selected_painpoints:
        examples = " | ".join(row["representative_examples"][:3])
        resolution = row.get("known_resolution") or "Chưa có cách xử lý đã xác nhận."
        text = (
            f"{source_marker(row['painpoint_cluster_id'], 'painpoint', 'qa')}\n"
            f"Pain point: {row['painpoint_title']}. Có {row['episode_count']} episode từ "
            f"{row['unique_reporters']} reporter; unresolved rate {row['unresolved_rate']:.1%}.\n"
            f"Ví dụ: {examples}\nCách xử lý đã biết: {resolution}"
        )
        blocks.append({"type": "text", "text": text, "page_idx": len(blocks)})

    return blocks, {
        "messages": len(selected_messages),
        "episodes": len(selected_episodes),
        "painpoints": len(selected_painpoints),
    }


class EngineRegistry:
    def __init__(self):
        self.storage_root = Path(os.getenv("RAG_STORAGE_ROOT", "/data/rag_storage"))
        self.base_url = os.getenv("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")
        openrouter_keys = {
            "phuc": os.getenv("OPENROUTER_API_KEY_PHUC", ""),
            "khang": os.getenv("OPENROUTER_API_KEY_KHANG", ""),
            "trinh": os.getenv("OPENROUTER_API_KEY_TRINH", ""),
            "default": os.getenv("OPENROUTER_API_KEY", ""),
        }
        rag_order = [
            name.strip().casefold()
            for name in os.getenv(
                "OPENROUTER_RAG_KEY_ORDER",
                "trinh,phuc,khang,default",
            ).split(",")
            if name.strip()
        ]
        self.openrouter_pool = OpenRouterKeyPool(
            openrouter_keys,
            {"rag": rag_order},
        )
        dedicated_llm_key = os.getenv("RAG_LLM_API_KEY", "")
        fallback_keys = self.openrouter_pool.candidates("rag")
        self.llm_api_key = (
            dedicated_llm_key
            or (fallback_keys[0].value if fallback_keys else "")
        )
        self.llm_base_url = (
            os.getenv("RAG_LLM_BASE_URL", "https://api.groq.com/openai/v1")
            if dedicated_llm_key
            else self.base_url
        )
        self.llm_model = (
            os.getenv("RAG_LLM_MODEL", "qwen/qwen3.6-27b")
            if dedicated_llm_key
            else os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free")
        )
        self.embedding_model = os.getenv(
            "RAG_EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b:free"
        )
        self.embedding_dimensions = int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "2048"))
        self.chunk_token_size = int(os.getenv("RAG_CHUNK_TOKEN_SIZE", "3000"))
        self._engines: dict[str, RAGAnything] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _embedding_func(self, texts: list[str]) -> np.ndarray:
        payload = {
            "model": self.embedding_model,
            "input": texts,
            "dimensions": self.embedding_dimensions,
            "encoding_format": "float",
        }
        failures: list[str] = []
        for slot in self.openrouter_pool.candidates("rag"):
            headers = {
                "Authorization": f"Bearer {slot.value}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-OpenRouter-Title": "Kute RAG-Anything",
            }
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    response = await client.post(
                        f"{self.base_url.rstrip('/')}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    body = response.json()
                rows = sorted(body["data"], key=lambda item: item.get("index", 0))
                self.openrouter_pool.mark_success(slot.name)
                return np.asarray(
                    [row["embedding"] for row in rows],
                    dtype=np.float32,
                )
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code not in RECOVERABLE_STATUS_CODES:
                    raise
                retry_after = exc.response.headers.get("Retry-After")
                try:
                    retry_seconds = float(retry_after) if retry_after else None
                except ValueError:
                    retry_seconds = None
                self.openrouter_pool.mark_failure(
                    slot.name,
                    status_code,
                    retry_seconds,
                )
                failures.append(f"{slot.name}:{status_code}")
            except httpx.RequestError:
                self.openrouter_pool.mark_failure(slot.name, None)
                failures.append(f"{slot.name}:network")
        raise RuntimeError(
            "Không có OpenRouter key khả dụng cho embedding."
            + (f" ({', '.join(failures)})" if failures else "")
        )

    async def _llm_func(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history_messages: list | None = None,
        **kwargs,
    ) -> str:
        if self.llm_base_url.startswith("https://api.groq.com"):
            # Qwen 3.6 enables reasoning by default on Groq. For this retrieval
            # workload, reasoning consumed nearly the whole completion budget and
            # truncated the grounded answer. Groq supports "none" for this model.
            kwargs["reasoning_effort"] = "none"
            # Groq Qwen supports JSON mode but not OpenAI's json_schema payload.
            # LightRAG's prompt still requests parseable JSON for keyword extraction.
            kwargs.pop("response_format", None)
            kwargs.pop("keyword_extraction", None)
            kwargs.pop("reasoning_format", None)
            kwargs.pop("include_reasoning", None)
        return await openai_complete_if_cache(
            self.llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            **kwargs,
        )

    async def get(self, scope_key: str) -> RAGAnything:
        slug = safe_scope(scope_key)
        if slug in self._engines:
            return self._engines[slug]
        lock = self._locks.setdefault(slug, asyncio.Lock())
        async with lock:
            if slug in self._engines:
                return self._engines[slug]
            working_dir = self.storage_root / slug
            config = RAGAnythingConfig(
                working_dir=str(working_dir),
                enable_image_processing=False,
                enable_table_processing=False,
                enable_equation_processing=False,
                display_content_stats=False,
            )
            embeddings = EmbeddingFunc(
                embedding_dim=self.embedding_dimensions,
                max_token_size=32768,
                func=self._embedding_func,
            )
            engine = RAGAnything(
                config=config,
                llm_model_func=self._llm_func,
                embedding_func=embeddings,
                lightrag_kwargs={
                    "llm_model_name": self.llm_model,
                    "embedding_batch_num": 16,
                    "embedding_func_max_async": 2,
                    "llm_model_max_async": 2,
                    "enable_llm_cache": True,
                    "chunk_token_size": self.chunk_token_size,
                    "chunk_overlap_token_size": 200,
                    "entity_extract_max_gleaning": 0,
                },
            )
            # Discord data is already parsed; direct content insertion does not need MinerU.
            engine._parser_installation_checked = True
            initialized = await engine._ensure_lightrag_initialized()
            if not initialized.get("success"):
                raise RuntimeError(initialized.get("error", "RAG-Anything init failed"))
            self._engines[slug] = engine
            return engine

    async def index(self, scope_key: str, processed_dir: Path) -> dict:
        engine = await self.get(scope_key)
        blocks, source_counts = build_blocks(processed_dir)
        digest = hashlib.sha256(
            "\n".join(block["text"] for block in blocks).encode("utf-8")
        ).hexdigest()[:16]
        manifest_path = Path(engine.working_dir) / "kute-index-manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                manifest.get("digest") == digest
                and int(manifest.get("vector_chunks", 0)) > 0
            ):
                return {**manifest, "indexed": False}
        document_id = f"discord-{safe_scope(scope_key)}-{digest}"
        await engine.insert_content_list(
            content_list=blocks,
            file_path=f"discord-{safe_scope(scope_key)}.jsonl",
            doc_id=document_id,
            display_stats=False,
        )
        vector_path = Path(engine.working_dir) / "vdb_chunks.json"
        try:
            vector_data = json.loads(vector_path.read_text(encoding="utf-8"))
            vector_count = len(vector_data.get("data", []))
        except (OSError, AttributeError, json.JSONDecodeError):
            vector_count = 0
        if vector_count == 0:
            raise RuntimeError(
                "LightRAG không tạo vector chunks; index bị từ chối thay vì ghi manifest giả."
            )
        manifest = {
            "scope_key": scope_key,
            "indexed": True,
            "document_id": document_id,
            "content_blocks": len(blocks),
            "source_counts": source_counts,
            "vector_chunks": vector_count,
            "digest": digest,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    async def query_scope(self, scope_key: str, query: str, mode: str) -> tuple[str, str]:
        engine = await self.get(scope_key)
        query_options = {
            "vlm_enhanced": False,
            "top_k": 5,
            "chunk_top_k": 1,
            "max_entity_tokens": 200,
            "max_relation_tokens": 200,
            "max_total_tokens": 4500,
            "enable_rerank": False,
        }
        context = await engine.aquery(
            query,
            mode=mode,
            only_need_context=True,
            **query_options,
        )
        answer_query = (
            f"{query}\n\n"
            "Yêu cầu bắt buộc: trả lời tiếng Việt trong tối đa 3 bullet, chỉ dùng dữ liệu "
            "truy xuất, không suy đoán. Nếu dữ liệu chưa có cách xử lý được xác nhận thì "
            "nói rõ điều đó. Giữ nguyên marker "
            "[SOURCE_ID=...|TYPE=...|CHANNEL=...] ở cuối từng ý có nguồn."
        )
        answer = await engine.aquery(
            answer_query,
            mode=mode,
            **query_options,
        )
        if answer is None or str(answer).strip() in {"", "None"}:
            raise RuntimeError("LightRAG không sinh được câu trả lời từ context.")
        clean_answer = re.sub(
            r"<think>.*?</think>",
            "",
            str(answer),
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        clean_answer = re.sub(
            r'(\|CHANNEL=[A-Za-z0-9_-]+)["\'”’]+\]',
            r"\1]",
            clean_answer,
        )
        clean_answer = re.split(
            r"\n#{1,6}\s+References\b",
            clean_answer,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].rstrip()
        return clean_answer, str(context)

    def indexed_scopes(self) -> list[str]:
        if not self.storage_root.exists():
            return []
        values = []
        for manifest_path in self.storage_root.glob("*/kute-index-manifest.json"):
            try:
                values.append(json.loads(manifest_path.read_text())["scope_key"])
            except (OSError, KeyError, json.JSONDecodeError):
                continue
        return sorted(set(values))


def parse_sources(value: str) -> list[dict]:
    seen: set[str] = set()
    sources: list[dict] = []
    for match in SOURCE_RE.finditer(value):
        source_id = match.group("id")
        if source_id in seen:
            continue
        seen.add(source_id)
        source_type = match.group("type")
        channel = match.group("channel")
        sources.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "channel_key": channel,
                "label": f"{source_type}:{source_id}",
            }
        )
    return sources
