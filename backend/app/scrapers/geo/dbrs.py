"""
app/scrapers/geo/dbrs.py — DBRS Morningstar credit rating actions scraper.

Source: https://dbrs.morningstar.com/research
  - DBRS Morningstar publishes press releases for rating actions
  - Full data requires paid subscription
  - Free tier shows recent rating action headlines on the research page

A credit rating downgrade → predict restructuring, refinancing, or
insolvency mandate within 90 days.

Signal types:
  geo_credit_downgrade         — downgrade or negative rating action
  geo_credit_outlook_negative  — negative outlook or credit watch

Note: DBRS full data requires a paid subscription. This scraper parses the
publicly accessible research/press release page. If the page is paywalled
or restructured, it returns [] gracefully.

Rate: 0.2 rps (respect commercial site)
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_DBRS_RESEARCH_URL = "https://dbrs.morningstar.com/research"

# Keywords for negative rating actions
_DOWNGRADE_KEYWORDS = frozenset({
    "downgrade", "downgraded", "lowered", "reduced",
    "cut", "revision down",
})

_NEGATIVE_OUTLOOK_KEYWORDS = frozenset({
    "negative outlook", "negative trend", "credit watch",
    "creditwatch negative", "under review with negative",
    "review-negative", "placed under review",
    "developing trend",
})

# Keywords confirming it's a rating action (not generic research)
_RATING_ACTION_KEYWORDS = frozenset({
    "rating", "rated", "confirms", "confirmed",
    "trend", "outlook", "review", "action",
    "upgrade", "downgrade", "affirm", "affirmed",
})


@register
class DbrsScraper(BaseScraper):
    """
    DBRS Morningstar credit rating actions scraper.

    Scrapes public credit rating action press releases — financial distress
    signals leading to insolvency, restructuring, banking mandates.

    Note: DBRS full data requires paid subscription. Free tier shows only
    recent headlines. Returns [] if page is paywalled or unavailable.
    """

    source_id = "geo_dbrs"
    source_name = "DBRS Morningstar Credit Ratings"
    signal_types = ["geo_credit_downgrade", "geo_credit_outlook_negative"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape DBRS Morningstar research page for rating actions."""
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_DBRS_RESEARCH_URL)
            if soup is None:
                log.warning(
                    "dbrs_page_unavailable",
                    note="DBRS full data requires paid subscription. "
                    "Free tier shows only recent headlines.",
                )
                return []

            # DBRS research page lists press releases as cards/links
            items = soup.select(
                "article, .research-item, .press-release, "
                ".card, a[href*='press-release'], a[href*='rating-action']"
            )
            if not items:
                items = soup.select("main a[href]")

            seen: set[str] = set()
            for item in items[:60]:
                title = self.safe_text(item)
                if not title or len(title) < 10 or title in seen:
                    continue
                seen.add(title)

                href = ""
                if hasattr(item, "get"):
                    href = item.get("href", "") or ""
                link_el = item.find("a") if hasattr(item, "find") else None
                if link_el and not href:
                    href = link_el.get("href", "") or ""

                if href and not href.startswith("http"):
                    href = f"https://dbrs.morningstar.com{href}"

                parsed = self._parse_rating_action(title, href)
                if parsed:
                    results.append(parsed)

        except Exception as exc:
            log.error("dbrs_scrape_error", error=str(exc))

        log.info("dbrs_scrape_complete", results=len(results))
        return results

    def _parse_rating_action(self, title: str, url: str) -> ScraperResult | None:
        """Parse a DBRS press release title into a ScraperResult."""
        title_lower = title.lower()

        # Must look like a rating action
        if not any(kw in title_lower for kw in _RATING_ACTION_KEYWORDS):
            return None

        # Classify signal type
        if any(kw in title_lower for kw in _DOWNGRADE_KEYWORDS):
            signal_type = "geo_credit_downgrade"
            confidence = 0.8
            hints = ["insolvency", "banking_finance", "securities"]
        elif any(kw in title_lower for kw in _NEGATIVE_OUTLOOK_KEYWORDS):
            signal_type = "geo_credit_outlook_negative"
            confidence = 0.7
            hints = ["insolvency", "banking_finance"]
        else:
            # Positive or neutral rating actions are not signals we care about
            return None

        # Try to extract company name — DBRS format: "DBRS Morningstar Downgrades Company X"
        company = self._extract_company(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=url or _DBRS_RESEARCH_URL,
            signal_value={
                "title": title,
                "action_type": signal_type.replace("geo_credit_", ""),
            },
            signal_text=f"DBRS: {title}",
            practice_area_hints=hints,
            raw_payload={"title": title, "url": url},
            confidence_score=confidence,
        )

    @staticmethod
    def _extract_company(title: str) -> str | None:
        """Attempt to extract company name from DBRS headline."""
        # Common patterns:
        #   "DBRS Morningstar Downgrades Company X to BB"
        #   "DBRS Morningstar Places Company X Under Review"
        #   "Company X Rating Downgraded"
        for prefix in ("DBRS Morningstar ", "Morningstar DBRS "):
            if title.startswith(prefix):
                rest = title[len(prefix):]
                # Skip the action verb
                parts = rest.split(" ", 1)
                if len(parts) >= 2:
                    entity = parts[1]
                    # Strip trailing rating/qualifier info
                    for cut in (" to ", " at ", " Rating", " Under ", "'s "):
                        if cut in entity:
                            entity = entity[:entity.index(cut)]
                    return entity.strip() or None
        return None
