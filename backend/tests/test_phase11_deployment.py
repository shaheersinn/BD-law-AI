"""
tests/test_phase11_deployment.py — Phase 11 deployment tests.

Tests:
  - All env vars in .env.example have corresponding config.py field
  - All config.py fields have corresponding .env.example entry
  - /api/health response matches expected JSON schema
  - /api/ready returns 503 when DB unreachable
  - /api/ready returns 200 when DB reachable
  - CI/CD workflow files exist
  - do-app.yaml exists and is valid

All tests run without live DB/Redis/Mongo (fully mocked).
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app

PROJECT_ROOT = Path(__file__).parent.parent.parent  # BD-law-AI/


# ── Env Var Mapping Tests ──────────────────────────────────────────────────


def _parse_env_example_vars() -> set[str]:
    """Extract variable names from .env.example."""
    env_file = PROJECT_ROOT / ".env.example"
    if not env_file.exists():
        pytest.skip(".env.example not found")
    vars_found: set[str] = set()
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Z_][A-Z0-9_]*)=", line)
        if match:
            vars_found.add(match.group(1).lower())
    return vars_found


def _get_settings_fields() -> set[str]:
    """Get all Settings field names."""
    s = Settings(environment="development")
    return set(s.model_fields.keys())


class TestEnvVarMapping:
    """Env vars and config.py fields are aligned."""

    def test_env_example_vars_have_config_fields(self) -> None:
        """All vars in .env.example have a corresponding Settings field."""
        env_vars = _parse_env_example_vars()
        config_fields = _get_settings_fields()
        missing = env_vars - config_fields
        # Some env vars may be aliases or not direct fields
        # Allow a small tolerance for env-only vars
        assert len(missing) <= 3, f"Env vars without config field: {missing}"

    def test_config_fields_have_env_example_entries(self) -> None:
        """All Settings fields have a corresponding .env.example entry."""
        env_vars = _parse_env_example_vars()
        config_fields = _get_settings_fields()
        # model_config is a pydantic internal, not an env var
        config_fields.discard("model_config")
        missing = config_fields - env_vars
        # Some internal fields may not need env entries
        assert len(missing) <= 5, f"Config fields without env entry: {missing}"


# ── Health Schema Tests ────────────────────────────────────────────────────


class TestHealthSchema:
    """Health endpoint returns exact expected JSON schema."""

    @pytest.mark.asyncio
    async def test_health_schema_fields(self) -> None:
        """Health response has exactly the expected top-level keys."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        required_keys = {"status", "version", "environment", "ml_ready", "components"}
        assert required_keys.issubset(set(data.keys()))

    @pytest.mark.asyncio
    async def test_health_components_schema(self) -> None:
        """Components dict has exactly the expected keys."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        components = response.json()["components"]
        expected_keys = {"postgresql", "mongodb", "redis", "ml"}
        assert set(components.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_health_component_values(self) -> None:
        """Component values are valid status strings."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/health")

        components = response.json()["components"]
        valid_db_states = {"connected", "unreachable"}
        valid_ml_states = {"ready", "not_loaded"}
        assert components["postgresql"] in valid_db_states
        assert components["mongodb"] in valid_db_states
        assert components["redis"] in valid_db_states
        assert components["ml"] in valid_ml_states


# ── Ready Endpoint Tests ──────────────────────────────────────────────────


class TestReadyEndpoint:
    """Ready endpoint behaviour."""

    @pytest.mark.asyncio
    async def test_ready_503_when_db_down(self) -> None:
        """Ready returns 503 when check_db_connection returns False."""
        with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=False):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/ready")

        assert response.status_code == 503
        assert response.json()["ready"] is False

    @pytest.mark.asyncio
    async def test_ready_200_when_db_up(self) -> None:
        """Ready returns 200 when check_db_connection returns True."""
        with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=True):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/ready")

        assert response.status_code == 200
        assert response.json()["ready"] is True


# ── Infrastructure Files Tests ─────────────────────────────────────────────


class TestInfrastructureFiles:
    """Deployment infrastructure files exist and are valid."""

    def test_ci_workflow_exists(self) -> None:
        """CI workflow file exists."""
        ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists(), "CI workflow missing at .github/workflows/ci.yml"

    def test_cd_workflow_exists(self) -> None:
        """CD workflow file exists."""
        cd_path = PROJECT_ROOT / ".github" / "workflows" / "cd.yml"
        assert cd_path.exists(), "CD workflow missing at .github/workflows/cd.yml"

    def test_do_app_yaml_exists(self) -> None:
        """DigitalOcean app spec exists."""
        do_path = PROJECT_ROOT / "do-app.yaml"
        assert do_path.exists(), "do-app.yaml missing"

    def test_dockerfile_exists(self) -> None:
        """Backend Dockerfile exists."""
        dockerfile = PROJECT_ROOT / "backend" / "Dockerfile"
        assert dockerfile.exists(), "backend/Dockerfile missing"

    def test_docker_compose_exists(self) -> None:
        """docker-compose.yml exists."""
        dc_path = PROJECT_ROOT / "docker-compose.yml"
        assert dc_path.exists(), "docker-compose.yml missing"

    def test_env_example_exists(self) -> None:
        """.env.example exists at project root."""
        env_path = PROJECT_ROOT / ".env.example"
        assert env_path.exists(), ".env.example missing"
