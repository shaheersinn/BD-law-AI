"""Tests for Phase CA-2 consumer precursor scrapers.

Covers per-scraper:
  - returns_results: mock HTTP → list[ScraperResult] with valid structure
  - handles_empty_response: 404/empty → returns []
  - handles_timeout: TimeoutException → returns []
  - health_check: bool return value

All HTTP calls are mocked — no real network traffic.
"""

from __future__ import annotations

import os
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
from app.scrapers.base import ScraperResult  # noqa: E402
from app.scrapers.registry import ScraperRegistry  # noqa: E402

_VALID_PA_KEYS = set(PRACTICE_AREA_BITS.keys())


# ── Mock helpers ──────────────────────────────────────────────────────────────


def _mock_resp(text: str = "", status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

_HEALTH_CANADA_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Health Canada Recalls</title>
    <item>
      <title>Recall: Acme Baby Food — Listeria Risk — by Acme Foods Inc.</title>
      <link>https://recalls-rappels.canada.ca/en/alert-recall/100</link>
      <pubDate>Sat, 28 Mar 2026 12:00:00 +0000</pubDate>
      <description>Acme Foods Inc. is recalling baby food due to Listeria risk.</description>
      <category>Food</category>
    </item>
  </channel>
</rss>"""

_TRANSPORT_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Transport Canada Recalls</title>
    <item>
      <title>Safety Recall — AutoMaker Inc. — Airbag Defect</title>
      <link>https://tc.canada.ca/recall/123</link>
      <pubDate>Mon, 24 Mar 2026 09:00:00 +0000</pubDate>
      <description>AutoMaker Inc. is recalling vehicles due to faulty airbag inflators.</description>
    </item>
  </channel>
</rss>"""

_CPSC_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>CPSC Recalls</title>
    <item>
      <title>CanadaCo Inc. Recalls Scooters Due to Fire Hazard</title>
      <link>https://www.cpsc.gov/Recalls/2026/example</link>
      <pubDate>Mon, 23 Mar 2026 14:00:00 +0000</pubDate>
      <description>CanadaCo Inc., of Toronto, Canada, recalls scooters. Battery overheats.</description>
    </item>
  </channel>
</rss>"""

_BBB_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BBB News</title>
    <item>
      <title>BBB Warning: Fraud complaints surge against SubscriptionCo — 500% increase</title>
      <link>https://www.bbb.org/news/2026/subscriptionco</link>
      <pubDate>Wed, 25 Mar 2026 16:00:00 +0000</pubDate>
      <summary>BBB received hundreds of complaints against SubscriptionCo Inc.</summary>
    </item>
  </channel>
</rss>"""

_OBSI_HTML = """<html><body>
<article>
  <h3><a href="/en/decisions/2026-1">OBSI Decision: TD Bank — Refused Recommendation</a></h3>
  <p>TD Bank declined to follow OBSI's recommendation. $12,500 awarded.</p>
  <time class="date" datetime="2026-03-20">March 20, 2026</time>
</article>
</body></html>"""

_CCTS_HTML = """<html><body>
<article class="news-item">
  <h3><a href="/news/2025-annual-report">
    CCTS Annual Report: Rogers leads complaint volume with 31% increase
  </a></h3>
  <time class="date">March 1, 2026</time>
  <p>Rogers accounted for the highest complaint volume among all telecom providers.</p>
</article>
</body></html>"""

_OPC_HTML = """<html><body>
<ul>
  <li>
    <h3><a href="/en/opc-actions-and-decisions/pipeda-findings/2026/012345">
      PIPEDA Report of Findings #12345 — Investigation into TechCorp Ltd.
    </a></h3>
    <p>TechCorp Ltd. experienced a breach affecting 250,000 individuals.</p>
    <time datetime="2026-03-15">March 15, 2026</time>
  </li>
</ul>
</body></html>"""

_PROVINCIAL_HTML = """<html><body>
<ul>
  <li>
    <h3><a href="/decisions/order-p26-001">
      Order P26-001 — Acme Insurance Corp — Privacy Breach Investigation
    </a></h3>
    <p>Commissioner ordered Acme Insurance Corp to improve security practices.</p>
    <time datetime="2026-03-10">March 10, 2026</time>
  </li>
</ul>
</body></html>"""


# ── Health Canada Recalls ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHealthCanadaRecallsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text=_HEALTH_CANADA_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_health_canada_recalls"
            assert r.signal_type == "recall_health_canada"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            assert "class_actions" in r.practice_area_hints
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS, f"Invalid practice_area_hint: {hint}"

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(status=404)
            results = await scraper.scrape()
        assert results == []

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<rss/>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_health_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("connection refused")
            result = await scraper.health_check()
        assert result is False


# ── Transport Canada Recalls ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTransportCanadaRecallsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text=_TRANSPORT_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_transport_canada_recalls"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(status=404)
            results = await scraper.scrape()
        assert results == []

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<html>OK</html>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_transport_canada_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("network error")
            result = await scraper.health_check()
        assert result is False


# ── CPSC Recalls ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCPSCRecallsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text=_CPSC_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_cpsc_recalls"
            assert r.signal_type == "recall_cpsc_us"
            assert 0.0 <= r.confidence_score <= 1.0
            assert "product_liability" in r.practice_area_hints
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(status=503)
            results = await scraper.scrape()
        assert results == []

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<rss/>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_cpsc_recalls")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("timeout")
            result = await scraper.health_check()
        assert result is False


# ── BBB Complaints ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBBBComplaintsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text=_BBB_RSS)
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_bbb_complaints"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(status=404)
            results = await scraper.scrape()
        assert results == []

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<rss/>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_bbb_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("unreachable")
            result = await scraper.health_check()
        assert result is False


# ── OBSI Decisions ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestOBSIDecisionsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_OBSI_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_obsi_decisions"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup("<html><body></body></html>", "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            mock_soup.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<html>OK</html>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_obsi_decisions")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("down")
            result = await scraper.health_check()
        assert result is False


# ── CCTS Complaints ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestCCTSComplaintsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_CCTS_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_ccts_complaints"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup("<html><body></body></html>", "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            mock_soup.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<html>OK</html>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_ccts_complaints")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("down")
            result = await scraper.health_check()
        assert result is False


# ── OPC Breach Reports ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestOPCBreachReportsScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_OPC_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_opc_breach_reports"
            assert r.signal_type in ("privacy_enforcement", "privacy_breach_report")
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            assert "privacy_cybersecurity" in r.practice_area_hints
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup("<html><body><ul></ul></body></html>", "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            mock_soup.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<html>OK</html>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_opc_breach_reports")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("down")
            result = await scraper.health_check()
        assert result is False


# ── Provincial Privacy Commissioners ─────────────────────────────────────────


@pytest.mark.asyncio
class TestProvincialPrivacyCommissionersScraper:
    async def test_returns_results(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup(_PROVINCIAL_HTML, "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ScraperResult)
            assert r.source_id == "consumer_provincial_privacy_commissioners"
            assert r.signal_type == "privacy_provincial_finding"
            assert r.source_url or r.raw_company_name
            assert 0.0 <= r.confidence_score <= 1.0
            assert "privacy_cybersecurity" in r.practice_area_hints
            for hint in r.practice_area_hints:
                assert hint in _VALID_PA_KEYS

    async def test_handles_empty_response(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            from bs4 import BeautifulSoup

            mock_soup.return_value = BeautifulSoup("<html><body><ul></ul></body></html>", "html.parser")
            results = await scraper.scrape()
        assert isinstance(results, list)

    async def test_handles_timeout(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get_soup", new_callable=AsyncMock) as mock_soup:
            mock_soup.side_effect = httpx.TimeoutException("timeout")
            results = await scraper.scrape()
        assert isinstance(results, list)
        assert results == []

    async def test_health_check_success(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _mock_resp(text="<html>OK</html>")
            result = await scraper.health_check()
        assert isinstance(result, bool)
        assert result is True

    async def test_health_check_failure(self) -> None:
        scraper = ScraperRegistry.get("consumer_provincial_privacy_commissioners")
        with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("timeout")
            result = await scraper.health_check()
        assert result is False
