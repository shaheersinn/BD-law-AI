"""
app/scrapers/social/stockhouse.py — Stockhouse investor forum scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class StockhouseScraper(BaseScraper):
    """
    Stockhouse investor forum scraper.

    Scrapes Stockhouse bulletin boards for investor sentiment and company mentions.
    """

    source_id = "social_stockhouse"
    source_name = "Stockhouse"
    signal_types = ["social_stockhouse_post", "social_investor_sentiment"]
    CATEGORY = "social"
    rate_limit_rps = 0.3
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Stockhouse forum posts and investor sentiment."""
        # TODO: Phase 1C — implement full scraper
        return []
