"""
Art auction estate liquidation scraper.

Sources: Heffel (heffel.com) + Waddington's (waddingtons.ca) auction catalogues.
Signal: estate_art_liquidation — fires when estate collections appear in major
Canadian auction house catalogues.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_HEFFEL_AUCTIONS_URL = "https://www.heffel.com/Auction/UpcomingAuctions_EN.aspx"
_WADDINGTONS_AUCTIONS_URL = "https://www.waddingtons.ca/auctions/"

_ESTATE_KEYWORDS = [
    "from the estate of",
    "property of a private collector",
    "estate collection",
    "collection of the late",
    "deceased estate",
    "the late",
    "estate of",
]

_HIGH_VALUE_THRESHOLD = 250_000  # CAD


@register
class ArtAuctionScraper(BaseScraper):
    source_id = "hnwi_art_auctions"
    source_name = "Heffel / Waddington's Art Auctions"
    signal_types = ["estate_art_liquidation"]
    CATEGORY = "hnwi"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for url, house_name in [
            (_HEFFEL_AUCTIONS_URL, "Heffel"),
            (_WADDINGTONS_AUCTIONS_URL, "Waddington's"),
        ]:
            try:
                page_results = await self._scrape_auction_house(url, house_name)
                results.extend(page_results)
            except Exception as exc:
                log.error("art_auction_error", house=house_name, error=str(exc))

        return results

    async def _scrape_auction_house(
        self, url: str, house_name: str
    ) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(url)
            if not soup:
                return results
        except Exception as exc:
            log.warning("art_auction_fetch_error", house=house_name, error=str(exc))
            return results

        # Parse auction lot entries
        lot_elements = (
            soup.find_all("div", class_=re.compile(r"lot|item|catalogue", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"lot|item", re.I))
        )

        for lot in lot_elements[:50]:
            try:
                text = self.safe_text(lot).lower()
                if not text:
                    continue

                # Check for estate-related keywords
                is_estate = any(kw in text for kw in _ESTATE_KEYWORDS)
                if not is_estate:
                    continue

                title = self.safe_text(lot.find(["h2", "h3", "h4", "a"])) or text[:100]

                # Try to extract estimate value
                estimate = self._extract_estimate(text)
                is_high_value = estimate is not None and estimate >= _HIGH_VALUE_THRESHOLD

                link_el = lot.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        base = url.split("/")[0] + "//" + url.split("/")[2]
                        source_url = base + href

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="estate_art_liquidation",
                        raw_company_name=self._extract_estate_name(text),
                        source_url=source_url or url,
                        signal_value={
                            "auction_house": house_name,
                            "title": title,
                            "is_high_value": is_high_value,
                            "estimate_cad": estimate,
                        },
                        signal_text=f"{house_name}: {title}",
                        published_at=self._now_utc(),
                        practice_area_hints=["Wills / Estates"],
                        raw_payload={"house": house_name, "title": title, "text": text[:500]},
                        confidence_score=0.85 if is_high_value else 0.70,
                    )
                )
            except Exception as exc:
                log.warning("art_auction_lot_parse_error", error=str(exc))

        return results

    @staticmethod
    def _extract_estimate(text: str) -> int | None:
        """Extract dollar estimate from lot text."""
        patterns = [
            r"\$\s*([\d,]+)\s*(?:,\d{3})*",
            r"estimate[d]?\s*(?:at\s*)?\$\s*([\d,]+)",
            r"([\d,]+)\s*(?:cad|cdn)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_estate_name(text: str) -> str | None:
        """Extract estate/collector name from descriptive text."""
        for prefix in ["from the estate of ", "collection of the late ", "estate of "]:
            idx = text.find(prefix)
            if idx != -1:
                name_start = idx + len(prefix)
                # Take up to next punctuation or end
                remaining = text[name_start:]
                match = re.match(r"([a-z\s\.\-']+)", remaining, re.I)
                if match:
                    name = match.group(1).strip().title()
                    if len(name) > 3:
                        return name
        return None
