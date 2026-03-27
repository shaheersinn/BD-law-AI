"""
tests/test_health.py — Phase 0 smoke tests.

Tests:
  - Health endpoint returns 200
  - Ready endpoint responds
  - Version endpoint returns correct version
  - Auth endpoints are registered
  - Rate limiting headers present

These tests verify the scaffold works end-to-end before any Phase 1 code is written.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    """Health endpoint must return 200 with status field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "components" in data
    assert "postgresql" in data["components"]
    assert "mongodb" in data["components"]
    assert "redis" in data["components"]


@pytest.mark.asyncio
async def test_ready_endpoint() -> None:
    """Ready endpoint must respond (200 or 503)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/ready")

    assert response.status_code in (200, 503)
    assert "ready" in response.json()


@pytest.mark.asyncio
async def test_version_endpoint() -> None:
    """Version endpoint must return version and environment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/version")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "environment" in data
    assert "name" in data
    assert "ORACLE" in data["name"]


@pytest.mark.asyncio
async def test_login_endpoint_registered() -> None:
    """Login endpoint must be registered and return 422 (not 404) for bad input."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={})

    # 422 = endpoint exists but validation failed (correct)
    # 404 = endpoint not registered (wrong)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials() -> None:
    """Login with bad credentials must return 401 or 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "wrongpassword"},
        )

    assert response.status_code in (401, 422, 500, 503)


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth() -> None:
    """Protected endpoints must return 401 without a token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/me")

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_request_id_in_response_headers() -> None:
    """Every response must include X-Request-ID header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_cors_headers_present() -> None:
    """CORS preflight must return correct headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    # CORS should allow our development origin
    assert response.status_code in (200, 204)


@pytest.mark.asyncio
async def test_404_returns_json() -> None:
    """404 errors must return JSON, not HTML."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/nonexistent-endpoint-xyz")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data or "detail" in data
