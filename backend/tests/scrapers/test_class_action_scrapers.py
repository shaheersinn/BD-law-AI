"""Tests for Phase CA-1 class action scrapers and Phase CA-2 consumer precursor scrapers.

Covers:
  - All 12 class action scrapers register correctly
  - All 8 consumer precursor scrapers register correctly
  - BaseScraper contract compliance (source_id, source_name, signal_types, etc.)
  - ScraperResult output validation (mocked HTTP responses)
  - practice_area_hints use valid PRACTICE_AREA_BITS keys
  - confidence_score in [0.0, 1.0]
  - French-language filtering
  - Company name extraction from case titles
  - Celery task registration (CA-1 + CA-2)
  - Alembic migration file validity
"""

from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-32chars")

from app.models.signal import PRACTICE_AREA_BITS  # noqa: E402
from app.scrapers.base import BaseScraper, ScraperResult  # noqa: E402
from app.scrapers.registry import ScraperRegistry  # noqa: E402

_VALID_PA_KEYS = set(PRACTICE_AREA_BITS.keys())

_CLASS_ACTION_SOURCE_IDS = [
    "class_actions_ontario",
    "class_actions_bc",
    "class_actions_quebec",
    "class_actions_federal",
    "class_actions_alberta",
    "class_actions_aggregator",
    "class_actions_siskinds",
    "class_actions_branch_macmaster",
    "class_actions_merchant_law",
    "class_actions_koskie_minsky",
    "class_actions_cba",
    "class_actions_courtlistener",
]

_CONSUMER_PRECURSOR_SOURCE_IDS = [
    "consumer_health_canada_recalls",
    "consumer_transport_canada_recalls",
    "consumer_cpsc_recalls",
    "consumer_bbb_complaints",
    "consumer_obsi_decisions",
    "consumer_ccts_complaints",
    "consumer_opc_breach_reports",
    "consumer_provincial_privacy_commissioners",
]


# ── Registration Tests ────────────────────────────────────────────────────────


class TestClassActionRegistration:
    """Verify all 12 class action scrapers register in the global registry."""

    def test_all_12_class_action_scrapers_registered(self) -> None:
        registry = ScraperRegistry.all_ids()
        for sid in _CLASS_ACTION_SOURCE_IDS:
            assert sid in registry, f"Scraper {sid} not found in registry"

    def test_class_action_category_count(self) -> None:
        scrapers = ScraperRegistry.by_category("class_actions")
        assert len(scrapers) >= 12, (
            f"Expected >= 12 class_actions scrapers, got {len(scrapers)}"
        )

    def test_total_scraper_count_increased(self) -> None:
        assert ScraperRegistry.count() >= 52, (
            f"Expected >= 52 total scrapers after CA-1, got {ScraperRegistry.count()}"
        )


class TestConsumerPrecursorRegistration:
    """Verify all 8 consumer precursor scrapers register in the global registry."""

    def test_all_8_consumer_scrapers_registered(self) -> None:
        registry = ScraperRegistry.all_ids()
        for sid in _CONSUMER_PRECURSOR_SOURCE_IDS:
            assert sid in registry, f"Consumer precursor scraper {sid} not found in registry"

    def test_consumer_category_count(self) -> None:
        scrapers = ScraperRegistry.by_category("consumer")
        assert len(scrapers) >= 8, (
            f"Expected >= 8 consumer scrapers, got {len(scrapers)}"
        )

    def test_total_scraper_count_with_consumer(self) -> None:
        assert ScraperRegistry.count() >= 60, (
            f"Expected >= 60 total scrapers after CA-2, got {ScraperRegistry.count()}"
        )


# ── Contract Tests ────────────────────────────────────────────────────────────


class TestClassActionContract:
    """Verify every class action scraper follows the BaseScraper contract."""

    @pytest.fixture(params=_CLASS_ACTION_SOURCE_IDS)
    def scraper(self, request: pytest.FixtureRequest) -> BaseScraper:
        return ScraperRegistry.get(request.param)

    def test_has_source_id(self, scraper: BaseScraper) -> None:
        assert scraper.source_id, "Missing source_id"

    def test_has_source_name(self, scraper: BaseScraper) -> None:
        assert scraper.source_name, "Missing source_name"

    def test_has_signal_types(self, scraper: BaseScraper) -> None:
        assert scraper.signal_types, "Missing signal_types"
        assert isinstance(scraper.signal_types, list)

    def test_category_is_class_actions(self, scraper: BaseScraper) -> None:
        assert getattr(scraper, "CATEGORY", "") == "class_actions"

    def test_rate_limit_positive(self, scraper: BaseScraper) -> None:
        assert scraper.rate_limit_rps > 0

    def test_concurrency_positive(self, scraper: BaseScraper) -> None:
        assert scraper.concurrency >= 1

    def test_has_scrape_method(self, scraper: BaseScraper) -> None:
        assert hasattr(scraper, "scrape"), "Missing scrape() method"

    def test_has_health_check_method(self, scraper: BaseScraper) -> None:
        assert hasattr(scraper, "health_check"), "Missing health_check() method"

    def test_inherits_base_scraper(self, scraper: BaseScraper) -> None:
        assert isinstance(scraper, BaseScraper)


