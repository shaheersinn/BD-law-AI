"""
tests/conftest.py — Pytest configuration for ORACLE test suite.

Sets up:
  - asyncio mode for all tests
  - Environment variables for testing (isolated from .env)
  - Shared fixtures: test client, test DB session
"""

from __future__ import annotations

import os

import pytest

# Override environment for tests — never use production settings in tests
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")  # DB 15 = test isolation
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "oracle_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-32chars")
os.environ.setdefault("DEBUG", "true")


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "integration: marks tests requiring live services")
    config.addinivalue_line("markers", "live: marks tests that hit real external URLs (use -m live)")
    config.addinivalue_line("markers", "phase1: marks tests for Phase 1 scrapers")
    config.addinivalue_line("markers", "phase2: marks tests for Phase 2 features")
