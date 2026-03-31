"""
app/scrapers/social/sedar_forums.py — SEDAR forums scraper stub.

SEDAR+ (sedarplus.ca) does not have a public discussion or forum component.
This scraper exists as a stub and returns [] on every run.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class SedarForumsScraper(BaseScraper):
    source_id = "social_sedar_forums"
    source_name = "SEDAR Investor Forums"
    signal_types = ["social_sedar_forum_post", "social_investor_complaint"]
    CATEGORY = "social"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        log.info(
            "sedar_forums_not_available",
            note="SEDAR+ has no public forum component — stub returns []",
        )
        return []
