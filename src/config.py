"""SavingsTracker — Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://savingstracker:changeme@localhost:5432/savingstracker"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 30

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Telegram (legacy global fallback; prefer per-household tokens) ──
    telegram_bot_token: str = ""
    # Comma-separated Telegram user IDs. Empty = any linked account.
    telegram_allowed_user_ids: str = ""
    # Comma-separated group/supergroup chat IDs. Empty = no group access.
    telegram_allowed_chat_ids: str = ""

    # ── Web auth (Google) ─────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    auth_secret_key: str = ""
    # Empty = any Google account may create a household. Non-empty = signup gate.
    # Household invites can still add emails that are not on this list.
    allowed_emails: str = ""
    public_base_url: str = ""
    cors_extra_origins: str = ""

    # ── LLM (OpenRouter) ──────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_model: str = "x-ai/grok-4.6"

    # ── Bank Connection (FinTS) ───────────────────────────
    fints_product_id: str = ""

    # ── Security ──────────────────────────────────────────
    encryption_key: str = ""

    # ── App Settings ──────────────────────────────────────
    log_level: str = "INFO"
    debug: bool = False

    @property
    def allowed_email_set(self) -> frozenset[str]:
        return frozenset(
            part.strip().lower()
            for part in self.allowed_emails.replace(";", ",").split(",")
            if part.strip()
        )

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            "http://localhost:5173",
            "http://localhost:4173",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:8000",
        ]
        if self.public_base_url:
            origins.append(self.public_base_url.rstrip("/"))
        for part in self.cors_extra_origins.replace(";", ",").split(","):
            origin = part.strip().rstrip("/")
            if origin:
                origins.append(origin)
        return list(dict.fromkeys(origins))

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg2").replace(
            "postgresql+psycopg2", "postgresql+psycopg2"
        )


settings = Settings()
