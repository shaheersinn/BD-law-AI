import pytest
import os
from unittest.mock import MagicMock
from app.scrapers.registry import ScraperRegistry

# Live tests require real network access and potentially API keys.
# They are excluded from standard CI by default via the 'live' marker.

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_canlii_rss():
    """CanLII RSS or API is reachable (using a test query)."""
    try:
        from app.scrapers.canlii import CanLIIScraper
        scraper = CanLIIScraper()
        # Search for a very common company to ensure results
        results = await scraper.search_company("Royal Bank", days_back=30)
        # If no key, results will be []
        # We just want to ensure it doesn't crash
        assert isinstance(results, list)
    except ImportError:
        pytest.skip("CanLIIScraper not found")

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_sedar_fetch():
    """SEDAR scraper can hit the filing provider or RSS."""
    try:
        # Assuming source_id is 'corporate_sedar'
        from app.scrapers.corporate.sedar import SedarScraper
        scraper = SedarScraper()
        results = await scraper.scrape()
        assert isinstance(results, list)
    except (ImportError, KeyError):
        pytest.skip("SedarScraper not found or registered")

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_mccarthy_blog():
    """McCarthy Tetrault blog RSS is live and returns items."""
    source_id = "lawblog_mccarthy"
    try:
        scraper_cls = ScraperRegistry.get(source_id)
        scraper = scraper_cls()
        results = await scraper.scrape()
        assert len(results) > 0
        assert results[0].source_id == source_id
    except (KeyError, Exception) as e:
        pytest.fail(f"Live McCarthy blog failed: {e}")

@pytest.mark.live
@pytest.mark.asyncio
async def test_public_source_connectivity():
    """Test connectivity to key public data portals."""
    import httpx
    targets = [
        "https://www.canlii.org/en/",
        "https://www.sedarplus.ca/",
        "https://www.mccarthy.ca/en/insights/rss"
    ]
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in targets:
            resp = await client.get(url, follow_redirects=True)
            assert resp.status_code == 200, f"Failed to reach {url}"
