"""
app/scrapers/geo/commodity_prices.py — Commodity prices scraper stub.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class CommodityPricesScraper(BaseScraper):
    """
    Commodity prices scraper.

    Tracks Canadian commodity price movements (oil, gas, metals, agriculture) —
    sector-specific signals for energy, mining, and agricultural legal mandates.
    """

    source_id = "geo_commodity"
    source_name = "Commodity Prices (Alpha Vantage / Yahoo Finance)"
    signal_types = ["geo_commodity_price_shock", "geo_commodity_price_trend"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape commodity price data for sector stress signals."""
        # TODO: Phase 1C — implement full scraper using Alpha Vantage API
        return []
