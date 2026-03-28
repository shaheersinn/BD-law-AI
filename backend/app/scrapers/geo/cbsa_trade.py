"""
app/scrapers/geo/cbsa_trade.py — Canada Border Services Agency trade data scraper.

Sources:
  - CBSA SIMA (Special Import Measures Act) investigations/decisions:
    https://www.cbsa-asfc.gc.ca/sima-lmsi/menu-eng.html
  - CBSA Advance Rulings:
    https://www.cbsa-asfc.gc.ca/publications/dm-md/d11/d11-11-3-eng.html
  - CBSA enforcement actions news:
    https://www.cbsa-asfc.gc.ca/media/release-communique/menu-eng.html

Anti-dumping and countervailing duty investigations are strong signals for
international trade law mandates.

Signal types:
  geo_cbsa_enforcement — CBSA enforcement action or news release
  geo_trade_remedy     — SIMA (anti-dumping/countervailing duty) investigation

Rate: 0.2 rps (government site)
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CBSA_NEWS_URL = (
    "https://www.cbsa-asfc.gc.ca/media/release-communique/menu-eng.html"
)
_CBSA_SIMA_URL = "https://www.cbsa-asfc.gc.ca/sima-lmsi/menu-eng.html"

# Keywords for trade remedy actions
_TRADE_REMEDY_KEYWORDS = frozenset({
    "anti-dumping", "dumping", "countervailing", "subsidy",
    "safeguard", "sima", "special import measures",
    "normal value", "preliminary determination", "final determination",
    "expiry review", "re-investigation",
})

# Keywords for general CBSA enforcement
_ENFORCEMENT_KEYWORDS = frozenset({
    "seizure", "smuggling", "contraband", "penalty",
    "non-compliance", "customs", "tariff", "duty",
    "embargo", "prohibition", "detention",
})


@register
class CbsaTradeScraper(BaseScraper):
    """
    Canada Border Services Agency (CBSA) trade data scraper.

    Scrapes CBSA news releases and SIMA investigation pages for
    trade enforcement actions — signals trade law and customs disputes.
    """

    source_id = "geo_cbsa"
    source_name = "Canada Border Services Agency (CBSA) Trade Data"
    signal_types = ["geo_cbsa_enforcement", "geo_trade_remedy"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape CBSA news and SIMA pages for trade enforcement signals."""
        results: list[ScraperResult] = []

        # CBSA news releases
        try:
            results.extend(await self._scrape_news())
        except Exception as exc:
            log.error("cbsa_news_error", error=str(exc))

        await self._rate_limit_sleep()

        # SIMA investigations
        try:
            results.extend(await self._scrape_sima())
        except Exception as exc:
            log.error("cbsa_sima_error", error=str(exc))

        log.info("cbsa_scrape_complete", results=len(results))
        return results

    async def _scrape_news(self) -> list[ScraperResult]:
        """Scrape CBSA news/media releases page."""
        soup = await self.get_soup(_CBSA_NEWS_URL)
        if soup is None:
            log.warning("cbsa_news_unavailable")
            return []

        results: list[ScraperResult] = []
        links = soup.select("main a[href], .wet-boew-multimedia a, li a")

        seen: set[str] = set()
        for link in links[:50]:
            title = self.safe_text(link)
            if not title or len(title) < 15 or title in seen:
                continue
            seen.add(title)

            href = link.get("href", "") or ""
            if href and not href.startswith("http"):
                href = f"https://www.cbsa-asfc.gc.ca{href}"

            title_lower = title.lower()
            if any(kw in title_lower for kw in _ENFORCEMENT_KEYWORDS | _TRADE_REMEDY_KEYWORDS):
                signal_type = (
                    "geo_trade_remedy"
                    if any(kw in title_lower for kw in _TRADE_REMEDY_KEYWORDS)
                    else "geo_cbsa_enforcement"
                )
                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type=signal_type,
                    source_url=href or _CBSA_NEWS_URL,
                    signal_value={"title": title, "source_page": "news"},
                    signal_text=f"CBSA: {title}",
                    practice_area_hints=["international_trade", "customs"],
                    raw_payload={"title": title, "url": href},
                    confidence_score=0.6,
                ))

        return results

    async def _scrape_sima(self) -> list[ScraperResult]:
        """Scrape CBSA SIMA (anti-dumping/countervailing duty) page."""
        soup = await self.get_soup(_CBSA_SIMA_URL)
        if soup is None:
            log.warning("cbsa_sima_unavailable")
            return []

        results: list[ScraperResult] = []
        links = soup.select("main a[href], li a[href]")

        seen: set[str] = set()
        for link in links[:50]:
            title = self.safe_text(link)
            if not title or len(title) < 10 or title in seen:
                continue
            seen.add(title)

            href = link.get("href", "") or ""
            if href and not href.startswith("http"):
                href = f"https://www.cbsa-asfc.gc.ca{href}"

            # SIMA pages list investigation names with product descriptions
            title_lower = title.lower()
            if any(kw in title_lower for kw in _TRADE_REMEDY_KEYWORDS) or (
                "investigation" in title_lower
            ):
                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type="geo_trade_remedy",
                    source_url=href or _CBSA_SIMA_URL,
                    signal_value={
                        "title": title,
                        "source_page": "sima",
                        "investigation_type": "sima",
                    },
                    signal_text=f"CBSA SIMA: {title}",
                    practice_area_hints=[
                        "international_trade", "customs", "competition_antitrust",
                    ],
                    raw_payload={"title": title, "url": href},
                    confidence_score=0.7,
                ))

        return results
