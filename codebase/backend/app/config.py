from dataclasses import dataclass
import os
from pathlib import Path


def default_eval_dir() -> Path:
    parents = Path(__file__).resolve().parents
    return parents[3] / "eval" if len(parents) > 3 else Path("/app/eval")


def split_order(value: str) -> list[str]:
    return [item.strip().casefold() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "ZicZord Discord Catch-up Copilot API"
    app_version: str = "0.5.0"
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
        "qwen/qwen3.6-27b",
    )
    openrouter_api_key_phuc: str | None = (
        os.getenv("OPENROUTER_API_KEY_PHUC") or None
    )
    openrouter_api_key_khang: str | None = (
        os.getenv("OPENROUTER_API_KEY_KHANG") or None
    )
    openrouter_api_key_trinh: str | None = (
        os.getenv("OPENROUTER_API_KEY_TRINH") or None
    )
    openrouter_chat_key_order: str = os.getenv(
        "OPENROUTER_CHAT_KEY_ORDER",
        "khang,trinh,phuc,default",
    )
    openrouter_brief_key_order: str = os.getenv(
        "OPENROUTER_BRIEF_KEY_ORDER",
        "phuc,khang,trinh,default",
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
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN") or None
    telegram_webhook_secret: str | None = (
        os.getenv("TELEGRAM_WEBHOOK_SECRET") or None
    )
    telegram_api_base_url: str = os.getenv(
        "TELEGRAM_API_BASE_URL",
        "https://api.telegram.org",
    )
    telegram_user_map_path: Path = Path(
        os.getenv(
            "TELEGRAM_USER_MAP_PATH",
            str(
                Path(__file__).resolve().parents[2]
                / "config"
                / "telegram-users.json"
            ),
        )
    )
    telegram_public_user_id: str | None = (
        os.getenv("TELEGRAM_PUBLIC_USER_ID") or None
    )
    database_url: str | None = os.getenv("DATABASE_URL") or None
    rag_enabled: bool = os.getenv("RAG_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    rag_anything_url: str | None = os.getenv("RAG_ANYTHING_URL") or None
    api_public_url: str = os.getenv("API_PUBLIC_URL", "http://localhost:8000")
    admin_api_key: str | None = os.getenv("ADMIN_API_KEY") or None
    eval_dir: Path = Path(
        os.getenv(
            "EVAL_DIR",
            str(default_eval_dir()),
        )
    )
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

    @property
    def openrouter_keys(self) -> dict[str, str]:
        values = {
            "phuc": self.openrouter_api_key_phuc,
            "khang": self.openrouter_api_key_khang,
            "trinh": self.openrouter_api_key_trinh,
            "default": self.openrouter_api_key,
        }
        return {name: value for name, value in values.items() if value}

    @property
    def openrouter_flow_orders(self) -> dict[str, list[str]]:
        return {
            "chat": split_order(self.openrouter_chat_key_order),
            "brief": split_order(self.openrouter_brief_key_order),
        }


settings = Settings()
