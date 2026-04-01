"""Live smoke tests for scrapers — only run with: pytest -m live

These tests hit REAL public URLs.  Run manually before each production deploy.
They are excluded from CI (pytest ignores tests/integration by default in CI).

Usage:
    # Run all live tests
    pytest tests/integration/test_scraper_live_smoke.py -v -m live

    # Run a single scraper live test
    pytest tests/integration/test_scraper_live_smoke.py::test_scac_live -v

Each test:
  - Creates the real scraper instance (no mocks)
  - Calls scraper.scrape() against the live public URL
  - Asserts >= 1 result returned
  - Verifies result structure (source_id, signal_type, confidence bounds)

Only free, publicly accessible sources are tested here.
Any scraper that requires a paid API key is skipped automatically.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-32chars")

from app.scrapers.base import ScraperResult  # noqa: E402
from app.scrapers.registry import ScraperRegistry  # noqa: E402

# Apply the live marker to the entire module
pytestmark = pytest.mark.live


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_valid_results(results: list[ScraperResult], source_id: str) -> None:
    """Common result assertions for all live smoke tests."""
    assert isinstance(results, list), f"{source_id}: scrape() must return a list"
    assert len(results) > 0, f"{source_id}: expected >= 1 result from live site"
    for r in results:
        assert isinstance(r, ScraperResult), f"{source_id}: results must be ScraperResult"
        assert r.source_id == source_id, f"Expected source_id={source_id}, got {r.source_id}"
        assert isinstance(r.signal_type, str) and len(r.signal_type) > 0
        assert r.source_url or r.raw_company_name, (
            f"{source_id}: result must have source_url or raw_company_name"
        )
        assert 0.0 <= r.confidence_score <= 1.0, (
            f"{source_id}: confidence_score out of bounds: {r.confidence_score}"
        )
        assert isinstance(r.practice_area_hints, list)


# ── Class Action Scrapers ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.live
async def test_siskinds_live() -> None:
    """Siskinds LLP class actions page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_siskinds")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_siskinds")
    assert all(r.signal_type.startswith("class_action_") for r in results)


@pytest.mark.asyncio
@pytest.mark.live
async def test_ontario_class_proceedings_live() -> None:
    """Ontario Superior Court class proceedings page returns >= 1 result."""
    scraper = ScraperRegistry.get("class_actions_ontario")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_ontario")


@pytest.mark.asyncio
@pytest.mark.live
async def test_bc_class_proceedings_live() -> None:
    """BC Supreme Court class proceedings page returns >= 1 result."""
    scraper = ScraperRegistry.get("class_actions_bc")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_bc")


@pytest.mark.asyncio
@pytest.mark.live
async def test_federal_court_class_proceedings_live() -> None:
    """Federal Court class proceedings page returns >= 1 result."""
    scraper = ScraperRegistry.get("class_actions_federal")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_federal")


@pytest.mark.asyncio
@pytest.mark.live
async def test_cba_class_actions_live() -> None:
    """CBA class actions page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_cba")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_cba")


@pytest.mark.asyncio
@pytest.mark.live
async def test_classaction_aggregator_live() -> None:
    """classaction.org/canada page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_aggregator")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_aggregator")


@pytest.mark.asyncio
@pytest.mark.live
async def test_branch_macmaster_live() -> None:
    """Branch MacMaster class actions page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_branch_macmaster")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_branch_macmaster")


@pytest.mark.asyncio
@pytest.mark.live
async def test_koskie_minsky_live() -> None:
    """Koskie Minsky class actions page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_koskie_minsky")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_koskie_minsky")


@pytest.mark.asyncio
@pytest.mark.live
async def test_merchant_law_live() -> None:
    """Merchant Law class actions page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_merchant_law")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_merchant_law")


@pytest.mark.asyncio
@pytest.mark.live
async def test_alberta_class_proceedings_live() -> None:
    """Alberta Courts class proceedings page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_alberta")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_alberta")


@pytest.mark.asyncio
@pytest.mark.live
async def test_quebec_class_proceedings_live() -> None:
    """Quebec courts class proceedings page returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_quebec")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_quebec")


@pytest.mark.asyncio
@pytest.mark.live
async def test_courtlistener_class_actions_live() -> None:
    """CourtListener/PACER class actions API returns at least 1 result."""
    scraper = ScraperRegistry.get("class_actions_courtlistener")
    results = await scraper.scrape()
    _assert_valid_results(results, "class_actions_courtlistener")
    assert all(
        r.signal_type in ("class_action_filed_us", "class_action_certified_us")
        for r in results
    )


# ── Consumer Precursor Scrapers ───────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.live
async def test_health_canada_recalls_live() -> None:
    """Health Canada RSS feed returns at least 1 recall result."""
    scraper = ScraperRegistry.get("consumer_health_canada_recalls")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_health_canada_recalls")
    assert all(r.signal_type == "recall_health_canada" for r in results)


@pytest.mark.asyncio
@pytest.mark.live
async def test_transport_canada_recalls_live() -> None:
    """Transport Canada RSS feed returns at least 1 recall result."""
    scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_transport_canada_recalls")


@pytest.mark.asyncio
@pytest.mark.live
async def test_cpsc_recalls_live() -> None:
    """CPSC recall RSS feed returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_cpsc_recalls")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_cpsc_recalls")
    assert all(r.signal_type == "recall_cpsc_us" for r in results)


@pytest.mark.asyncio
@pytest.mark.live
async def test_bbb_complaints_live() -> None:
    """BBB complaints RSS/news returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_bbb_complaints")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_bbb_complaints")


@pytest.mark.asyncio
@pytest.mark.live
async def test_opc_breach_reports_live() -> None:
    """OPC PIPEDA findings page returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_opc_breach_reports")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_opc_breach_reports")
    assert all(
        r.signal_type in ("privacy_enforcement", "privacy_breach_report") for r in results
    )


@pytest.mark.asyncio
@pytest.mark.live
async def test_obsi_decisions_live() -> None:
    """OBSI decisions page returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_obsi_decisions")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_obsi_decisions")


@pytest.mark.asyncio
@pytest.mark.live
async def test_ccts_complaints_live() -> None:
    """CCTS news/reports page returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_ccts_complaints")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_ccts_complaints")


@pytest.mark.asyncio
@pytest.mark.live
async def test_provincial_privacy_commissioners_live() -> None:
    """Provincial privacy commissioners page returns at least 1 result."""
    scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
    results = await scraper.scrape()
    _assert_valid_results(results, "consumer_provincial_privacy_commissioners")
    assert all(r.signal_type == "privacy_provincial_finding" for r in results)
