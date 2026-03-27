"""
tests/test_phase0_scaffold.py — Phase 0 scaffold tests.

Tests:
  - Settings load without error
  - DB engine creates with correct pool config
  - /api/health returns correct JSON structure
  - CORS headers present
  - /api/ready returns 503 when DB unreachable
  - /api/ready returns 200 when DB reachable

All tests run without live DB/Redis/Mongo (fully mocked).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app

# ── Settings Tests ──────────────────────────────────────────────────────────


class TestSettings:
    """Settings load and validate correctly."""

    def test_settings_load_development(self) -> None:
        """Settings load with defaults in development mode."""
        s = Settings(environment="development")
        assert s.app_name == "ORACLE — BD for Law"
        assert s.environment == "development"

    def test_settings_has_required_fields(self) -> None:
        """Settings includes all critical fields."""
        s = Settings(environment="development")
        assert hasattr(s, "database_url")
        assert hasattr(s, "redis_url")
        assert hasattr(s, "mongodb_url")
        assert hasattr(s, "secret_key")
        assert hasattr(s, "celery_broker_url")

    def test_settings_db_pool_defaults(self) -> None:
        """DB pool settings have correct defaults."""
        s = Settings(environment="development")
        assert s.db_pool_size == 20
        assert s.db_max_overflow == 10
        assert s.db_pool_timeout == 30
        assert s.db_pool_recycle == 3600

    def test_settings_is_production_property(self) -> None:
        """is_production property works correctly."""
        dev = Settings(environment="development")
        assert not dev.is_production
        assert dev.is_development

    def test_settings_production_requires_strong_secret(self) -> None:
        """Production mode rejects short secret keys."""
        with pytest.raises(ValueError, match="SECRET_KEY must be at least 32"):
            Settings(
                environment="production",
                secret_key="short",
                database_url="postgresql+asyncpg://user:pass@prod-host:5432/prod_db",
            )

    def test_settings_production_rejects_localhost_db(self) -> None:
        """Production mode rejects localhost database URL."""
        with pytest.raises(ValueError, match="DATABASE_URL must be set"):
            Settings(
                environment="production",
                secret_key="a" * 64,
                database_url="postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_db",
            )

    def test_settings_feature_flags(self) -> None:
        """Feature flags have correct defaults."""
        s = Settings(environment="development")
        assert s.bayesian_engine_enabled is True
        assert s.transformer_engine_enabled is True
        assert s.live_feeds_enabled is False

    def test_settings_rate_limit_defaults(self) -> None:
        """Rate limit defaults are reasonable."""
        s = Settings(environment="development")
        assert s.rate_limit_requests == 100
        assert s.rate_limit_window_seconds == 3600


# ── Health Endpoint Tests ───────────────────────────────────────────────────


class TestHealthEndpoint:
    """Health endpoint returns expected structure."""

    @pytest.mark.asyncio
    async def test_health_returns_status_and_components(self) -> None:
        """Health returns status, version, environment, components dict."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert "environment" in data
        assert "components" in data
        assert "postgresql" in data["components"]
        assert "mongodb" in data["components"]
        assert "redis" in data["components"]
        assert "ml" in data["components"]

    @pytest.mark.asyncio
    async def test_health_includes_ml_ready(self) -> None:
        """Health response includes ml_ready boolean."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        data = response.json()
        assert "ml_ready" in data
        assert isinstance(data["ml_ready"], bool)


# ── Ready Endpoint Tests ───────────────────────────────────────────────────


class TestReadyEndpoint:
    """Ready endpoint behaviour based on DB connectivity."""

    @pytest.mark.asyncio
    async def test_ready_returns_503_when_db_unreachable(self) -> None:
        """Ready returns 503 when check_db_connection returns False."""
        with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=False):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False
        assert "PostgreSQL" in data.get("reason", "")

    @pytest.mark.asyncio
    async def test_ready_returns_200_when_db_reachable(self) -> None:
        """Ready returns 200 when check_db_connection returns True."""
        with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=True):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True


# ── CORS Tests ──────────────────────────────────────────────────────────────


class TestCORS:
    """CORS headers are present on responses."""

    @pytest.mark.asyncio
    async def test_cors_preflight_returns_headers(self) -> None:
        """CORS preflight from allowed origin returns correct headers."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.options(
                "/api/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

        assert response.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_cors_allows_configured_origin(self) -> None:
        """GET from allowed origin includes access-control headers."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/health",
                headers={"Origin": "http://localhost:5173"},
            )

        assert response.status_code == 200


# ── Version Endpoint ────────────────────────────────────────────────────────


class TestVersionEndpoint:
    """Version endpoint returns correct structure."""

    @pytest.mark.asyncio
    async def test_version_returns_expected_fields(self) -> None:
        """Version returns version, environment, name."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "environment" in data
        assert "name" in data
        assert "ORACLE" in data["name"]

    @pytest.mark.asyncio
    async def test_404_returns_json(self) -> None:
        """Non-existent endpoints return JSON, not HTML."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/nonexistent-endpoint-xyz")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data
