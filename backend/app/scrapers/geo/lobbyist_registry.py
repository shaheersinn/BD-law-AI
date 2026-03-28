"""
app/scrapers/geo/lobbyist_registry.py — Federal Lobbyist Registry scraper.

Source: https://lobbycanada.gc.ca
  - Open Data portal provides monthly XML/CSV data dumps
  - RSS feed for new registrations: https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/cmmnsRss

A company registering lobbyists for "financial regulations" in Ottawa →
predict banking/regulatory mandate within 60–90 days.

Signal types:
  geo_lobbyist_registration — new or renewed lobbyist registration
  geo_lobbying_activity     — active lobbying on a specific subject matter

Rate: 0.2 rps (government site)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405 — trusted government RSS

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_LOBBY_CANADA_RSS = "https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/cmmnsRss"

# Mapping of lobbying subject matters to ORACLE practice areas
_SUBJECT_TO_PRACTICE: dict[str, list[str]] = {
    "financial": ["banking_finance", "securities"],
    "taxation": ["tax"],
    "environment": ["environmental", "mining"],
    "energy": ["environmental", "mining", "infrastructure"],
    "health": ["health_law"],
    "industry": ["competition_antitrust", "regulatory"],
    "international trade": ["international_trade", "customs"],
    "immigration": ["immigration"],
    "transport": ["infrastructure"],
    "defence": ["administrative_public_law"],
    "intellectual property": ["intellectual_property"],
    "privacy": ["privacy", "technology"],
    "labour": ["employment_labour"],
    "housing": ["real_estate", "construction"],
    "justice": ["litigation", "regulatory"],
    "procurement": ["infrastructure", "administrative_public_law"],
    "telecommunications": ["technology"],
    "science": ["technology", "intellectual_property"],
    "agriculture": ["international_trade"],
}


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
        """Scrape lobbyist registration and activity data from RSS feed."""
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_LOBBY_CANADA_RSS)
            if resp.status_code != 200:
                log.warning("lobbyist_rss_non200", status=resp.status_code)
                return []

            root = ET.fromstring(resp.text)  # nosec B314 — trusted government RSS
            for item in root.iter("item"):
                parsed = self._parse_rss_item(item)
                if parsed:
                    results.append(parsed)

        except Exception as exc:
            log.error("lobbyist_scrape_error", error=str(exc))

        log.info("lobbyist_scrape_complete", results=len(results))
        return results

    def _parse_rss_item(self, item: ET.Element) -> ScraperResult | None:
        """Parse a single RSS item from the Lobby Canada feed."""
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()

        if not title:
            return None

        # Extract company/organization from title (format: "Organization - Type")
        registrant = title.split(" - ")[0].strip() if " - " in title else title

        # Determine practice area hints from description keywords
        hints = self._match_practice_areas(description + " " + title)
        if not hints:
            hints = ["regulatory"]

        signal_type = (
            "geo_lobbyist_registration"
            if "registration" in title.lower() or "new" in title.lower()
            else "geo_lobbying_activity"
        )

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=registrant,
            source_url=link or "https://lobbycanada.gc.ca",
            signal_value={
                "registrant": registrant,
                "description": description,
            },
            signal_text=f"Lobbyist registry: {title}",
            published_at=self._parse_date(pub_date),
            practice_area_hints=hints,
            raw_payload={"title": title, "description": description, "link": link},
            confidence_score=0.65,
        )

    @staticmethod
    def _match_practice_areas(text: str) -> list[str]:
        """Match lobbying subject matter keywords to practice areas."""
        text_lower = text.lower()
        matched: list[str] = []
        for keyword, areas in _SUBJECT_TO_PRACTICE.items():
            if keyword in text_lower:
                for area in areas:
                    if area not in matched:
                        matched.append(area)
        return matched