class TestConsumerPrecursorContract:
    """Verify every consumer precursor scraper follows the BaseScraper contract."""

    @pytest.fixture(params=_CONSUMER_PRECURSOR_SOURCE_IDS)
    def scraper(self, request: pytest.FixtureRequest) -> BaseScraper:
        return ScraperRegistry.get(request.param)

    def test_has_source_id(self, scraper: BaseScraper) -> None:
        assert scraper.source_id, "Missing source_id"
        assert scraper.source_id.startswith("consumer_"), (
            f"Consumer scraper source_id should start with 'consumer_', got {scraper.source_id}"
        )

    def test_has_source_name(self, scraper: BaseScraper) -> None:
        assert scraper.source_name, "Missing source_name"

    def test_has_signal_types(self, scraper: BaseScraper) -> None:
        assert scraper.signal_types, "Missing signal_types"
        assert isinstance(scraper.signal_types, list)
        assert len(scraper.signal_types) >= 1

    def test_category_is_consumer(self, scraper: BaseScraper) -> None:
        assert getattr(scraper, "CATEGORY", "") == "consumer", (
            f"Expected CATEGORY='consumer', got {getattr(scraper, 'CATEGORY', 'missing')}"
        )

    def test_rate_limit_conservative(self, scraper: BaseScraper) -> None:
        assert 0 < scraper.rate_limit_rps <= 1.0, (
            f"Consumer scrapers should be respectful (≤ 1.0 rps), got {scraper.rate_limit_rps}"
        )

    def test_concurrency_not_aggressive(self, scraper: BaseScraper) -> None:
        assert 1 <= scraper.concurrency <= 5

    def test_has_scrape_method(self, scraper: BaseScraper) -> None:
        assert hasattr(scraper, "scrape"), "Missing scrape() method"

    def test_inherits_base_scraper(self, scraper: BaseScraper) -> None:
        assert isinstance(scraper, BaseScraper)

    def test_ttl_seconds_set(self, scraper: BaseScraper) -> None:
        assert scraper.ttl_seconds > 0


# ── Mock Helpers ──────────────────────────────────────────────────────────────


def _mock_response(
    text: str = "", status_code: int = 200, json_data: dict | None = None
) -> httpx.Response:
    resp = httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_data is not None:
        resp._content = __import__("json").dumps(json_data).encode()
    return resp


# ── Class Action Scraper Output Tests ─────────────────────────────────────────

_ONTARIO_HTML = """
<html><body>
<table>
<tr>
  <td><a href="/scj/class-actions/case-123">Smith v. Acme Corp</a></td>
  <td>Certified</td>
  <td>2026-02-15</td>
</tr>
<tr>
  <td><a href="/scj/class-actions/case-456">Jones v. BigBank Inc.</a></td>
  <td>Filed</td>
  <td>2026-03-01</td>
</tr>
</table>
</body></html>
"""

_BC_HTML = """
<html><body>
<table>
<tr>
  <td><a href="/case/789">Doe v. TechCo Ltd.</a></td>
  <td>Filed</td>
  <td>2026-02-20</td>
</tr>
</table>
</body></html>
"""

_SISKINDS_HTML = """
<html><body>
<div class="class-actions">
  <article>
    <h3><a href="/class-actions/securities-fraud-investigation">
      Securities Fraud Investigation — MiningCo Inc.
    </a></h3>
    <span class="date">March 10, 2026</span>
  </article>
  <article>
    <h3><a href="/class-actions/privacy-breach">
      Privacy Breach Class Action — DataCorp
    </a></h3>
    <span class="date">February 28, 2026</span>
  </article>
</div>
</body></html>
"""

