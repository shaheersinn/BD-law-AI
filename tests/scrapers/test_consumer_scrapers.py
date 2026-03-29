import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
import httpx

from app.scrapers.consumer.bbb_complaints import BbbComplaintsScraper
from app.scrapers.consumer.ccts_complaints import CctsComplaintsScraper
from app.scrapers.consumer.cpsc_recalls import CpscRecallsScraper
from app.scrapers.consumer.health_canada_recalls import HealthCanadaRecallsScraper
from app.scrapers.consumer.obsi_decisions import ObsiDecisionsScraper
from app.scrapers.consumer.opc_breach_reports import OpcBreachReportsScraper
from app.scrapers.consumer.provincial_privacy_commissioners import ProvincialPrivacyCommissionersScraper
from app.scrapers.consumer.transport_canada_recalls import TransportCanadaRecallsScraper

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "consumer"

def load_fixture(name: str) -> str:
    path = FIXTURE_DIR / f"{name}.html"
    if not path.exists():
        path = FIXTURE_DIR / f"{name}.json"
    if not path.exists():
        path = FIXTURE_DIR / f"{name}.xml"
    if not path.exists():
        return "<html><body>No fixture found</body></html>"
    return path.read_text(encoding="utf-8")

SCRAPERS = [
    BbbComplaintsScraper,
    CctsComplaintsScraper,
    CpscRecallsScraper,
    HealthCanadaRecallsScraper,
    ObsiDecisionsScraper,
    OpcBreachReportsScraper,
    ProvincialPrivacyCommissionersScraper,
    TransportCanadaRecallsScraper,
]

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_consumer_scraper_returns_results(scraper_cls):
    """Scraper returns list[ScraperResult] with valid structure."""
    scraper = scraper_cls()
    fixture_content = load_fixture(scraper.source_id)
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = fixture_content
    mock_response.json.return_value = {} # Default if JSON
    
    with patch("app.scrapers.base.BaseScraper.get", return_value=mock_response):
        results = await scraper.scrape()
        
        assert isinstance(results, list)
        if results:
            for r in results:
                assert r.source_id == scraper.source_id
                assert isinstance(r.signal_type, str)
                # For consumer scrapers, they might only have raw_company_name or source_url
                assert r.source_url or r.raw_company_name

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_consumer_scraper_handles_empty_response(scraper_cls):
    """Scraper returns [] on empty/error response."""
    scraper = scraper_cls()
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.text = ""
    
    with patch("app.scrapers.base.BaseScraper.get", return_value=mock_response):
        results = await scraper.scrape()
        assert results == []

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_consumer_scraper_handles_timeout(scraper_cls):
    """Scraper returns [] on timeout, does not raise."""
    scraper = scraper_cls()
    
    with patch("app.scrapers.base.BaseScraper.get", side_effect=asyncio.TimeoutError()):
        results = await scraper.scrape()
        assert results == []

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_consumer_scraper_health_check(scraper_cls):
    """health_check() returns bool."""
    scraper = scraper_cls()
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    
    with patch("app.scrapers.base.BaseScraper.get", return_value=mock_response):
        assert await scraper.health_check() is True
        
    with patch("app.scrapers.base.BaseScraper.get", side_effect=Exception("Failed")):
        assert await scraper.health_check() is False
