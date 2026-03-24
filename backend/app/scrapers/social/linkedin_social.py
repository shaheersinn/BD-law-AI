"""
app/scrapers/social/linkedin_social.py — LinkedIn social signals scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class LinkedInSocialScraper(BaseScraper):
    """
    LinkedIn social signals scraper.

    Scrapes company posts and updates from LinkedIn for corporate activity signals.
    """

    source_id = "social_linkedin"
    source_name = "LinkedIn"
    signal_types = ["social_linkedin_post", "social_company_update"]
    CATEGORY = "social"
    rate_limit_rps = 0.1
    concurrency = 1
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """Scrape LinkedIn company posts and updates."""
        # TODO: Phase 1C — implement full scraper using Proxycurl API
        return []
