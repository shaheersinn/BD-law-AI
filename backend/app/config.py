"""
app/config.py — ORACLE application configuration.

All settings are read from environment variables (or .env file in development).
Uses pydantic-settings v2 for type-safe configuration with validation.
Never hard-code secrets. Never commit .env to git.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    ORACLE application settings.

    All values are read from environment variables.
    Secrets must NEVER have default values in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = Field(default="ORACLE — BD for Law", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # ── Security ───────────────────────────────────────────────────────────────
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="JWT signing secret key — MUST be changed in production",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiry in minutes"
    )
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry in days")
    max_login_attempts: int = Field(
        default=5, description="Max failed login attempts before lockout"
    )
    lockout_duration_minutes: int = Field(
        default=15, description="Account lockout duration in minutes"
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_db",
        description="Async PostgreSQL connection URL (asyncpg driver required)",
    )
    db_pool_size: int = Field(default=20, description="DB connection pool size")
    db_max_overflow: int = Field(default=10, description="DB pool max overflow")
    db_pool_timeout: int = Field(default=30, description="DB pool timeout in seconds")
    db_pool_recycle: int = Field(default=3600, description="DB connection recycle time in seconds")
    db_echo: bool = Field(default=False, description="Echo SQL queries (debug only)")

    # ── MongoDB Atlas ──────────────────────────────────────────────────────────
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL (Atlas or local)",
    )
    mongodb_db_name: str = Field(
        default="oracle_signals",
        description="MongoDB database name for social signals and corporate graph",
    )
    mongodb_max_pool_size: int = Field(default=50, description="MongoDB connection pool size")

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (broker and cache)",
    )
    redis_result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Redis URL for Celery result backend",
    )
    redis_cache_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
    redis_rate_limit_ttl: int = Field(default=3600, description="Rate limit window in seconds")

    # ── Celery ─────────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL",
    )
    celery_task_time_limit: int = Field(default=3600, description="Hard task time limit in seconds")
    celery_task_soft_time_limit: int = Field(
        default=3300, description="Soft task time limit in seconds"
    )
    celery_worker_concurrency: int = Field(default=4, description="Celery worker concurrency")

    # ── DigitalOcean Spaces (model artifact storage) ───────────────────────────
    spaces_key: str = Field(default="", description="DigitalOcean Spaces access key")
    spaces_secret: str = Field(default="", description="DigitalOcean Spaces secret key")
    spaces_bucket: str = Field(default="oracle-models", description="Spaces bucket name")
    spaces_region: str = Field(default="tor1", description="Spaces region")
    spaces_endpoint: str = Field(
        default="https://tor1.digitaloceanspaces.com",
        description="Spaces endpoint URL",
    )

    # ── Model Storage (local) ──────────────────────────────────────────────────
    models_dir: str = Field(
        default="data/models", description="Local directory for ML model artifacts"
    )
    data_dir: str = Field(default="data", description="Root data directory")

    # ── External APIs — Scrapers ───────────────────────────────────────────────
    canlii_api_key: str = Field(default="", description="CanLII API key (free)")
    opensky_username: str = Field(default="", description="OpenSky Network username")
    opensky_password: str = Field(default="", description="OpenSky Network password")
    proxycurl_api_key: str = Field(default="", description="Proxycurl API key (LinkedIn)")
    alpha_vantage_api_key: str = Field(
        default="", description="Alpha Vantage API key (market data)"
    )
    twitter_bearer_token: str = Field(default="", description="Twitter/X API bearer token")
    hibp_api_key: str = Field(
        default="", description="HaveIBeenPwned API key (dark web monitoring)"
    )
    reddit_client_id: str = Field(default="", description="Reddit OAuth2 client ID")
    reddit_client_secret: str = Field(default="", description="Reddit OAuth2 client secret")

    # ── LLM — Training Phase Only (never production) ──────────────────────────
    groq_api_key: str = Field(
        default="",
        description="Groq API key — Phase 4 training ONLY, never production scoring",
    )

    # ── Monitoring ─────────────────────────────────────────────────────────────
    sentry_dsn: str = Field(default="", description="Sentry DSN for error monitoring")
    slack_webhook_url: str = Field(default="", description="Slack webhook for critical alerts")

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    rate_limit_requests: int = Field(default=100, description="Max requests per window per user")
    rate_limit_window_seconds: int = Field(default=3600, description="Rate limit window in seconds")

    # ── Multi-tenancy (future) ─────────────────────────────────────────────────
    # Currently single-tenant. Multi-tenant architecture designed but not activated.
    # When multi-tenancy is enabled, each firm gets isolated DB schema.
    multi_tenant_enabled: bool = Field(
        default=False,
        description="Enable multi-tenant mode (future — single tenant first)",
    )

    # ── Feature Flags ─────────────────────────────────────────────────────────
    bayesian_engine_enabled: bool = Field(
        default=True, description="Enable Bayesian convergence engines"
    )
    transformer_engine_enabled: bool = Field(
        default=True,
        description="Enable Transformer scorer (uses Bayesian until it earns the right)",
    )
    live_feeds_enabled: bool = Field(
        default=False,
        description="Enable live Redis Streams pipeline (Phase 5 — disabled in Phase 0)",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure environment is a known value."""
        valid = {"development", "staging", "production"}
        if v not in valid:
            raise ValueError(f"environment must be one of {valid}")
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        """In production, enforce that critical secrets are not defaults."""
        if self.environment == "production":
            # In production, secret_key should not be auto-generated
            # (auto-generated keys change on restart, invalidating all tokens)
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if self.database_url.startswith("postgresql+asyncpg://oracle:oracle@localhost"):
                raise ValueError("DATABASE_URL must be set to a real database URL in production")
        return self

    @property
    def is_production(self) -> bool:
        """Convenience property for production environment check."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Convenience property for development environment check."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    Using lru_cache ensures Settings is loaded once per process.
    This is the recommended pattern for FastAPI dependency injection.

    Usage:
        from app.config import get_settings
        settings = get_settings()
        # or as FastAPI dependency:
        # settings: Settings = Depends(get_settings)
    """
    return Settings()
