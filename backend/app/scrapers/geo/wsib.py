"""
app/scrapers/geo/wsib.py — WSIB (Workplace Safety and Insurance Board) scraper.

Source: https://www.wsib.ca/en/about-wsib/news-and-events/news-releases
  - WSIB does not publish individual claims data publicly.
  - News releases contain enforcement actions, penalty decisions, and
    policy changes that signal employment law exposure.

Signal types:
  geo_wsib_penalty          — penalty or fine mentioned in news release
  geo_wsib_compliance_order — compliance order or enforcement action

Rate: 0.2 rps (government site)
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_WSIB_NEWS_URL = "https://www.wsib.ca/en/about-wsib/news-and-events/news-releases"

# Keywords that indicate enforcement/penalty in WSIB news releases
_PENALTY_KEYWORDS = frozenset(
    {
        "penalty",
        "fine",
        "fined",
        "penalized",
        "conviction",
        "prosecuted",
        "prosecution",
        "violation",
    }
)
_COMPLIANCE_KEYWORDS = frozenset(
    {
        "compliance",
        "order",
        "enforcement",
        "inspection",
        "non-compliance",
        "workplace safety",
        "fatality",
        "injury",
    }
)


@register
class WsibScraper(BaseScraper):
    """
    WSIB (Workplace Safety and Insurance Board) enforcement scraper.

    Scrapes WSIB news releases for enforcement actions — signals employment
    law exposure, workplace injury litigation, and regulatory compliance issues.

    Note: WSIB does not publish individual company claims data publicly.
    This scraper monitors news releases for enforcement mentions only.
    """

    source_id = "geo_wsib"
    source_name = "WSIB (Workplace Safety and Insurance Board)"
    signal_types = ["geo_wsib_penalty", "geo_wsib_compliance_order"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape WSIB news releases for enforcement actions."""
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_WSIB_NEWS_URL)
            if soup is None:
                log.warning("wsib_page_unavailable")
                return []

            # WSIB news page lists articles as links in the main content area
            articles = soup.select("article, .views-row, .news-item, li a[href*='news']")
            if not articles:
                # Fallback: try generic link extraction from main content
                articles = soup.select("main a[href], .content a[href]")

            for article in articles[:50]:  # Cap at 50 items
                parsed = self._parse_article(article)
                if parsed:
                    results.append(parsed)

        except Exception as exc:
            log.error("wsib_scrape_error", error=str(exc))

        log.info("wsib_scrape_complete", results=len(results))
        return results

    def _parse_article(self, element: object) -> ScraperResult | None:
        """Parse a news article/link element from WSIB page."""
        title = self.safe_text(element)
        if not title or len(title) < 10:
            return None

        # Extract link
        href = ""
        if hasattr(element, "get"):
            href = element.get("href", "") or ""  # type: ignore[union-attr]
        if hasattr(element, "find"):
            link_el = element.find("a")  # type: ignore[union-attr]
            if link_el:
                href = link_el.get("href", "") or ""

        if href and not href.startswith("http"):
            href = f"https://www.wsib.ca{href}"

        title_lower = title.lower()
        signal_type = self._classify_signal(title_lower)
        if not signal_type:
            return None

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            source_url=href or _WSIB_NEWS_URL,
            signal_value={"title": title},
            signal_text=f"WSIB: {title}",
            practice_area_hints=["employment_labour", "regulatory"],
            raw_payload={"title": title, "url": href},
            confidence_score=0.6,
        )

    @staticmethod
    def _classify_signal(text: str) -> str | None:
        """Classify news text into a signal type, or None if not relevant."""
        if any(kw in text for kw in _PENALTY_KEYWORDS):
            return "geo_wsib_penalty"
        if any(kw in text for kw in _COMPLIANCE_KEYWORDS):
            return "geo_wsib_compliance_order"
        return None
