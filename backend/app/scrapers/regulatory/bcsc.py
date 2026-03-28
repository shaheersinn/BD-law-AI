"""
app/scrapers/regulatory/bcsc.py — BC Securities Commission scraper.

Data source: https://www.bcsc.bc.ca/enforcement/enforcement-actions
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — BCSC enforcement predicts securities litigation mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BCSC_ENFORCEMENT_URL = (
    "https://www.bcsc.bc.ca/enforcement/enforcement-actions"
)


@register
class BCSCScraper(BaseScraper):
    """
    BC Securities Commission scraper.

    Scrapes enforcement actions from BCSC.
    """

    source_id = "regulatory_bcsc"
    source_name = "BC Securities Commission"
    signal_types = ["regulatory_enforcement", "regulatory_cease_trade"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape BCSC enforcement actions."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_BCSC_ENFORCEMENT_URL)
            if resp.status_code != 200:
                log.warning("bcsc_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.find_all("article")
                or soup.select("table tbody tr")
                or soup.find_all("div", class_="views-row")
                or soup.select("ul.list-unstyled li, div.card, div.enforcement-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("bcsc_scrape_error", error=str(exc))

        log.info("bcsc_scrape_complete", count=len(results))
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

        link_el = item.find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = (
                href
                if href.startswith("http")
                else f"https://www.bcsc.bc.ca{href}"
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

        respondent = self._extract_respondent(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_enforcement",
            raw_company_name=respondent,
            source_url=source_url,
            signal_value={"title": title, "regulator": "BCSC"},
            signal_text=f"BCSC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["securities", "litigation", "regulatory"],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.85,
        )

    def _parse_table_row(
        self, cells: list[Any], cutoff: datetime
    ) -> ScraperResult | None:
        respondent = self.safe_text(cells[0])
        if not respondent or len(respondent) < 3:
            return None

        action_type = self.safe_text(cells[1]) if len(cells) > 1 else ""
        date_str = self.safe_text(cells[2]) if len(cells) > 2 else ""
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
                else f"https://www.bcsc.bc.ca{href}"
            )

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_enforcement",
            raw_company_name=respondent,
            source_url=source_url,
            signal_value={
                "respondent": respondent,
                "action_type": action_type,
                "regulator": "BCSC",
            },
            signal_text=f"BCSC: {action_type} — {respondent}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["securities", "litigation", "regulatory"],
            raw_payload={
                "respondent": respondent,
                "action_type": action_type,
            },
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_respondent(title: str) -> str | None:
        lower = title.lower()
        for prefix in ["in the matter of ", "re ", "settlement with "]:
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                name = title[idx:].split(" — ")[0].split(" - ")[0].strip()
                if name:
                    return name
        return None
