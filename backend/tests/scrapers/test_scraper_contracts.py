"""Universal contract tests for ALL registered scrapers.

Verifies:
  - Every scraper has required attributes (source_id, source_name, signal_types, etc.)
  - All source_ids are unique across the entire registry
  - Minimum scraper count >= 90 (regression guard against accidental deregistration)
  - scrape() is an async coroutine function
  - health_check() exists on every scraper
"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-32chars")

from app.scrapers.registry import _REGISTRY, _load_registry  # noqa: E402


def get_all_scraper_classes() -> list[type]:
    """Load the registry and return all scraper classes."""
    _load_registry()
    return list(_REGISTRY.values())


# ── Registry count guard ──────────────────────────────────────────────────────


def test_registry_minimum_count() -> None:
    """Regression guard — catches accidental deregistration."""
    _load_registry()
    count = len(_REGISTRY)
    assert count >= 90, (
        f"Expected >= 90 scrapers, got {count}. "
        "Scrapers were likely deregistered accidentally."
    )


def test_registry_source_ids_all_unique() -> None:
    """No two scrapers may share the same source_id."""
    _load_registry()
    ids = [cls().source_id for cls in _REGISTRY.values()]
    duplicates = [x for x in set(ids) if ids.count(x) > 1]
    assert len(ids) == len(set(ids)), f"Duplicate source_ids found: {duplicates}"


# ── Parametrised per-scraper contract tests ───────────────────────────────────


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_source_id(scraper_cls: type) -> None:
    """source_id must be a non-empty string."""
    scraper = scraper_cls()
    assert isinstance(scraper.source_id, str), (
        f"{scraper_cls.__name__}: source_id must be str"
    )
    assert len(scraper.source_id) > 0, (
        f"{scraper_cls.__name__}: source_id must not be empty"
    )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_source_name(scraper_cls: type) -> None:
    """source_name must be a non-empty string."""
    scraper = scraper_cls()
    assert isinstance(scraper.source_name, str), (
        f"{scraper_cls.__name__}: source_name must be str"
    )
    assert len(scraper.source_name) > 0, (
        f"{scraper_cls.__name__}: source_name must not be empty"
    )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_signal_types(scraper_cls: type) -> None:
    """signal_types must be a non-empty list."""
    scraper = scraper_cls()
    assert isinstance(scraper.signal_types, list), (
        f"{scraper_cls.__name__}: signal_types must be a list"
    )
    assert len(scraper.signal_types) > 0, (
        f"{scraper_cls.__name__}: signal_types must have at least one entry"
    )
    for st in scraper.signal_types:
        assert isinstance(st, str) and len(st) > 0, (
            f"{scraper_cls.__name__}: every signal_type must be a non-empty string"
        )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_rate_limit_positive(scraper_cls: type) -> None:
    """rate_limit_rps must be a positive number."""
    scraper = scraper_cls()
    assert scraper.rate_limit_rps > 0, (
        f"{scraper_cls.__name__}: rate_limit_rps must be > 0, got {scraper.rate_limit_rps}"
    )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_concurrency_valid(scraper_cls: type) -> None:
    """concurrency must be >= 1."""
    scraper = scraper_cls()
    assert scraper.concurrency >= 1, (
        f"{scraper_cls.__name__}: concurrency must be >= 1, got {scraper.concurrency}"
    )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_scrape_method(scraper_cls: type) -> None:
    """scrape() must exist and be an async coroutine function."""
    scraper = scraper_cls()
    assert hasattr(scraper, "scrape"), f"{scraper_cls.__name__}: missing scrape() method"
    assert asyncio.iscoroutinefunction(scraper.scrape), (
        f"{scraper_cls.__name__}: scrape() must be an async coroutine function"
    )


@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_health_check(scraper_cls: type) -> None:
    """health_check() must exist."""
    scraper = scraper_cls()
    assert hasattr(scraper, "health_check"), (
        f"{scraper_cls.__name__}: missing health_check() method"
    )
