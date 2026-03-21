"""
app/config.py — centralised configuration via pydantic-settings.
All values read from environment variables (or .env file).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "BD for Law"
    app_version: str = "3.0.0"
    environment: str = Field("development", pattern="^(development|staging|production)$")
    debug: bool = False
    secret_key: str = Field("dev-secret-key-change-this-in-production-32chars", min_length=32)
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: PostgresDsn = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/bdforlaw"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: RedisDsn = Field("redis://localhost:6379/0")
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field("", description="Get from console.anthropic.com. Groq used as fallback if empty.")
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 1000

    # ── External APIs ─────────────────────────────────────────────────────────
    canlii_api_key: str = ""
    opensky_username: str = ""
    opensky_password: str = ""
    proxycurl_api_key: str = ""
    foursquare_api_key: str = ""
    groq_api_key: str = ""         # free LLM fallback

    # ── Notifications ─────────────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "bd-signals@halcyon.legal"
    slack_webhook_url: str = ""
    slack_bot_token: str = ""

    # ── ML ────────────────────────────────────────────────────────────────────
    models_dir: str = "models"          # where .pkl files live
    min_training_rows: int = 50         # minimum labelled alerts before retraining
    churn_risk_threshold: int = 60      # score above which alerts fire

    # ── Monitoring ────────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"

    # ── Scrapers ──────────────────────────────────────────────────────────────
    scraper_timeout_seconds: int = 30
    scraper_user_agent: str = (
        "Mozilla/5.0 (compatible; BDforLaw/3.0; +https://halcyon.legal/bot)"
    )
    jet_bay_street_airports: list[str] = [
        "CYTZ",  # Toronto Billy Bishop
        "CYYZ",  # Toronto Pearson
        "KJFK",  # New York JFK
        "KEWR",  # New York Newark
        "KLGA",  # New York LaGuardia
        "EGLL",  # London Heathrow
        "EGLC",  # London City
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
