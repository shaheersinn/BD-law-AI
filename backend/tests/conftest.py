"""
tests/conftest.py — Shared pytest fixtures.

Provides:
  - async_client: httpx.AsyncClient pointed at the test app
  - mock_db: mocked AsyncSession
  - auth_headers: JWT headers for different roles
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


# ── Event loop ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ── Settings override ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """Use test-safe settings — no real DB or Redis needed for unit tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-long-enough-for-jwt")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    monkeypatch.setenv("ENVIRONMENT", "test")


# ── Auth helpers ───────────────────────────────────────────────────────────────

def _make_user(role_str: str, user_id: int = 1, partner_id: int = None):
    from app.auth.models import User, UserRole
    from app.auth.service import create_access_token
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"{role_str}@halcyon.legal"
    user.role = UserRole(role_str)
    user.partner_id = partner_id
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return _make_user("admin", user_id=1)


@pytest.fixture
def partner_headers():
    return _make_user("partner", user_id=2, partner_id=1)


@pytest.fixture
def associate_headers():
    return _make_user("associate", user_id=3)


@pytest.fixture
def readonly_headers():
    return _make_user("readonly", user_id=4)


# ── Mock cache ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_cache(monkeypatch):
    """Replace cache with an in-memory mock."""
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ttl=None):
        store[key] = value
        return True

    async def mock_delete(key):
        store.pop(key, None)
        return True

    async def mock_exists(key):
        return key in store

    async def mock_health():
        return True

    from app.cache import client as cache_module
    monkeypatch.setattr(cache_module.cache, "get", mock_get)
    monkeypatch.setattr(cache_module.cache, "set", mock_set)
    monkeypatch.setattr(cache_module.cache, "delete", mock_delete)
    monkeypatch.setattr(cache_module.cache, "exists", mock_exists)
    monkeypatch.setattr(cache_module.cache, "health_check", mock_health)
    return store
