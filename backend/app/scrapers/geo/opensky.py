"""
app/scrapers/geo/opensky.py — OpenSky Network flight tracking scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class OpenSkyScraper(BaseScraper):
    """
    OpenSky Network flight tracking scraper.

    Monitors private jet and corporate aircraft movements as a proxy for
    executive travel signals — M&A due diligence, emergency board meetings.
    """

    source_id = "geo_opensky"
    source_name = "OpenSky Network (Corporate Flight Tracking)"
    signal_types = ["geo_flight_corporate_jet", "geo_executive_travel"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """Scrape corporate flight activity from OpenSky Network."""
        # TODO: Phase 1C — implement full scraper using OpenSky REST API
        return []
