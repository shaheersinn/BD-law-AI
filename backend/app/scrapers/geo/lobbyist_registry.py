"""
app/scrapers/geo/lobbyist_registry.py — Office of the Commissioner of Lobbying scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class LobbyistRegistryScraper(BaseScraper):
    """
    Office of the Commissioner of Lobbying of Canada scraper.

    Scrapes lobbyist registration data — signals pending regulatory changes,
    government relations activity, and policy disputes.
    """

    source_id = "geo_lobbyist"
    source_name = "Office of the Commissioner of Lobbying of Canada"
    signal_types = ["geo_lobbyist_registration", "geo_lobbying_activity"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape lobbyist registration and activity data."""
        # TODO: Phase 1C — implement full scraper using Lobbying Registry open data
        return []
