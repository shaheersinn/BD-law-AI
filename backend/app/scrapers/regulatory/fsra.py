"""
app/scrapers/regulatory/fsra.py — Financial Services Regulatory Authority of Ontario scraper.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class FSRAScraper(BaseScraper):
    """
    Financial Services Regulatory Authority of Ontario scraper.

    Scrapes regulatory enforcement actions and bulletins.
    """

    source_id = "regulatory_fsra"
    source_name = "Financial Services Regulatory Authority of Ontario"
    signal_types = ["regulatory_enforcement", "regulatory_bulletin"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2  # government site — be respectful
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape regulatory enforcement actions."""
        # TODO: Phase 1C — implement full scraper
        return []
