"""
app/scrapers/regulatory/osc.py — Ontario Securities Commission scraper.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class OSCScraper(BaseScraper):
    """
    Ontario Securities Commission scraper.

    Scrapes regulatory enforcement actions and bulletins.
    """

    source_id = "regulatory_osc"
    source_name = "Ontario Securities Commission"
    signal_types = ["regulatory_enforcement", "regulatory_bulletin"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2  # government site — be respectful
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape regulatory enforcement actions."""
        # TODO: Phase 1C — implement full scraper
        return []
