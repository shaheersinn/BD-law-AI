"""
app/scrapers/geo/municipal_permits.py — Municipal building permits scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class MunicipalPermitsScraper(BaseScraper):
    """
    Municipal building permits scraper.

    Scrapes major Canadian city open data portals for building permits —
    signals construction activity, real estate disputes, zoning conflicts.
    """

    source_id = "geo_municipal"
    source_name = "Municipal Building Permits (Toronto/Vancouver/Calgary)"
    signal_types = ["geo_municipal_permit_issued", "geo_municipal_permit_value"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape municipal building permit data."""
        # TODO: Phase 1C — implement full scraper using city open data APIs
        return []
