"""
app/scrapers/geo/cra_liens.py — CRA tax lien scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class CraTaxLienScraper(BaseScraper):
    """
    Canada Revenue Agency (CRA) tax lien and garnishment scraper.

    Scrapes CRA enforcement actions including director liability notices,
    tax liens, and garnishments — financial distress leading indicator.
    """

    source_id = "geo_cra_liens"
    source_name = "CRA Tax Liens and Enforcement"
    signal_types = ["geo_cra_tax_lien", "geo_cra_director_liability"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape CRA tax liens and enforcement actions."""
        # TODO: Phase 1C — implement full scraper
        return []
