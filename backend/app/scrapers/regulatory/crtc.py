"""
app/scrapers/regulatory/crtc.py — CRTC scraper.

Data source: https://crtc.gc.ca/eng/deci.htm (decisions page)
Approach: HTML scraping; skip French-language decisions
Signal value: MODERATE — CRTC decisions predict telecom regulatory mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CRTC_DECISIONS_URL = "https://crtc.gc.ca/eng/deci.htm"


@register
class CRTCScraper(BaseScraper):
    """
    CRTC (Canadian Radio-television and Telecommunications Commission) scraper.

    Scrapes regulatory decisions and enforcement actions.
    Filters out French-language records.
    """

    source_id = "regulatory_crtc"
    source_name = "CRTC (Canadian Radio-television and Telecommunications Commission)"
    signal_types = ["regulatory_enforcement", "regulatory_crtc_decision"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape CRTC decisions and enforcement actions."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_CRTC_DECISIONS_URL)
            if resp.status_code != 200:
                log.warning("crtc_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.find_all("article")
                or soup.find_all("li", class_="views-row")
                or soup.select("ul li, div.views-row")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("crtc_scrape_error", error=str(exc))

        log.info("crtc_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        cells = item.find_all("td")
        if cells and len(cells) >= 2:
            return self._parse_table_row(cells, cutoff)

        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title or len(title) < 5:
            return None

        if self._is_french_only(title):
            return None

        link_el = item.find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = (
                href
                if href.startswith("http")
                else f"https://crtc.gc.ca{href}"
            )

        date_el = item.find("time") or item.find(
            class_=lambda c: c and "date" in str(c).lower()
        )
        published_at = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_crtc_decision",
            raw_company_name=None,
            source_url=source_url,
            signal_value={"title": title, "regulator": "CRTC"},
            signal_text=f"CRTC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["regulatory", "media_telecom"],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.80,
        )

    def _parse_table_row(
        self, cells: list[Any], cutoff: datetime
    ) -> ScraperResult | None:
        title = self.safe_text(cells[0])
        if not title or len(title) < 5:
            return None

        if self._is_french_only(title):
            return None

        date_str = self.safe_text(cells[-1])
        published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        link_el = cells[0].find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = (
                href
                if href.startswith("http")
                else f"https://crtc.gc.ca{href}"
            )

        decision_type = self.safe_text(cells[1]) if len(cells) > 1 else ""

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_crtc_decision",
            raw_company_name=None,
            source_url=source_url,
            signal_value={
                "title": title,
                "decision_type": decision_type,
                "regulator": "CRTC",
            },
            signal_text=f"CRTC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["regulatory", "media_telecom"],
            raw_payload={
                "title": title,
                "decision_type": decision_type,
            },
            confidence_score=0.80,
        )

    @staticmethod
    def _is_french_only(title: str) -> bool:
        french_markers = [" et ", " de la ", " du ", " les ", " des ", " aux "]
        english_markers = ["the ", "and ", " or ", " of ", " for ", " in "]
        has_french = any(m in f" {title.lower()} " for m in french_markers)
        has_english = any(m in f" {title.lower()} " for m in english_markers)
        return has_french and not has_english
