"""
tests/scrapers/test_phase_s3_geo.py — Phase S3 geo intelligence scrapers test suite.

Tests:
  1. Municipal permits: Toronto CKAN API returns results, filters < $1M permits
  2. Municipal permits: returns [] on API failure
  3. Municipal permits: demolition permit classified correctly
  4. OpenSky scraper instantiates with correct source_id
  5. OpenSky: parse_flight returns ScraperResult
  6. Dark web scraper skips without API key
  7. Dark web scraper parses HIBP breach correctly
  8. Lobbyist registry: parses RSS items
  9. Lobbyist registry: practice area matching
  10. WSIB: classifies penalty keywords
  11. Labour relations: parses CIRB decision
  12. CRA liens: documented stub with enforcement filter
  13. CBSA trade: identifies trade remedy keywords
  14. DBRS: classifies downgrade vs negative outlook
  15. DBRS: extracts company name from headline
  16. All 8+ geo scrapers registered in ScraperRegistry

Mocks all external HTTP calls — no real network traffic in tests.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _mock_settings(**overrides):
    """Return a mock Settings object with geo API keys."""
    defaults = {
        "hibp_api_key": "test_hibp_key",
        "opensky_username": "",
        "opensky_password": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_response(status_code: int = 200, json_data=None, text: str = ""):
    """Return a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


# ── 1. Municipal Permits: Toronto CKAN API returns results ──────────────────


@pytest.mark.asyncio
async def test_municipal_permits_toronto_returns_results():
    """Toronto CKAN API should return results for permits > $1M."""
    from app.scrapers.geo.municipal_permits import MunicipalPermitsScraper

    scraper = MunicipalPermitsScraper()

    ckan_response = {
        "success": True,
        "result": {
            "records": [
                {
                    "ESTIMATED_CONST_COST": "15000000",
                    "APPLICANT": "Acme Construction Ltd",
                    "OWNER": "Big Corp Inc",
                    "PERMIT_TYPE": "New Building",
                    "STATUS": "Issued",
                    "ISSUED_DATE": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
                    "STREET_NAME": "123 Bay St",
                },
                {
                    "ESTIMATED_CONST_COST": "500000",
                    "APPLICANT": "Small Reno Co",
                    "PERMIT_TYPE": "Alteration",
                    "STATUS": "Issued",
                    "ISSUED_DATE": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
                },
            ]
        },
    }

    scraper.get_json = AsyncMock(return_value=ckan_response)
    scraper._rate_limit_sleep = AsyncMock()

    results = await scraper._scrape_toronto()

    # Only the $15M permit should pass the $1M filter
    assert len(results) == 1
    assert results[0].signal_type == "geo_permit_major_construction"
    assert results[0].raw_company_name == "Acme Construction Ltd"
    assert results[0].confidence_score == 0.6


# ── 2. Municipal Permits: returns [] on API failure ──────────────────────────


@pytest.mark.asyncio
async def test_municipal_permits_returns_empty_on_api_failure():
    """Municipal permits should return [] when API returns None."""
    from app.scrapers.geo.municipal_permits import MunicipalPermitsScraper

    scraper = MunicipalPermitsScraper()
    scraper.get_json = AsyncMock(return_value=None)
    scraper._rate_limit_sleep = AsyncMock()

    results = await scraper._scrape_toronto()
    assert results == []


# ── 3. Municipal Permits: demolition classified correctly ────────────────────


@pytest.mark.asyncio
async def test_municipal_permits_demolition_signal():
    """Demolition permits should be classified as geo_permit_demolition."""
    from app.scrapers.geo.municipal_permits import MunicipalPermitsScraper

    scraper = MunicipalPermitsScraper()

    ckan_response = {
        "success": True,
        "result": {
            "records": [
                {
                    "ESTIMATED_CONST_COST": "2000000",
                    "APPLICANT": "Demo Corp",
                    "PERMIT_TYPE": "Demolition",
                    "STATUS": "Issued",
                    "ISSUED_DATE": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
                },
            ]
        },
    }

    scraper.get_json = AsyncMock(return_value=ckan_response)
    scraper._rate_limit_sleep = AsyncMock()

    results = await scraper._scrape_toronto()
    assert len(results) == 1
    assert results[0].signal_type == "geo_permit_demolition"


