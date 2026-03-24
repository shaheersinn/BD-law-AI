"""
app/scrapers/social/twitter.py — Twitter/X scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class TwitterScraper(BaseScraper):
    """
    Twitter/X scraper.

    Scrapes Twitter mentions and trending topics related to Canadian companies.
    """

    source_id = "social_twitter"
    source_name = "Twitter/X"
    signal_types = ["social_twitter_mention", "social_trending_topic"]
    CATEGORY = "social"
    rate_limit_rps = 0.5
    concurrency = 2
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Twitter mentions and trending topics."""
        # TODO: Phase 1C — implement full scraper using Twitter Bearer Token
        return []