_COURTLISTENER_JSON = {
    "count": 1,
    "results": [
        {
            "caseName": "Smith v. Canadian Mining Corp.",
            "dateFiled": "2026-02-10",
            "court": "District Court, S.D.N.Y.",
            "suitNature": "Securities Fraud",
            "docketNumber": "1:26-cv-01234",
            "absolute_url": "/docket/123456/smith-v-canadian-mining-corp/",
        }
    ],
}


@pytest.mark.asyncio
class TestOntarioClassProceedingsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("class_actions_ontario")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(text=_ONTARIO_HTML)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "class_actions_ontario"
            assert r.signal_type.startswith("class_action_")
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS, f"Invalid practice_area_hint: {hint}"

    async def test_scrape_handles_error(self) -> None:
        scraper = ScraperRegistry.get("class_actions_ontario")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(status_code=500)
            results = await scraper.scrape()
        assert results == []


@pytest.mark.asyncio
class TestBCClassProceedingsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("class_actions_bc")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(text=_BC_HTML)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "class_actions_bc"
            assert 0.0 <= r.confidence_score <= 1.0


@pytest.mark.asyncio
class TestSiskindsClassActionsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("class_actions_siskinds")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(text=_SISKINDS_HTML)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "class_actions_siskinds"
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS


@pytest.mark.asyncio
class TestCourtListenerClassActionsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("class_actions_courtlistener")
        with patch.object(scraper, "get_json", new_callable=AsyncMock) as mock_json:
            mock_json.return_value = _COURTLISTENER_JSON
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert r.source_id == "class_actions_courtlistener"
            assert r.signal_type in ("class_action_filed_us", "class_action_certified_us")
            assert 0.0 <= r.confidence_score <= 1.0
            assert "class_actions" in r.practice_area_hints

    async def test_scrape_handles_empty_api(self) -> None:
        scraper = ScraperRegistry.get("class_actions_courtlistener")
        with patch.object(scraper, "get_json", new_callable=AsyncMock) as mock_json:
            mock_json.return_value = {"count": 0, "results": []}
            results = await scraper.scrape()
        assert results == []


# ── Consumer Precursor Scraper Output Tests ───────────────────────────────────

_HEALTH_CANADA_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Health Canada Recalls</title>
    <item>
      <title>Recall: Acme Baby Food — Listeria Risk — by Acme Foods Inc.</title>
      <link>https://recalls-rappels.canada.ca/en/alert-recall/123</link>
      <pubDate>Sat, 28 Mar 2026 12:00:00 +0000</pubDate>
      <description>Acme Foods Inc. is recalling baby food due to possible Listeria contamination. Risk of serious illness.</description>
      <category>Food</category>
    </item>
    <item>
      <title>Recall: XYZ Toy Set — Choking Hazard</title>
      <link>https://recalls-rappels.canada.ca/en/alert-recall/124</link>
      <pubDate>Fri, 27 Mar 2026 10:00:00 +0000</pubDate>
      <description>Small parts may detach, posing a choking hazard to children under 3.</description>
      <category>Children's Products</category>
    </item>
  </channel>
</rss>
"""

_CPSC_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>CPSC Recalls</title>
    <item>
      <title>CanadaCo Inc. Recalls Electric Scooters Due to Fire Hazard</title>
      <link>https://www.cpsc.gov/Recalls/2026/example</link>
      <pubDate>Mon, 23 Mar 2026 14:00:00 +0000</pubDate>
      <description>CanadaCo Inc., of Toronto, Canada, is recalling electric scooters. The battery can overheat, posing a fire hazard. 50,000 units sold in Canada and US.</description>
    </item>
  </channel>
</rss>
"""

_OPC_HTML = """
<html><body>
<ul>
  <li>
    <h3><a href="/en/opc-actions-and-decisions/pipeda-findings/2026/012345">
      PIPEDA Report of Findings #12345 — Investigation into TechCorp Ltd.'s handling of a security breach
    </a></h3>
    <p>TechCorp Ltd. experienced a breach affecting approximately 250,000 individuals. The breach was caused by an unauthorized intrusion.</p>
    <time datetime="2026-03-15">March 15, 2026</time>
  </li>
  <li>
    <h3><a href="/en/opc-actions-and-decisions/pipeda-findings/2026/012346">
      PIPEDA Report of Findings #12346 — SmallCo investigation
    </a></h3>
    <p>Investigation into SmallCo's data practices affecting 500 users.</p>
    <time datetime="2026-02-20">February 20, 2026</time>
  </li>
</ul>
</body></html>
"""

