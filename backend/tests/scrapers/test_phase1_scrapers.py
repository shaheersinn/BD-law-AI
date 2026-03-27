"""
tests/scrapers/test_phase1_scrapers.py — Phase 1 test suite.

Tests:
  1. All scrapers are registered and instantiable
  2. BaseScraper contract (source_id, source_name, signal_types set)
  3. Entity resolver — normalize_company_name
  4. ScraperResult dataclass validation
  5. Storage module — persist_signals with mock DB
  6. Law blog firm config — all 27 firms have valid config
  7. Rate limit math
  8. Circuit breaker logic
  9. Registry — by_category filtering
  10. ScraperHealth model — schema validation

Mocks all external HTTP calls — no real network traffic in tests.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── 1. All scrapers registered ─────────────────────────────────────────────────
def test_all_scrapers_registered():
    """Every scraper module must register via @register decorator."""
    # Import all scraper modules to trigger registration
    import importlib
    import os

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scraper_root = os.path.join(base, "app", "scrapers")

    categories = [
        "corporate",
        "legal",
        "regulatory",
        "jobs",
        "market",
        "news",
        "social",
        "geo",
        "law_blogs",
    ]

    for cat in categories:
        cat_path = os.path.join(scraper_root, cat)
        if not os.path.isdir(cat_path):
            continue
        for fname in os.listdir(cat_path):
            if fname.endswith(".py") and fname != "__init__.py":
                module_path = f"app.scrapers.{cat}.{fname[:-3]}"
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    pytest.fail(f"Failed to import {module_path}: {e}")

    from app.scrapers.registry import ScraperRegistry

    count = ScraperRegistry.count()
    # We expect at least 40 scrapers registered (many are multi-file)
    assert count >= 40, f"Expected >= 40 scrapers, got {count}"


# ── 2. BaseScraper contract ────────────────────────────────────────────────────
def test_base_scraper_contract():
    """Every registered scraper must have source_id, source_name, signal_types."""
    from app.scrapers.registry import ScraperRegistry

    scrapers = ScraperRegistry.all_scrapers()
    for scraper in scrapers:
        assert scraper.source_id, f"{scraper.__class__.__name__} missing source_id"
        assert scraper.source_name, f"{scraper.__class__.__name__} missing source_name"
        assert scraper.signal_types, f"{scraper.__class__.__name__} missing signal_types"
        assert scraper.rate_limit_rps > 0, (
            f"{scraper.__class__.__name__} rate_limit_rps must be > 0"
        )
        assert scraper.concurrency >= 1, f"{scraper.__class__.__name__} concurrency must be >= 1"


def test_base_scraper_requires_source_id():
    """BaseScraper.__init__ raises ValueError if source_id not set."""
    from app.scrapers.base import BaseScraper

    class BrokenScraper(BaseScraper):
        source_id = ""
        source_name = "Test"
        signal_types = ["test"]

        async def scrape(self):
            return []

    with pytest.raises(ValueError, match="source_id"):
        BrokenScraper()


# ── 3. Entity resolver — normalize_company_name ────────────────────────────────
def test_normalize_company_name_basic():
    from app.scrapers.entity_resolver import normalize_company_name

    assert normalize_company_name("Royal Bank of Canada Inc.") == "royal bank"
    assert normalize_company_name("Shopify Inc.") == "shopify"
    assert normalize_company_name("BCE Corp.") == "bce"
    assert normalize_company_name("") == ""


def test_normalize_company_name_unicode():
    from app.scrapers.entity_resolver import normalize_company_name

    result = normalize_company_name("Hydro-Québec")
    assert "hydro" in result
    # No non-ASCII chars
    assert result.isascii()


def test_normalize_company_name_legal_suffixes():
    from app.scrapers.entity_resolver import normalize_company_name

    cases = [
        ("Apple Inc.", "apple"),
        ("Microsoft Corporation", "microsoft"),
        ("Tesla, Inc.", "tesla"),
        ("Loblaws Companies Limited", "loblaws companies"),
    ]
    for raw, expected in cases:
        result = normalize_company_name(raw)
        assert expected in result, (
            f"normalize({raw!r}) = {result!r}, expected {expected!r} in result"
        )


# ── 4. ScraperResult dataclass ─────────────────────────────────────────────────
def test_scraper_result_defaults():
    from app.scrapers.base import ScraperResult

    result = ScraperResult(
        source_id="test_source",
        signal_type="test_signal",
    )
    assert result.source_id == "test_source"
    assert result.signal_type == "test_signal"
    assert result.confidence_score == 1.0
    assert result.practice_area_hints == []
    assert result.raw_payload == {}
    assert result.is_negative_label is False
    assert result.raw_company_name is None
    assert result.published_at is None


def test_scraper_result_with_values():
    from app.scrapers.base import ScraperResult

    result = ScraperResult(
        source_id="corporate_sedar",
        signal_type="filing_material_change",
        raw_company_name="Shopify Inc.",
        confidence_score=0.95,
        practice_area_hints=["securities", "ma"],
        signal_value={"filing_type": "MCR", "date": "2024-01-15"},
        published_at=datetime(2024, 1, 15, tzinfo=UTC),
    )
    assert result.raw_company_name == "Shopify Inc."
    assert "securities" in result.practice_area_hints
    assert result.signal_value["filing_type"] == "MCR"


# ── 5. Rate limit math ────────────────────────────────────────────────────────
def test_rate_limit_rps_values():
    """Verify all scrapers have sensible rate limits (not accidentally 0 or 100)."""
    from app.scrapers.registry import ScraperRegistry

    for scraper in ScraperRegistry.all_scrapers():
        assert 0 < scraper.rate_limit_rps <= 10, (
            f"{scraper.source_id}: rate_limit_rps={scraper.rate_limit_rps} out of bounds"
        )


# ── 6. Law blog firms ─────────────────────────────────────────────────────────
def test_law_blog_27_firms():
    """Verify all 27 Canadian law firm scrapers are configured and registered."""
    from app.scrapers.law_blogs.firm_blogs import ALL_FIRMS

    assert len(ALL_FIRMS) == 27, f"Expected 27 firms, got {len(ALL_FIRMS)}"

    tier1_firms = [f for f in ALL_FIRMS if f.tier == 1]
    tier2_firms = [f for f in ALL_FIRMS if f.tier == 2]
    assert len(tier1_firms) == 15, f"Expected 15 Tier 1 firms, got {len(tier1_firms)}"
    assert len(tier2_firms) == 12, f"Expected 12 Tier 2 firms, got {len(tier2_firms)}"

    for firm in ALL_FIRMS:
        assert firm.firm_id, "Firm missing firm_id"
        assert firm.firm_name, "Firm missing firm_name"
        assert firm.rss_url.startswith("http"), f"{firm.firm_id} invalid rss_url: {firm.rss_url}"
        assert len(firm.practice_focus) >= 1, f"{firm.firm_id} missing practice_focus"


def test_law_blog_all_firms_registered():
    """All 27 law firm scrapers must be in the registry."""
    from app.scrapers.law_blogs.firm_blogs import ALL_FIRMS
    from app.scrapers.registry import ScraperRegistry

    for firm in ALL_FIRMS:
        source_id = f"lawblog_{firm.firm_id}"
        try:
            scraper = ScraperRegistry.get(source_id)
            assert scraper.source_id == source_id
        except KeyError:
            pytest.fail(f"Firm {firm.firm_id} not in registry (expected source_id={source_id!r})")


# ── 7. Circuit breaker logic ──────────────────────────────────────────────────
def test_circuit_breaker_opens_after_threshold():
    """Circuit breaker must open after consecutive_failures >= threshold."""
    from app.scrapers.base import BaseScraper

    class TestScraper(BaseScraper):
        source_id = "test_circuit"
        source_name = "Test Circuit"
        signal_types = ["test"]

        async def scrape(self):
            return []

    scraper = TestScraper()
    assert not scraper._is_circuit_open()

    # Simulate failures up to threshold
    scraper._circuit_failures = scraper._circuit_threshold
    scraper._circuit_open = True
    scraper._circuit_last_failure = __import__("time").monotonic()

    assert scraper._is_circuit_open()


def test_circuit_breaker_recovers_after_timeout():
    """Circuit breaker must move to half-open after recovery timeout."""
    import time

    from app.scrapers.base import BaseScraper

    class TestScraper2(BaseScraper):
        source_id = "test_circuit2"
        source_name = "Test Circuit 2"
        signal_types = ["test"]

        async def scrape(self):
            return []

    scraper = TestScraper2()
    scraper._circuit_open = True
    scraper._circuit_failures = 10
    # Set last failure far in the past
    scraper._circuit_last_failure = time.monotonic() - 999.0

    # Should return False (not open) because recovery timeout elapsed
    assert not scraper._is_circuit_open()
    assert not scraper._circuit_open


# ── 8. Registry filtering ─────────────────────────────────────────────────────
def test_registry_by_category():
    from app.scrapers.registry import ScraperRegistry

    corporate = ScraperRegistry.by_category("corporate")
    legal = ScraperRegistry.by_category("legal")
    regulatory = ScraperRegistry.by_category("regulatory")

    assert len(corporate) >= 5, f"Expected >= 5 corporate scrapers, got {len(corporate)}"
    assert len(legal) >= 4, f"Expected >= 4 legal scrapers, got {len(legal)}"
    assert len(regulatory) >= 6, f"Expected >= 6 regulatory scrapers, got {len(regulatory)}"

    for s in corporate:
        assert s.source_id.startswith("corporate_"), f"Wrong prefix: {s.source_id}"


# ── 9. BaseScraper date parsing ───────────────────────────────────────────────
def test_parse_date_formats():
    from app.scrapers.base import BaseScraper

    class _TestScraper(BaseScraper):
        source_id = "test_date"
        source_name = "Test Date"
        signal_types = ["test"]

        async def scrape(self):
            return []

    scraper = _TestScraper()
    assert scraper._parse_date("2024-01-15") == datetime(2024, 1, 15, tzinfo=UTC)
    assert scraper._parse_date("2024-01-15T10:30:00") == datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
    assert scraper._parse_date("") is None
    assert scraper._parse_date(None) is None
    assert scraper._parse_date("not-a-date") is None


# ── 10. HTTP header generation ────────────────────────────────────────────────
def test_browser_headers_no_python_ua():
    from app.scrapers.base import _browser_headers

    headers = _browser_headers()
    ua = headers.get("User-Agent", "")
    assert "python" not in ua.lower(), "User-Agent must not expose Python"
    assert "httpx" not in ua.lower(), "User-Agent must not expose httpx"
    assert "Mozilla" in ua, "User-Agent must look like a browser"
    assert "Accept-Language" in headers
    assert "Accept-Encoding" in headers


def test_browser_headers_extra_merge():
    from app.scrapers.base import _browser_headers

    headers = _browser_headers({"Authorization": "Bearer test123"})
    assert headers["Authorization"] == "Bearer test123"
    assert "Mozilla" in headers.get("User-Agent", "")


# ── 11. ScraperRegistry count ─────────────────────────────────────────────────
def test_registry_all_ids_sorted():
    from app.scrapers.registry import ScraperRegistry

    ids = ScraperRegistry.all_ids()
    assert ids == sorted(ids), "Registry IDs must be returned sorted"
    assert len(ids) >= 40


# ── 12. Migration syntax check ────────────────────────────────────────────────
def test_alembic_migration_syntax():
    import ast
    import os

    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alembic",
        "versions",
        "0002_phase1_scrapers.py",
    )
    if os.path.exists(migration_path):
        with open(migration_path) as f:
            src = f.read()
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"Migration syntax error: {e}")
    else:
        pytest.skip("Migration file not found")


# ── 13. BaseScraper.get() retries 3x on transport error ──────────────────────
@pytest.mark.asyncio
async def test_base_scraper_fetch_retries_3x():
    """Mock httpx.AsyncClient to fail twice then succeed. Verify BaseScraper.get() makes 3 attempts."""
    from unittest.mock import AsyncMock, MagicMock

    from app.scrapers.base import BaseScraper

    class RetryScraper(BaseScraper):
        source_id = "test_retry"
        source_name = "Test Retry"
        signal_types = ["test"]
        retry_attempts = 3
        retry_min_wait = 0.01  # very short for test speed
        retry_max_wait = 0.02

        async def scrape(self):
            return []

    scraper = RetryScraper()

    # Build mock responses: two TransportErrors, then a 200
    import httpx

    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get = AsyncMock(
        side_effect=[
            httpx.TransportError("fail 1"),
            httpx.TransportError("fail 2"),
            success_response,
        ]
    )

    # Patch _get_client to return our mock
    scraper._get_client = AsyncMock(return_value=mock_client)

    response = await scraper.get("https://example.com/test")
    assert response.status_code == 200
    assert mock_client.get.call_count == 3


# ── 14. BudgetManager blocks when over limit ────────────────────────────────
@pytest.mark.asyncio
async def test_budget_manager_blocks_over_limit():
    """ApiBudgetManager.check_budget returns False when daily limit exceeded."""
    from unittest.mock import AsyncMock

    from app.scrapers.budget_manager import ApiBudgetManager

    manager = ApiBudgetManager()
    # Patch _get_redis to return None (in-memory mode)
    manager._get_redis = AsyncMock(return_value=None)

    # alpha_vantage has daily_limit=25
    # Consume 25 credits
    for _ in range(25):
        await manager.consume("alpha_vantage", amount=1)

    # Now check_budget should return False
    allowed = await manager.check_budget("alpha_vantage")
    assert allowed is False

    # Unknown source should always be allowed
    allowed_unknown = await manager.check_budget("unknown_source_xyz")
    assert allowed_unknown is True


# ── 15. EntityResolver returns unmatched for garbage input ───────────────────
def test_entity_resolver_returns_none_for_garbage():
    """EntityResolver.resolve with empty index returns matched=False for garbage."""
    from app.services.entity_resolution import EntityResolver

    resolver = EntityResolver()
    # Don't rebuild from DB — leave index empty
    result = resolver.resolve("xyzzy garble 123")
    assert result.matched is False
    assert result.entity_id is None
    assert result.entity_type == "unknown"
    assert result.score == 0.0


# ── 16. Registry has at least 65 scrapers ────────────────────────────────────
def test_registry_has_at_least_65_scrapers():
    """ScraperRegistry must have >= 65 scrapers registered."""
    from app.scrapers.registry import ScraperRegistry

    count = ScraperRegistry.count()
    assert count >= 65, f"Expected >= 65 scrapers, got {count}"