# ── 4. OpenSky scraper instantiates ──────────────────────────────────────────


def test_opensky_scraper_instantiates():
    """OpenSky scraper should instantiate with correct attributes."""
    from app.scrapers.geo.opensky import OpenSkyScraper

    scraper = OpenSkyScraper()
    assert scraper.source_id == "geo_opensky"
    assert scraper.CATEGORY == "geo"
    assert "geo_flight_corporate_jet" in scraper.signal_types


# ── 5. OpenSky: parse_flight returns ScraperResult ───────────────────────────


def test_opensky_parse_flight():
    """OpenSky _parse_flight should return a valid ScraperResult."""
    from app.scrapers.geo.opensky import OpenSkyScraper

    scraper = OpenSkyScraper()
    flight = {
        "callsign": "GLF500  ",
        "icao24": "abc123",
        "estDepartureAirport": "KJFK",
        "lastSeen": int(datetime.now(tz=UTC).timestamp()),
    }

    result = scraper._parse_flight(flight, "CYYZ", "Toronto Pearson")
    assert result is not None
    assert result.signal_type == "geo_flight_corporate_jet"
    assert result.signal_value["destination_airport"] == "CYYZ"
    assert result.signal_value["is_bizjet_callsign"] is True
    assert result.confidence_score == 0.7


# ── 6. Dark web scraper skips without API key ────────────────────────────────


@pytest.mark.asyncio
async def test_dark_web_scraper_skips_without_api_key():
    """Dark web scraper should return [] when no HIBP API key is set."""
    from app.scrapers.geo.dark_web import DarkWebBreachScraper

    scraper = DarkWebBreachScraper()

    with patch(
        "app.scrapers.geo.dark_web.get_settings",
        return_value=_mock_settings(hibp_api_key=""),
    ):
        results = await scraper.scrape()

    assert results == []


# ── 7. Dark web scraper parses HIBP breach ───────────────────────────────────


@pytest.mark.asyncio
async def test_dark_web_scraper_parses_hibp_breach():
    """Dark web scraper should parse HIBP breach data correctly."""
    from app.scrapers.geo.dark_web import DarkWebBreachScraper

    scraper = DarkWebBreachScraper()

    breaches = [
        {
            "Name": "ExampleCorp",
            "Domain": "examplecorp.ca",
            "BreachDate": "2026-03-15",
            "AddedDate": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "PwnCount": 500000,
            "DataClasses": ["Email addresses", "Passwords"],
            "IsVerified": True,
            "IsSensitive": False,
        },
        {
            "Name": "OldBreach",
            "Domain": "old.com",
            "BreachDate": "2020-01-01",
            "AddedDate": "2020-01-15T00:00:00Z",
            "PwnCount": 100,
            "DataClasses": ["Email addresses"],
            "IsVerified": True,
            "IsSensitive": False,
        },
    ]

    mock_resp = _mock_response(200, json_data=breaches)
    scraper.get = AsyncMock(return_value=mock_resp)

    with patch(
        "app.scrapers.geo.dark_web.get_settings",
        return_value=_mock_settings(hibp_api_key="test_key"),
    ):
        results = await scraper.scrape()

    # Only the recent breach should be included (OldBreach is > 30 days ago)
    assert len(results) == 1
    assert results[0].raw_company_name == "ExampleCorp"
    assert results[0].signal_type == "geo_data_breach"
    assert "privacy" in results[0].practice_area_hints


# ── 8. Lobbyist registry: parses RSS items ──────────────────────────────────