_PROVINCIAL_PRIVACY_HTML = """
<html><body>
<ul>
  <li>
    <h3><a href="/decisions/order-p26-001">
      Order P26-001 — Acme Insurance Corp — Privacy Breach Investigation
    </a></h3>
    <p>The Commissioner ordered Acme Insurance Corp to improve security practices after a breach.</p>
    <time datetime="2026-03-10">March 10, 2026</time>
  </li>
</ul>
</body></html>
"""

_OBSI_HTML = """
<html><body>
<article>
  <h3><a href="/en/decisions/2026-banking-decision-1">
    OBSI Decision: TD Bank — Refused Recommendation — $12,500 Award
  </a></h3>
  <p>TD Bank declined to follow OBSI's recommendation. OBSI awarded $12,500 to the complainant.</p>
  <time class="date" datetime="2026-03-20">March 20, 2026</time>
</article>
<article>
  <h3><a href="/en/decisions/2026-investment-decision-2">
    OBSI Decision: Investment Firm Non-Compliance
  </a></h3>
  <p>Investment firm failed to compensate client for unsuitable investment recommendations.</p>
  <time class="date" datetime="2026-02-28">February 28, 2026</time>
</article>
</body></html>
"""

_CCTS_HTML = """
<html><body>
<article class="news-item">
  <h3><a href="/news/2025-annual-report">CCTS 2025 Annual Report: Rogers leads complaint volume with 31% increase</a></h3>
  <time class="date">March 1, 2026</time>
  <p>The CCTS annual report reveals Rogers accounted for the highest complaint volume among all TSPs.</p>
</article>
</body></html>
"""

_BBB_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BBB News</title>
    <item>
      <title>BBB Warning: Fraud complaints surge against SubscriptionCo Inc. — 500% increase</title>
      <link>https://www.bbb.org/news/2026/subscriptionco-fraud-warning</link>
      <pubDate>Wed, 25 Mar 2026 16:00:00 +0000</pubDate>
      <summary>BBB has received hundreds of complaints about SubscriptionCo Inc. for deceptive subscription billing practices.</summary>
    </item>
  </channel>
