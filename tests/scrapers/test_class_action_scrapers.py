import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pathlib import Path
import httpx

from app.scrapers.class_actions.alberta_class_proceedings import AlbertaClassProceedingsScraper
from app.scrapers.class_actions.bc_class_proceedings import BcClassProceedingsScraper
from app.scrapers.class_actions.branch_macmaster_class_actions import BranchMacmasterClassActionsScraper
from app.scrapers.class_actions.cba_class_actions import CbaClassActionsScraper
from app.scrapers.class_actions.classaction_ca import ClassActionCaScraper
from app.scrapers.class_actions.federal_court_class_proceedings import FederalCourtClassProceedingsScraper
from app.scrapers.class_actions.koskie_minsky_class_actions import KoskieMinskyClassActionsScraper
from app.scrapers.class_actions.merchant_law_class_actions import MerchantLawClassActionsScraper
from app.scrapers.class_actions.ontario_class_proceedings import OntarioClassProceedingsScraper
from app.scrapers.class_actions.pacer_class_actions import PacerClassActionsScraper
from app.scrapers.class_actions.quebec_class_proceedings import QuebecClassProceedingsScraper
from app.scrapers.class_actions.siskinds_class_actions import SiskindsClassActionsScraper

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "class_actions"

def load_fixture(name: str) -> str:
    path = FIXTURE_DIR / f"{name}.html"
    if not path.exists():
        path = FIXTURE_DIR / f"{name}.json"
    if not path.exists():
        return "<html><body>No fixture found</body></html>"
    return path.read_text(encoding="utf-8")

SCRAPERS = [
    AlbertaClassProceedingsScraper,
    BcClassProceedingsScraper,
    BranchMacmasterClassActionsScraper,
    CbaClassActionsScraper,
    ClassActionCaScraper,
    FederalCourtClassProceedingsScraper,
    KoskieMinskyClassActionsScraper,
    MerchantLawClassActionsScraper,
    OntarioClassProceedingsScraper,
    PacerClassActionsScraper,
    QuebecClassProceedingsScraper,
    SiskindsClassActionsScraper,
]

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_class_action_scraper_returns_results(scraper_cls):
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
                assert r.source_url or r.raw_company_name
                assert "class_actions" in r.practice_area_hints

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_class_action_scraper_handles_empty_response(scraper_cls):
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
async def test_class_action_scraper_handles_timeout(scraper_cls):
    """Scraper returns [] on timeout, does not raise."""
    scraper = scraper_cls()
    
    with patch("app.scrapers.base.BaseScraper.get", side_effect=asyncio.TimeoutError()):
        results = await scraper.scrape()
        assert results == []

@pytest.mark.asyncio
@pytest.mark.parametrize("scraper_cls", SCRAPERS)
async def test_class_action_scraper_health_check(scraper_cls):
    """health_check() returns bool."""
    scraper = scraper_cls()
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    
    with patch("app.scrapers.base.BaseScraper.get", return_value=mock_response):
        assert await scraper.health_check() is True
        
    with patch("app.scrapers.base.BaseScraper.get", side_effect=Exception("Failed")):
        assert await scraper.health_check() is False
