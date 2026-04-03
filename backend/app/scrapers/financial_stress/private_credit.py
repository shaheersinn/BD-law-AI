"""
Private credit deterioration scraper.

Sources: D&B Direct+ API, Equifax Canada Commercial API, TransUnion Canada
Commercial API — all require subscriptions.

Signal: private_credit_deterioration — fires when PAYDEX drops >20 points
in 90 days or DBT exceeds 30 days.

NOTE: All three sources require paid subscriptions. This scraper is FULLY
degradable — when no credentials are configured, it logs a warning and
returns [].
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_DNB_API_URL = "https://plus.dnb.com/v1/data/duns"
_EQUIFAX_API_URL = "https://api.equifax.ca/business/v1"
_TRANSUNION_API_URL = "https://api.transunion.ca/commercial/v1"


@register
class PrivateCreditScraper(BaseScraper):
    source_id = "financial_stress_private_credit"
    source_name = "Private Credit Bureaus (D&B / Equifax / TransUnion)"
    signal_types = ["private_credit_deterioration"]
    CATEGORY = "financial_stress"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """
        All three credit bureau APIs require paid subscriptions.
        This scraper degrades gracefully when no credentials are available.
        """
        results: list[ScraperResult] = []

        # D&B Direct+
        try:
            dnb_results = await self._scrape_dnb()
            results.extend(dnb_results)
        except Exception as exc:
            log.warning("private_credit_dnb_error", error=str(exc))

        # Equifax Canada
        try:
            equifax_results = await self._scrape_equifax()
            results.extend(equifax_results)
        except Exception as exc:
            log.warning("private_credit_equifax_error", error=str(exc))

        return results

    async def _scrape_dnb(self) -> list[ScraperResult]:
        """Query D&B Direct+ for PAYDEX deterioration. Requires DNB_API_KEY."""
        from app.config import get_settings  # noqa: PLC0415

        settings = get_settings()
        api_key = getattr(settings, "dnb_api_key", None) or ""
        if not api_key:
            log.warning(
                "private_credit_dnb_no_key",
                msg="DNB_API_KEY not configured — skipping D&B scraper",
            )
            return []

        # With a valid key, would query D&B Direct+ API
        # Placeholder: return empty until subscription is active
        log.info("private_credit_dnb_ready", msg="D&B API key configured but scraper stub active")
        return []

    async def _scrape_equifax(self) -> list[ScraperResult]:
        """Query Equifax Canada Commercial API. Requires EQUIFAX_API_KEY."""
        from app.config import get_settings  # noqa: PLC0415

        settings = get_settings()
        api_key = getattr(settings, "equifax_api_key", None) or ""
        if not api_key:
            log.warning(
                "private_credit_equifax_no_key",
                msg="EQUIFAX_API_KEY not configured — skipping Equifax scraper",
            )
            return []

        log.info(
            "private_credit_equifax_ready", msg="Equifax API key configured but scraper stub active"
        )
        return []