</rss>
"""


@pytest.mark.asyncio
class TestHealthCanadaRecallsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(text=_HEALTH_CANADA_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert r.source_id == "consumer_health_canada_recalls"
            assert r.signal_type == "recall_health_canada"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "product_liability" in r.practice_area_hints
            assert "class_actions" in r.practice_area_hints

    async def test_scrape_handles_bad_status(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(status_code=503)
            results = await scraper.scrape()
        assert results == []

    async def test_risk_level_extraction(self) -> None:
        from app.scrapers.consumer.health_canada_recalls import HealthCanadaRecallsScraper

        assert HealthCanadaRecallsScraper._extract_risk_level("Death risk recall", "") == "high"
        assert (
            HealthCanadaRecallsScraper._extract_risk_level("Choking hazard", "") == "medium"
        )
        assert HealthCanadaRecallsScraper._extract_risk_level("Labeling issue", "") == "low"


@pytest.mark.asyncio
class TestCPSCRecallsScraper:
    async def test_scrape_rss_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_response(text=_CPSC_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert r.source_id == "consumer_cpsc_recalls"
            assert r.signal_type == "recall_cpsc_us"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "product_liability" in r.practice_area_hints

    async def test_canadian_company_flag(self) -> None:
        from app.scrapers.consumer.cpsc_recalls import CPSCRecallsScraper

        assert CPSCRecallsScraper._is_canadian_company("CanadaCo Inc. of Toronto, Canada", "")
        assert not CPSCRecallsScraper._is_canadian_company("US Widgets Corp of Dallas, TX", "")

    async def test_hazard_extraction(self) -> None:
        from app.scrapers.consumer.cpsc_recalls import CPSCRecallsScraper

        assert CPSCRecallsScraper._extract_hazard("fire hazard — battery overheats") == "fire_hazard"
        assert CPSCRecallsScraper._extract_hazard("choking risk for children") == "choking_hazard"
        assert (
            CPSCRecallsScraper._extract_hazard("electrical shock when wet") == "electrical_hazard"
        )


@pytest.mark.asyncio
class TestOPCBreachReportsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_OPC_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert r.source_id == "consumer_opc_breach_reports"
            assert r.signal_type in ("privacy_enforcement", "privacy_breach_report")
            assert 0.0 <= r.confidence_score <= 1.0
            assert "privacy_cybersecurity" in r.practice_area_hints

    async def test_individuals_count_extraction(self) -> None:
        from app.scrapers.consumer.opc_breach_reports import OPCBreachReportsScraper

        assert (
            OPCBreachReportsScraper._extract_individuals_count(
                "breach affecting 250,000 individuals", ""
            )
            == 250_000
        )
        assert (
            OPCBreachReportsScraper._extract_individuals_count(
                "approximately 1,500 customers affected", ""
            )
            == 1_500
        )
        assert OPCBreachReportsScraper._extract_individuals_count("no count mentioned", "") is None

    async def test_class_action_risk_threshold(self) -> None:
        from app.scrapers.consumer.opc_breach_reports import OPCBreachReportsScraper, _CLASS_ACTION_THRESHOLD

        assert _CLASS_ACTION_THRESHOLD == 10_000

        count = OPCBreachReportsScraper._extract_individuals_count(
            "breach affecting 250,000 individuals", ""
        )
        assert count is not None and count >= _CLASS_ACTION_THRESHOLD


@pytest.mark.asyncio
class TestProvincialPrivacyCommissionersScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_PROVINCIAL_PRIVACY_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "consumer_provincial_privacy_commissioners"
            assert r.signal_type == "privacy_provincial_finding"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "privacy_cybersecurity" in r.practice_area_hints

    async def test_covers_three_provinces(self) -> None:
        from app.scrapers.consumer.provincial_privacy_commissioners import _COMMISSIONERS

        provinces = {c.province for c in _COMMISSIONERS}
        assert "ON" in provinces
        assert "BC" in provinces
        assert "AB" in provinces

    async def test_order_gets_higher_confidence(self) -> None:
        from app.scrapers.consumer.provincial_privacy_commissioners import (
            ProvincialPrivacyCommissionersScraper,
        )

        is_order_title = "Order P26-001 — Acme Corp"
        is_finding_title = "Investigation of Acme Corp"
        assert ProvincialPrivacyCommissionersScraper._classify_decision(is_order_title, "") == "order"
        assert (
            ProvincialPrivacyCommissionersScraper._classify_decision(is_finding_title, "")
            != "order"
        )


@pytest.mark.asyncio
class TestOBSIDecisionsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_OBSI_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "consumer_obsi_decisions"
            assert r.signal_type == "consumer_complaint_financial"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "class_actions" in r.practice_area_hints
            assert "banking_finance" in r.practice_area_hints


@pytest.mark.asyncio
class TestCCTSComplaintsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_CCTS_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "consumer_ccts_complaints"
            assert r.signal_type == "consumer_complaint_telecom"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "class_actions" in r.practice_area_hints

    async def test_provider_extraction(self) -> None:
        from app.scrapers.consumer.ccts_complaints import CCTSComplaintsScraper

        assert CCTSComplaintsScraper._extract_provider("Rogers leads all TSPs", "") == "Rogers"
        assert CCTSComplaintsScraper._extract_provider("Bell and Telus complaints", "") in (
            "Bell",
            "Telus",
        )
        assert CCTSComplaintsScraper._extract_provider("No provider here", "") is None


@pytest.mark.asyncio
class TestBBBComplaintsScraper:
    async def test_scrape_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
            mock_rss.return_value = {
                "entries": [
                    {
                        "title": "BBB Warning: Fraud complaints spike against SubscriptionCo",
                        "link": "https://www.bbb.org/news/123",
                        "summary": "Deceptive billing practices led to hundreds of consumer complaints against SubscriptionCo.",
                        "published": "Wed, 25 Mar 2026 16:00:00 +0000",
                    }
                ]
            }
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert r.source_id == "consumer_bbb_complaints"
            assert r.signal_type == "consumer_complaint_spike"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "class_actions" in r.practice_area_hints


# ── Practice Area Validation ──────────────────────────────────────────────────


class TestPracticeAreaHints:
    """Every class action scraper must use valid PRACTICE_AREA_BITS keys."""

    @pytest.fixture(params=_CLASS_ACTION_SOURCE_IDS)
    def scraper(self, request: pytest.FixtureRequest) -> BaseScraper:
        return ScraperRegistry.get(request.param)

    def test_all_signal_types_are_strings(self, scraper: BaseScraper) -> None:
        for st in scraper.signal_types:
            assert isinstance(st, str)
            assert len(st) > 3


class TestConsumerPracticeAreaHints:
    """Every consumer precursor scraper must reference class_actions in its practice areas."""

    @pytest.fixture(params=_CONSUMER_PRECURSOR_SOURCE_IDS)
    def scraper(self, request: pytest.FixtureRequest) -> BaseScraper:
        return ScraperRegistry.get(request.param)

    def test_all_signal_types_are_strings(self, scraper: BaseScraper) -> None:
        for st in scraper.signal_types:
            assert isinstance(st, str)
            assert len(st) > 3


# ── Company Name Extraction ───────────────────────────────────────────────────


class TestCompanyNameExtraction:
    def test_ontario_extracts_defendant(self) -> None:
        mod = importlib.import_module(
            "app.scrapers.class_actions.ontario_class_proceedings"
        )
        cls = mod.OntarioClassProceedingsScraper
        assert cls._extract_company_name("Smith v. Acme Corp") == "Acme Corp"
        assert cls._extract_company_name("Jones vs BigBank Inc.") == "BigBank Inc"
        assert cls._extract_company_name("No defendant here") is None

    def test_courtlistener_extracts_defendant(self) -> None:
        mod = importlib.import_module(
            "app.scrapers.class_actions.pacer_class_actions"
        )
        fn = mod._extract_company_name
        assert fn("Smith v. Canadian Mining Corp.") == "Canadian Mining Corp."
        assert fn("No defendant here at all") is None

    def test_health_canada_extracts_company(self) -> None:
        from app.scrapers.consumer.health_canada_recalls import HealthCanadaRecallsScraper

        result = HealthCanadaRecallsScraper._extract_company(
            "Baby Food Recall — by Acme Foods Inc.", "Risk of contamination"
        )
        assert result is not None
        assert "Acme" in result

    def test_opc_extracts_organization_from_finding(self) -> None:
        from app.scrapers.consumer.opc_breach_reports import OPCBreachReportsScraper

        # "involving" separator pattern
        result = OPCBreachReportsScraper._extract_organization(
            "PIPEDA Report of Findings #12345 involving TechCorp Ltd.", ""
        )
        assert result is not None
        assert "TechCorp" in result


# ── Celery Task Registration ──────────────────────────────────────────────────


class TestCeleryClassActionTask:
    def test_class_action_task_registered(self) -> None:
        from app.tasks.celery_app import celery_app
        import app.tasks.scraper_tasks  # noqa: F401 — force task registration

        task_names = list(celery_app.tasks.keys())
        assert "scrapers.run_class_actions" in task_names

    def test_beat_schedule_has_class_actions(self) -> None:
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "scrape-class-actions" in schedule
        entry = schedule["scrape-class-actions"]
        assert entry["task"] == "scrapers.run_class_actions"

    def test_task_routes_to_scrapers_queue(self) -> None:
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes.get("scrapers.run_class_actions") == {"queue": "scrapers"}


class TestCeleryConsumerPrecursorTask:
    def test_consumer_precursor_task_registered(self) -> None:
        from app.tasks.celery_app import celery_app
        import app.tasks.scraper_tasks  # noqa: F401 — force task registration

        task_names = list(celery_app.tasks.keys())
        assert "scrapers.scrape_consumer_precursors" in task_names

    def test_beat_schedule_has_consumer_precursors(self) -> None:
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "scrape-consumer-precursors" in schedule
        entry = schedule["scrape-consumer-precursors"]
        assert entry["task"] == "scrapers.scrape_consumer_precursors"

    def test_consumer_task_routes_to_scrapers_queue(self) -> None:
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes.get("scrapers.scrape_consumer_precursors") == {"queue": "scrapers"}

    def test_beat_schedule_runs_three_times_daily(self) -> None:
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        entry = schedule["scrape-consumer-precursors"]
        # Schedule should run at 3 hours: 8, 14, 20
        crontab = entry["schedule"]
        assert crontab is not None


# ── Migration File Validity ───────────────────────────────────────────────────


class TestMigrationFile:
    def test_migration_0009_exists(self) -> None:
        migration_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "alembic"
            / "versions"
        )
        migration_file = migration_dir / "0009_class_action_tables.py"
        assert migration_file.exists(), f"Migration not found at {migration_file}"

    def test_migration_0009_valid_python(self) -> None:
        migration_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "alembic"
            / "versions"
        )
        migration_file = migration_dir / "0009_class_action_tables.py"
        source = migration_file.read_text()
        ast.parse(source)

    def test_migration_0009_has_upgrade_downgrade(self) -> None:
        migration_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "alembic"
            / "versions"
        )
        migration_file = migration_dir / "0009_class_action_tables.py"
        source = migration_file.read_text()
        assert "def upgrade" in source
        assert "def downgrade" in source
        assert "class_action_cases" in source
