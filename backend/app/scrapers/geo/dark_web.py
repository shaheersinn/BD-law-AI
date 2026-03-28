"""
app/scrapers/geo/dark_web.py — Dark web breach monitoring scraper.

Source: HaveIBeenPwned API v3 — https://haveibeenpwned.com/API/v3
  - /breaches — all known breaches (free, no auth for this endpoint)
  - /breachedaccount/{email} — requires API key ($3.50/month)
  - Domain-level breach checks require API key

A data breach → predict privacy law mandate within 30 days
(mandatory breach notification under PIPEDA).

Note: There is also a social_breach_monitor scraper in app/scrapers/social/
that covers HIBP + CCCS advisories. This geo scraper focuses on domain-level
breach detection for companies in our database, while the social scraper
covers the general breach feed.

Signal types:
  geo_data_breach    — data breach detected for a company domain
  geo_darkweb_mention — breach involving Canadian companies

Rate: 0.05 rps (HIBP rate limit: 10 req/min with API key)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_HIBP_BREACHES = "https://haveibeenpwned.com/api/v3/breaches"


@register
class DarkWebBreachScraper(BaseScraper):
    """
    Dark web breach monitoring scraper.

    Monitors HaveIBeenPwned breach database for recent breaches —
    signals privacy law, cybersecurity regulatory, and class action exposure.

    Requires HIBP_API_KEY environment variable. Returns [] if not configured.
    """

    source_id = "geo_darkweb"
    source_name = "Dark Web Breach Monitor (HaveIBeenPwned)"
    signal_types = ["geo_data_breach", "geo_darkweb_mention"]
    CATEGORY = "geo"
    rate_limit_rps = 0.05
    concurrency = 1
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        """Scrape HIBP breaches feed for recent breaches."""
        settings = get_settings()
        hibp_key = getattr(settings, "hibp_api_key", "")
        if not hibp_key:
            log.info("dark_web_skipped_no_api_key")
            return []

        results: list[ScraperResult] = []

        try:
            resp = await self.get(
                _HIBP_BREACHES,
                headers={
                    "hibp-api-key": hibp_key,
                    "User-Agent": "ORACLE-BD/1.0",
                },
            )
            if resp.status_code != 200:
                log.warning("hibp_non200", status=resp.status_code)
                return []

            breaches = resp.json()
            if not isinstance(breaches, list):
                return []

            cutoff = datetime.now(tz=UTC) - timedelta(days=30)

            for breach in breaches:
                parsed = self._parse_breach(breach, cutoff)
                if parsed:
                    results.append(parsed)

        except Exception as exc:
            log.error("hibp_scrape_error", error=str(exc))

        log.info("dark_web_scrape_complete", results=len(results))
        return results

    def _parse_breach(
        self, breach: dict, cutoff: datetime
    ) -> ScraperResult | None:
        """Parse a single HIBP breach record."""
        added_date = self._parse_date(breach.get("AddedDate"))
        if added_date and added_date < cutoff:
            return None

        if not breach.get("IsVerified"):
            return None

        name = breach.get("Name", "")
        domain = breach.get("Domain", "")
        pwn_count = breach.get("PwnCount", 0)
        data_classes = breach.get("DataClasses", [])
        is_sensitive = breach.get("IsSensitive", False)

        # Higher confidence for sensitive breaches or large breaches
        confidence = 0.7
        if is_sensitive:
            confidence = 0.9
        elif pwn_count > 1_000_000:
            confidence = 0.85
        elif pwn_count > 100_000:
            confidence = 0.8

        signal_type = (
            "geo_data_breach" if domain else "geo_darkweb_mention"
        )

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=name,
            source_url=f"https://haveibeenpwned.com/PwnedWebsites#{name}",
            signal_value={
                "breach_name": name,
                "breach_date": breach.get("BreachDate"),
                "added_date": breach.get("AddedDate"),
                "pwn_count": pwn_count,
                "data_classes": data_classes,
                "is_sensitive": is_sensitive,
                "domain": domain,
            },
            signal_text=(
                f"Data breach: {name} — {pwn_count:,} records"
                f"{' (sensitive)' if is_sensitive else ''}"
            ),
            published_at=added_date,
            practice_area_hints=["privacy", "technology", "class_actions"],
            raw_payload=breach,
            confidence_score=confidence,
        )
