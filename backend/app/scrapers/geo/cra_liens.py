"""
app/scrapers/geo/cra_liens.py — CRA tax lien scraper (documented stub).

CRA lien data requires provincial PPSA registry access — not publicly queryable
via web. Individual tax lien records are filed with provincial land registries
(e.g., Ontario's Teranet/Parcel Register) and PPSA (Personal Property Security
Act) registries. These are not available through any free public API.

Possible future implementation paths:
  1. Teranet API partnership (Ontario land registry — paid, per-search pricing)
  2. BC Land Title and Survey Authority API (paid subscription)
  3. Saskatchewan ISC (paid)
  4. Alberta SPIN (paid)

Until a registry API partnership is established, this scraper monitors the CRA
newsroom for enforcement-related press releases as a partial proxy.

Source: https://www.canada.ca/en/revenue-agency/news.html

Signal types:
  geo_cra_tax_lien          — tax enforcement action (from news)
  geo_cra_director_liability — director liability or assessment (from news)

Rate: 0.2 rps (government site)
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CRA_NEWS_URL = "https://www.canada.ca/en/revenue-agency/news.html"

# Keywords signalling tax enforcement actions
_TAX_ENFORCEMENT_KEYWORDS = frozenset(
    {
        "tax evasion",
        "tax fraud",
        "guilty plea",
        "sentenced",
        "convicted",
        "charged",
        "prosecution",
        "penalty",
        "director liability",
        "assessment",
        "garnishment",
        "lien",
        "seizure",
        "compliance action",
    }
)


@register
class CraTaxLienScraper(BaseScraper):
    """
    Canada Revenue Agency (CRA) tax lien and enforcement scraper.

    Note: CRA lien data requires provincial PPSA registry access — not publicly
    queryable via web. Future implementation requires Teranet or equivalent API
    partnership. This scraper monitors CRA newsroom for enforcement press releases
    as a partial proxy signal.
    """

    source_id = "geo_cra_liens"
    source_name = "CRA Tax Liens and Enforcement"
    signal_types = ["geo_cra_tax_lien", "geo_cra_director_liability"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape CRA newsroom for tax enforcement press releases."""
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_CRA_NEWS_URL)
            if soup is None:
                log.warning("cra_news_unavailable")
                return []

            # canada.ca news pages list items in .item-group or similar selectors
            links = soup.select(
                "article a, .item a, .views-row a, "
                "main a[href*='news'], li a[href*='revenue-agency']"
            )
            if not links:
                links = soup.select("main a[href]")

            seen: set[str] = set()
            for link in links[:50]:
                title = self.safe_text(link)
                if not title or len(title) < 15 or title in seen:
                    continue
                seen.add(title)

                href = link.get("href", "") or ""
                if href and not href.startswith("http"):
                    href = f"https://www.canada.ca{href}"

                parsed = self._parse_news_item(title, href)
                if parsed:
                    results.append(parsed)

        except Exception as exc:
            log.error("cra_scrape_error", error=str(exc))

        log.info("cra_scrape_complete", results=len(results))
        return results

    def _parse_news_item(self, title: str, url: str) -> ScraperResult | None:
        """Parse a CRA news item, filtering for enforcement content only."""
        title_lower = title.lower()

        if not any(kw in title_lower for kw in _TAX_ENFORCEMENT_KEYWORDS):
            return None

        signal_type = (
            "geo_cra_director_liability"
            if "director" in title_lower or "liability" in title_lower
            else "geo_cra_tax_lien"
        )

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            source_url=url or _CRA_NEWS_URL,
            signal_value={"title": title},
            signal_text=f"CRA Enforcement: {title}",
            practice_area_hints=["tax", "insolvency"],
            raw_payload={"title": title, "url": url},
            confidence_score=0.65,
        )
