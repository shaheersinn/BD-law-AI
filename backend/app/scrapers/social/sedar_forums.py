"""
app/scrapers/social/sedar_forums.py — SEDAR investor forums scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class SedarForumsScraper(BaseScraper):
    """
    SEDAR investor forums scraper.

    Scrapes investor forums and complaint boards associated with SEDAR-listed companies.
    """

    source_id = "social_sedar_forums"
    source_name = "SEDAR Investor Forums"
    signal_types = ["social_sedar_forum_post", "social_investor_complaint"]
    CATEGORY = "social"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape SEDAR-related investor forum posts and complaints."""
        # TODO: Phase 1C — implement full scraper
        return []
