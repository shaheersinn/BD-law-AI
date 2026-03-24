"""
app/scrapers/social/reddit.py — Reddit scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class RedditScraper(BaseScraper):
    """
    Reddit scraper.

    Scrapes subreddit mentions and activity related to Canadian companies and legal topics.
    """

    source_id = "social_reddit"
    source_name = "Reddit"
    signal_types = ["social_reddit_mention", "social_subreddit_activity"]
    CATEGORY = "social"
    rate_limit_rps = 0.5
    concurrency = 2
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Reddit mentions and subreddit activity."""
        # TODO: Phase 1C — implement full scraper using Reddit OAuth API
        return []
