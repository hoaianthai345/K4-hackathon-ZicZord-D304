from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Kute Discord Catch-up Copilot API"
    app_version: str = "0.4.0"
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    memory_provider: str = os.getenv("MEMORY_PROVIDER", "local").lower()
    hindsight_base_url: str = os.getenv("HINDSIGHT_BASE_URL", "http://hindsight:8888")
    hindsight_api_key: str | None = os.getenv("HINDSIGHT_API_KEY") or None
    apify_api_base_url: str = os.getenv("APIFY_API_BASE_URL", "https://api.apify.com/v2")
    apify_token: str | None = os.getenv("APIFY_TOKEN") or None
    apify_dataset_id: str | None = os.getenv("APIFY_DATASET_ID") or None
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY") or None
    openrouter_api_base_url: str = os.getenv(
        "OPENROUTER_API_BASE_URL",
        "https://openrouter.ai/api/v1",
    )
    openrouter_model: str = os.getenv(
        "OPENROUTER_MODEL",
        "google/gemma-4-26b-a4b-it:free",
    )
    openrouter_site_url: str = os.getenv(
        "OPENROUTER_SITE_URL",
        "http://localhost:3000",
    )
    groq_api_key: str | None = os.getenv("GROQ_API_KEY") or None
    groq_api_base_url: str = os.getenv(
        "GROQ_API_BASE_URL",
        "https://api.groq.com/openai/v1",
    )
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
    database_url: str | None = os.getenv("DATABASE_URL") or None
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    rag_anything_url: str | None = os.getenv("RAG_ANYTHING_URL") or None
    api_public_url: str = os.getenv("API_PUBLIC_URL", "http://localhost:8000")
    admin_api_key: str | None = os.getenv("ADMIN_API_KEY") or None
    state_path: Path = Path(
        os.getenv(
            "STATE_PATH",
            str(Path(__file__).resolve().parents[1] / "state" / "demo_state.json"),
        )
    )

    @property
    def frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        ]


settings = Settings()
