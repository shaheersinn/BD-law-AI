import pytest
import asyncio
from app.scrapers.registry import _load_registry, _REGISTRY

def get_all_scraper_classes():
    _load_registry()
    # Handle both Name and source_id for old scrapers
    return list(_REGISTRY.values())

@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_has_required_attributes(scraper_cls):
    """Verify that every registered scraper has the required BaseScraper attributes."""
    scraper = scraper_cls()
    assert isinstance(scraper.source_id, str) and len(scraper.source_id) > 0
    assert isinstance(scraper.source_name, str) and len(scraper.source_name) > 0
    assert isinstance(scraper.signal_types, list) and len(scraper.signal_types) > 0
    assert scraper.rate_limit_rps > 0
    assert scraper.concurrency >= 1
    assert hasattr(scraper, 'scrape')
    assert asyncio.iscoroutinefunction(scraper.scrape)
    assert hasattr(scraper, 'health_check')

@pytest.mark.parametrize("scraper_cls", get_all_scraper_classes())
def test_scraper_source_id_unique(scraper_cls):
    """No two scrapers share the same source_id."""
    _load_registry()
    ids = [cls().source_id for cls in _REGISTRY.values()]
    assert len(ids) == len(set(ids)), f"Duplicate source_ids found: {[x for x in ids if ids.count(x) > 1]}"

def test_registry_minimum_count():
    """Regression guard — catches accidental deregistration."""
    _load_registry()
    count = len(_REGISTRY)
    assert count >= 110, f"Expected >= 110 scrapers, got {count}. Scrapers were deregistered!"