@pytest.mark.asyncio
async def test_lobbyist_registry_parses_rss():
    """Lobbyist registry should parse RSS feed items."""
    from app.scrapers.geo.lobbyist_registry import LobbyistRegistryScraper

    scraper = LobbyistRegistryScraper()

    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Lobbying Registry</title>
        <item>
          <title>Big Bank Corp - New Registration - Financial Regulations</title>
          <link>https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/cmmns?lang=eng</link>
          <description>New lobbyist registration for financial regulation advocacy</description>
          <pubDate>Mon, 25 Mar 2026 12:00:00 GMT</pubDate>
        </item>
        <item>
          <title>Energy Co - Renewal - Environment and Energy Policy</title>
          <link>https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/cmmns?lang=eng</link>
          <description>Lobbying activity on energy and environmental policy</description>
          <pubDate>Tue, 26 Mar 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>"""

    mock_resp = _mock_response(200, text=rss_xml)
    mock_resp.text = rss_xml
    scraper.get = AsyncMock(return_value=mock_resp)

    results = await scraper.scrape()

    assert len(results) == 2
    assert results[0].source_id == "geo_lobbyist"
    assert results[0].raw_company_name == "Big Bank Corp"
    assert results[0].signal_type == "geo_lobbyist_registration"


# ── 9. Lobbyist registry: practice area matching ────────────────────────────


def test_lobbyist_practice_area_matching():
    """Lobbyist scraper should match subject keywords to practice areas."""
    from app.scrapers.geo.lobbyist_registry import LobbyistRegistryScraper

    areas = LobbyistRegistryScraper._match_practice_areas(
        "Discussion about financial regulation and taxation policy"
    )
    assert "banking_finance" in areas
    assert "tax" in areas


# ── 10. WSIB: classifies penalty keywords ────────────────────────────────────


def test_wsib_classify_signal():
    """WSIB scraper should classify penalty vs compliance keywords."""
    from app.scrapers.geo.wsib import WsibScraper

    assert WsibScraper._classify_signal("company fined for violation") == "geo_wsib_penalty"
    assert (
        WsibScraper._classify_signal("compliance order issued after inspection")
        == "geo_wsib_compliance_order"
    )
    assert WsibScraper._classify_signal("general news update") is None


# ── 11. Labour relations: parses CIRB decision ──────────────────────────────


def test_labour_relations_parse_decision():
    """Labour relations scraper should parse CIRB decision titles."""
    from app.scrapers.geo.labour_relations import LabourRelationsScraper

    scraper = LabourRelationsScraper()

    result = scraper._parse_decision(
        "Teamsters v. National Railways - Certification Application",
        "https://cirb-ccri.gc.ca/en/decisions/123",
    )
    assert result is not None
    assert result.signal_type == "geo_union_certification"
    assert result.raw_company_name == "National Railways"


# ── 12. CRA liens: documented stub with enforcement filter ──────────────────


def test_cra_liens_is_documented():
    """CRA liens scraper should have documentation about PPSA requirement."""
    from app.scrapers.geo.cra_liens import CraTaxLienScraper

    scraper = CraTaxLienScraper()
    assert scraper.source_id == "geo_cra_liens"
    assert "PPSA" in CraTaxLienScraper.__doc__ or "Teranet" in CraTaxLienScraper.__doc__


def test_cra_liens_parse_news_filters_irrelevant():
    """CRA liens scraper should filter out non-enforcement news."""
    from app.scrapers.geo.cra_liens import CraTaxLienScraper

    scraper = CraTaxLienScraper()

    # Enforcement item should be included
    result = scraper._parse_news_item(
        "Ontario resident convicted of tax evasion",
        "https://www.canada.ca/en/revenue-agency/news/2026/03/example.html",
    )
    assert result is not None
    assert result.signal_type == "geo_cra_tax_lien"

    # Non-enforcement item should be filtered out
    result = scraper._parse_news_item(
        "CRA announces new tax filing deadline",
        "https://www.canada.ca/en/revenue-agency/news/2026/03/deadline.html",
    )
    assert result is None


# ── 13. CBSA trade: identifies trade remedy keywords ─────────────────────────


def test_cbsa_trade_instantiates():
    """CBSA trade scraper should instantiate with correct attributes."""
    from app.scrapers.geo.cbsa_trade import CbsaTradeScraper

    scraper = CbsaTradeScraper()
    assert scraper.source_id == "geo_cbsa"
    assert "geo_trade_remedy" in scraper.signal_types
    assert scraper.CATEGORY == "geo"


# ── 14. DBRS: classifies downgrade vs negative outlook ──────────────────────


def test_dbrs_parse_downgrade():
    """DBRS scraper should classify downgrade headlines correctly."""
    from app.scrapers.geo.dbrs import DbrsScraper

    scraper = DbrsScraper()

    result = scraper._parse_rating_action(
        "DBRS Morningstar Downgrades Acme Corp to BBB (low)",
        "https://dbrs.morningstar.com/research/123",
    )
    assert result is not None
    assert result.signal_type == "geo_credit_downgrade"
    assert result.confidence_score == 0.8


def test_dbrs_parse_negative_outlook():
    """DBRS scraper should classify negative outlook headlines."""
    from app.scrapers.geo.dbrs import DbrsScraper

    scraper = DbrsScraper()

    result = scraper._parse_rating_action(
        "DBRS Morningstar Places Big Bank Under Review with Negative Outlook",
        "https://dbrs.morningstar.com/research/456",
    )
    assert result is not None
    assert result.signal_type == "geo_credit_outlook_negative"


def test_dbrs_skips_positive_actions():
    """DBRS scraper should skip positive/neutral rating actions."""
    from app.scrapers.geo.dbrs import DbrsScraper

    scraper = DbrsScraper()

    result = scraper._parse_rating_action(
        "DBRS Morningstar Confirms AAA Rating for Stable Corp",
        "https://dbrs.morningstar.com/research/789",
    )
    assert result is None


# ── 15. DBRS: extracts company name from headline ───────────────────────────


def test_dbrs_extract_company():
    """DBRS scraper should extract company name from standard headlines."""
    from app.scrapers.geo.dbrs import DbrsScraper

    name = DbrsScraper._extract_company(
        "DBRS Morningstar Downgrades Acme Corp to BB"
    )
    assert name == "Acme Corp"


# ── 16. All geo scrapers registered ─────────────────────────────────────────


def test_all_geo_scrapers_registered():
    """All 8 Phase S3 geo scrapers must be registered in ScraperRegistry."""
    from app.scrapers.registry import ScraperRegistry

    all_ids = ScraperRegistry.all_ids()
    required = [
        "geo_municipal",
        "geo_opensky",
        "geo_lobbyist",
        "geo_wsib",
        "geo_labour",
        "geo_darkweb",
        "geo_cbsa",
        "geo_dbrs",
    ]
    for sid in required:
        assert sid in all_ids, f"Missing geo scraper: {sid}"


def test_geo_scrapers_have_correct_category():
    """All Phase S3 geo scrapers must have CATEGORY = 'geo'."""
    from app.scrapers.registry import ScraperRegistry

    geo_scrapers = ScraperRegistry.by_category("geo")
    geo_ids = [s.source_id for s in geo_scrapers]
    for sid in [
        "geo_municipal",
        "geo_opensky",
        "geo_lobbyist",
        "geo_wsib",
        "geo_labour",
        "geo_darkweb",
        "geo_cbsa",
        "geo_dbrs",
    ]:
        assert sid in geo_ids, f"Scraper {sid} missing CATEGORY='geo'"


# ── Extra: Vancouver permits parsing ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_municipal_permits_vancouver_returns_results():
    """Vancouver Open Data API should return results for permits > $1M."""
    from app.scrapers.geo.municipal_permits import MunicipalPermitsScraper

    scraper = MunicipalPermitsScraper()

    van_response = {
        "results": [
            {
                "projectvalue": 5000000,
                "applicant": "West Coast Builders",
                "typeofwork": "New Building",
                "address": "456 Granville St",
                "issuedate": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
                "permitcategory": "Commercial",
            },
            {
                "projectvalue": 200000,
                "applicant": "Small Job Co",
                "typeofwork": "Alteration",
                "issuedate": datetime.now(tz=UTC).strftime("%Y-%m-%d"),
            },
        ]
    }

    scraper.get_json = AsyncMock(return_value=van_response)

    results = await scraper._scrape_vancouver()

    # Only $5M permit should pass (the $200k one filtered out)
    assert len(results) == 1
    assert results[0].signal_value["city"] == "Vancouver"
    assert results[0].raw_company_name == "West Coast Builders"
