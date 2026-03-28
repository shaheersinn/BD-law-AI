"""
app/scrapers/regulatory/osc.py — Ontario Securities Commission scraper.

Data source: https://www.osc.ca/en/securities-law/enforcement/
Approach: HTML scraping with BeautifulSoup (no official API)
Update frequency: Daily (enforcement actions published irregularly)
Signal value: CRITICAL — OSC enforcement is direct mandate signal for
  securities litigation, regulatory defence, cease trade order work
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OSC_ENFORCEMENT_URL = (
    "https://www.osc.ca/en/securities-law/enforcement"
    "/enforcement-notices-and-temporary-orders"
)
_OSC_SETTLEMENTS_URL = (
    "https://www.osc.ca/en/securities-law/enforcement/settlements"
)


@register
class OSCScraper(BaseScraper):
    """
    Ontario Securities Commission scraper.

    Scrapes enforcement notices, temporary orders, and settlements.
    """

    source_id = "regulatory_osc"
    source_name = "Ontario Securities Commission"
    signal_types = [
        "regulatory_enforcement",
        "regulatory_cease_trade",
        "regulatory_settlement",
    ]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape OSC enforcement actions and settlements."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        for url, signal_type in [
            (_OSC_ENFORCEMENT_URL, "regulatory_enforcement"),
            (_OSC_SETTLEMENTS_URL, "regulatory_settlement"),
        ]:
            try:
                page_results = await self._scrape_page(url, signal_type, cutoff)
                results.extend(page_results)
            except Exception as exc:
                log.error("osc_page_error", url=url, error=str(exc))

        log.info("osc_scrape_complete", count=len(results))
        return results

    async def _scrape_page(
        self, url: str, signal_type: str, cutoff: datetime
    ) -> list[ScraperResult]:
        resp = await self.get(url)
        if resp.status_code != 200:
            log.warning("osc_fetch_failed", url=url, status=resp.status_code)
            return []

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[ScraperResult] = []

        items = (
            soup.find_all("article")
            or soup.find_all("div", class_="views-row")
            or soup.find_all("li", class_="views-row")
            or soup.select("table tbody tr")
        )

        for item in items[:30]:
            try:
                result = self._parse_item(item, signal_type, cutoff)
                if result:
                    results.append(result)
            except Exception as exc:
                log.warning("osc_parse_item_error", error=str(exc))

        return results

    def _parse_item(
        self, item: Any, signal_type: str, cutoff: datetime
    ) -> ScraperResult | None:
        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title or len(title) < 5:
            return None

        if self._is_french_only(title):
            return None

        link_el = item.find("a", href=True)
        source_url = ""
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"https://www.osc.ca{href}"

        date_el = item.find("time") or item.find(
            ["span", "div"], class_=lambda c: c and "date" in str(c).lower()
        )
        published_at: datetime | None = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        company_name = self._extract_respondent(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company_name,
            source_url=source_url or None,
            signal_value={
                "title": title,
                "action_type": signal_type,
                "regulator": "OSC",
            },
            signal_text=f"OSC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["securities", "litigation", "regulatory"],
            raw_payload={
                "title": title,
                "url": source_url,
                "action_type": signal_type,
            },
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_respondent(title: str) -> str | None:
        lower = title.lower()
        for prefix in [
            "in the matter of ",
            "re ",
            "settlement with ",
            "temporary order — ",
            "temporary order - ",
        ]:
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                name = title[idx:].split(" — ")[0].split(" - ")[0].split(" and ")[0].strip()
                if name:
                    return name
        return None

    @staticmethod
    def _is_french_only(title: str) -> bool:
        french_markers = [" et ", " de la ", " du ", " les ", " des ", " aux "]
        english_markers = ["the ", "and ", " or ", " of ", " for ", " in "]
        has_french = any(m in f" {title.lower()} " for m in french_markers)
        has_english = any(m in f" {title.lower()} " for m in english_markers)
        return has_french and not has_english
