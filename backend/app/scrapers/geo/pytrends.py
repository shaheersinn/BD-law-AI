"""
app/scrapers/geo/pytrends.py — PyTrends (Google Trends) scraper stub.

Note: The primary Google Trends implementation lives in google_trends.py.
This file provides a PyTrends-specific stub for direct pytrends API access.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class PyTrendsScraper(BaseScraper):
    """
    PyTrends direct scraper stub.

    Queries Google Trends via the pytrends library for Canadian legal keyword spikes.
    See also: geo_scrapers.google_trends for the primary implementation.
    """

    source_id = "geo_pytrends"
    source_name = "PyTrends (Google Trends Direct)"
    signal_types = ["geo_trends_legal_spike", "geo_trends_keyword_spike"]
    CATEGORY = "geo"
    rate_limit_rps = 0.016  # 1 req/60s — pytrends aggressive throttle
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Google Trends keyword spikes via pytrends."""
        # TODO: Phase 1C — implement full scraper
        return []
