"""
tests/scrapers/test_phase_s1_regulatory.py — Phase S1 regulatory scraper tests.

All tests mock HTTP — never make real requests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.scrapers.base import ScraperResult

# ── Sample HTML fixtures ────────────────────────────────────────────────────────

_ENFORCEMENT_HTML = """
<html><body>
<article>
  <h3><a href="/en/enforcement/case-123">In the Matter of Acme Corp</a></h3>
  <span class="date">2026-03-01</span>
</article>
<article>
  <h3><a href="/en/enforcement/case-456">Settlement with XYZ Inc.</a></h3>
  <time datetime="2026-02-15">February 15, 2026</time>
</article>
<article>
  <h3><a href="/en/enforcement/case-789">Ordonnance temporaire des entreprises du Québec</a></h3>
  <span class="date">2026-02-10</span>
</article>
</body></html>
"""

_TABLE_HTML = """
<html><body>
<table><tbody>
<tr>
  <td><a href="/enforcement/abc">Big Bank Ltd</a></td>
  <td>Administrative penalty</td>
  <td>March 5, 2026</td>
</tr>
<tr>
  <td><a href="/enforcement/def">Finance Co</a></td>
  <td>Cease trade order</td>
  <td>February 20, 2026</td>
</tr>
</tbody></table>
</body></html>
"""

_DOJ_RSS = {
    "entries": [
        {
            "title": "DOJ Charges Canadian Company for Fraud",
            "description": "A Toronto-based company was charged with securities fraud.",
            "link": "https://www.justice.gov/news/123",
            "published": "2026-03-10",
        },
        {
            "title": "US Domestic Case With No Foreign Connection",
            "description": "A domestic US matter unrelated to any other jurisdiction.",
            "link": "https://www.justice.gov/news/456",
            "published": "2026-03-08",
        },
    ]
}

_SEC_RSS = {
    "entries": [
        {
            "title": "SEC Action Against TSX-Listed Company",
            "description": "Enforcement release involving a TSX-listed entity.",
            "link": "https://www.sec.gov/litigation/admin/release-123",
            "published": "2026-03-12",
        },
        {
            "title": "Domestic US Accounting Release",
            "description": "Purely domestic US matter.",
            "link": "https://www.sec.gov/litigation/admin/release-456",
            "published": "2026-03-11",
        },
    ]
}

_EMPTY_HTML = "<html><body><div>No enforcement actions found</div></body></html>"


def _mock_response(text: str, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )


# ── OSC Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_osc_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.osc import OSCScraper

    scraper = OSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(isinstance(r, ScraperResult) for r in results)
    assert all(r.source_id == "regulatory_osc" for r in results)
    assert all(r.practice_area_hints for r in results)
    assert all(r.signal_text for r in results)


@pytest.mark.asyncio
async def test_osc_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.osc import OSCScraper

    scraper = OSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


@pytest.mark.asyncio
async def test_osc_scraper_skips_french_records():
    from app.scrapers.regulatory.osc import OSCScraper

    scraper = OSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    titles = [r.signal_text for r in results]
    assert not any("Québec" in t for t in titles)


@pytest.mark.asyncio
async def test_osc_extracts_respondent_name():
    from app.scrapers.regulatory.osc import OSCScraper

    scraper = OSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    company_names = [r.raw_company_name for r in results if r.raw_company_name]
    assert "Acme Corp" in company_names


# ── OSFI Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_osfi_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.osfi_enforcement import OSFIEnforcementScraper

    scraper = OSFIEnforcementScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_osfi_enforcement" for r in results)
    assert all("banking_finance" in r.practice_area_hints for r in results)


@pytest.mark.asyncio
async def test_osfi_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.osfi_enforcement import OSFIEnforcementScraper

    scraper = OSFIEnforcementScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=503)
        results = await scraper.scrape()

    assert results == []


# ── BCSC Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcsc_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.bcsc import BCSCScraper

    scraper = BCSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_bcsc" for r in results)
    assert all("securities" in r.practice_area_hints for r in results)


@pytest.mark.asyncio
async def test_bcsc_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.bcsc import BCSCScraper

    scraper = BCSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=404)
        results = await scraper.scrape()

    assert results == []


# ── ASC Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_asc_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.asc import ASCScraper

    scraper = ASCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_asc" for r in results)


@pytest.mark.asyncio
async def test_asc_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.asc import ASCScraper

    scraper = ASCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


# ── FSRA Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fsra_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.fsra import FSRAScraper

    scraper = FSRAScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_fsra" for r in results)
    assert all("insurance" in r.practice_area_hints for r in results)


@pytest.mark.asyncio
async def test_fsra_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.fsra import FSRAScraper

    scraper = FSRAScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


# ── CRTC Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crtc_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.crtc import CRTCScraper

    scraper = CRTCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_crtc" for r in results)
    assert all("regulatory" in r.practice_area_hints for r in results)


@pytest.mark.asyncio
async def test_crtc_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.crtc import CRTCScraper

    scraper = CRTCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


@pytest.mark.asyncio
async def test_crtc_scraper_skips_french_records():
    from app.scrapers.regulatory.crtc import CRTCScraper

    scraper = CRTCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    titles = [r.signal_text for r in results]
    assert not any("Québec" in t for t in titles)


# ── OPC Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opc_scraper_returns_results_on_valid_html():
    from app.scrapers.regulatory.opc import OPCScraper

    scraper = OPCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert all(r.source_id == "regulatory_opc" for r in results)
    assert all("privacy_data" in r.practice_area_hints for r in results)


@pytest.mark.asyncio
async def test_opc_scraper_returns_empty_on_fetch_failure():
    from app.scrapers.regulatory.opc import OPCScraper

    scraper = OPCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


@pytest.mark.asyncio
async def test_opc_scraper_skips_french_records():
    from app.scrapers.regulatory.opc import OPCScraper

    scraper = OPCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    titles = [r.signal_text for r in results]
    assert not any("Québec" in t for t in titles)


# ── US DOJ Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_doj_scraper_returns_results_on_valid_rss():
    from app.scrapers.regulatory.us_doj import USDOJScraper

    scraper = USDOJScraper()
    with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = _DOJ_RSS
        results = await scraper.scrape()

    assert len(results) == 1
    assert results[0].source_id == "regulatory_us_doj"
    assert "litigation" in results[0].practice_area_hints
    assert "Canadian" in results[0].signal_text or "DOJ" in results[0].signal_text


@pytest.mark.asyncio
async def test_doj_scraper_filters_non_canadian():
    from app.scrapers.regulatory.us_doj import USDOJScraper

    scraper = USDOJScraper()
    with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = _DOJ_RSS
        results = await scraper.scrape()

    titles = [r.signal_text for r in results]
    assert not any("Domestic" in t for t in titles)


@pytest.mark.asyncio
async def test_doj_scraper_returns_empty_on_rss_failure():
    from app.scrapers.regulatory.us_doj import USDOJScraper

    scraper = USDOJScraper()
    with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = {}
        results = await scraper.scrape()

    assert results == []


# ── SEC AAER Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sec_aaer_scraper_returns_results_on_valid_rss():
    from app.scrapers.regulatory.sec_aaer import SECAAERScraper

    scraper = SECAAERScraper()
    with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = _SEC_RSS
        results = await scraper.scrape()

    assert len(results) == 1
    assert results[0].source_id == "regulatory_sec_aaer"
    assert "securities" in results[0].practice_area_hints


@pytest.mark.asyncio
async def test_sec_aaer_scraper_filters_non_canadian():
    from app.scrapers.regulatory.sec_aaer import SECAAERScraper

    scraper = SECAAERScraper()
    with patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss:
        mock_rss.return_value = _SEC_RSS
        results = await scraper.scrape()

    titles = [r.signal_text for r in results]
    assert not any("Domestic" in t for t in titles)


@pytest.mark.asyncio
async def test_sec_aaer_falls_back_to_html():
    from app.scrapers.regulatory.sec_aaer import SECAAERScraper

    html_with_canadian = """
    <html><body><table><tbody>
    <tr><td><a href="/lit/123">SEC Action involving TSX Company</a></td></tr>
    </tbody></table></body></html>
    """
    scraper = SECAAERScraper()
    with (
        patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss,
        patch.object(scraper, "get", new_callable=AsyncMock) as mock_get,
    ):
        mock_rss.return_value = {}
        mock_get.return_value = _mock_response(html_with_canadian)
        results = await scraper.scrape()

    assert len(results) >= 1
    assert results[0].source_id == "regulatory_sec_aaer"


@pytest.mark.asyncio
async def test_sec_aaer_returns_empty_on_total_failure():
    from app.scrapers.regulatory.sec_aaer import SECAAERScraper

    scraper = SECAAERScraper()
    with (
        patch.object(scraper, "get_rss", new_callable=AsyncMock) as mock_rss,
        patch.object(scraper, "get", new_callable=AsyncMock) as mock_get,
    ):
        mock_rss.return_value = {}
        mock_get.return_value = _mock_response("", status_code=500)
        results = await scraper.scrape()

    assert results == []


# ── Registry Tests ───────────────────────────────────────────────────────────


def test_all_regulatory_scrapers_registered():
    from app.scrapers.registry import ScraperRegistry

    all_scrapers = ScraperRegistry.all_scrapers()
    source_ids = [s.source_id for s in all_scrapers]

    required = [
        "regulatory_osc",
        "regulatory_osfi_enforcement",
        "regulatory_bcsc",
        "regulatory_asc",
        "regulatory_fsra",
        "regulatory_crtc",
        "regulatory_opc",
        "regulatory_us_doj",
        "regulatory_sec_aaer",
    ]
    for sid in required:
        assert sid in source_ids, f"Missing scraper: {sid}"


def test_all_regulatory_scrapers_have_category():
    from app.scrapers.registry import ScraperRegistry

    all_scrapers = ScraperRegistry.all_scrapers()
    regulatory = [s for s in all_scrapers if s.source_id.startswith("regulatory_")]

    for scraper in regulatory:
        assert scraper.CATEGORY == "regulatory", (
            f"{scraper.source_id} has CATEGORY={scraper.CATEGORY!r}"
        )


# ── Cross-cutting Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_scraper_raises_on_exception():
    """All 9 scrapers must return [] on exception, never raise."""
    from app.scrapers.regulatory.asc import ASCScraper
    from app.scrapers.regulatory.bcsc import BCSCScraper
    from app.scrapers.regulatory.crtc import CRTCScraper
    from app.scrapers.regulatory.fsra import FSRAScraper
    from app.scrapers.regulatory.opc import OPCScraper
    from app.scrapers.regulatory.osc import OSCScraper
    from app.scrapers.regulatory.osfi_enforcement import OSFIEnforcementScraper
    from app.scrapers.regulatory.sec_aaer import SECAAERScraper
    from app.scrapers.regulatory.us_doj import USDOJScraper

    scrapers = [
        OSCScraper(),
        OSFIEnforcementScraper(),
        BCSCScraper(),
        ASCScraper(),
        FSRAScraper(),
        CRTCScraper(),
        OPCScraper(),
        USDOJScraper(),
        SECAAERScraper(),
    ]

    for scraper in scrapers:
        with patch.object(
            scraper, "get", new_callable=AsyncMock, side_effect=Exception("network error")
        ):
            if hasattr(scraper, "get_rss"):
                with patch.object(
                    scraper,
                    "get_rss",
                    new_callable=AsyncMock,
                    side_effect=Exception("network error"),
                ):
                    results = await scraper.scrape()
            else:
                results = await scraper.scrape()
            assert results == [], f"{scraper.source_id} raised instead of returning []"


@pytest.mark.asyncio
async def test_all_results_have_required_fields():
    """Every ScraperResult must have source_id, signal_type, practice_area_hints."""
    from app.scrapers.regulatory.osc import OSCScraper

    scraper = OSCScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ENFORCEMENT_HTML)
        results = await scraper.scrape()

    for r in results:
        assert r.source_id, "source_id must not be empty"
        assert r.signal_type, "signal_type must not be empty"
        assert len(r.practice_area_hints) > 0, "practice_area_hints must not be empty"
        assert r.signal_text, "signal_text must not be empty"
        assert r.confidence_score > 0.0, "confidence_score must be positive"
