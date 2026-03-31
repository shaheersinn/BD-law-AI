"""
app/scrapers/regulatory/osfi_enforcement.py — OSFI Enforcement Actions scraper.

Data source: https://www.osfi-bsif.gc.ca/en/supervision/enforcement
Approach: HTML scraping (enforcement actions page)
Signal value: HIGH — OSFI actions directly predict banking/finance mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OSFI_ENFORCEMENT_URL = "https://www.osfi-bsif.gc.ca/en/supervision/enforcement"


@register
class OSFIEnforcementScraper(BaseScraper):
    """
    OSFI Enforcement Actions scraper.

    Scrapes enforcement actions from the Office of the Superintendent
    of Financial Institutions.
    """

    source_id = "regulatory_osfi_enforcement"
    source_name = "OSFI Enforcement Actions"
    signal_types = ["regulatory_enforcement", "regulatory_osfi_action"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape OSFI enforcement actions."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_OSFI_ENFORCEMENT_URL)
            if resp.status_code != 200:
                log.warning("osfi_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.find_all("article")
                or soup.find_all("div", class_="views-row")
                or soup.select("ul.list-unstyled li, div.enforcement-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("osfi_scrape_error", error=str(exc))

        log.info("osfi_scrape_complete", count=len(results))
        return results

    def _parse_item(self, item: Any, cutoff: datetime) -> ScraperResult | None:
        cells = item.find_all("td")
        if cells and len(cells) >= 2:
            return self._parse_table_row(cells, cutoff)
        return self._parse_article_item(item, cutoff)

    def _parse_table_row(self, cells: list[Any], cutoff: datetime) -> ScraperResult | None:
        institution = self.safe_text(cells[0])
        if not institution or len(institution) < 3:
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
            source_url = href if href.startswith("http") else f"https://www.osfi-bsif.gc.ca{href}"

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_osfi_action",
            raw_company_name=institution,
            source_url=source_url,
            signal_value={
                "institution": institution,
                "action_type": action_type,
                "regulator": "OSFI",
            },
            signal_text=f"OSFI: {action_type} — {institution}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["banking_finance", "regulatory", "insurance"],
            raw_payload={
                "institution": institution,
                "action_type": action_type,
                "date": date_str,
            },
            confidence_score=0.90,
        )

    def _parse_article_item(self, item: Any, cutoff: datetime) -> ScraperResult | None:
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
            source_url = href if href.startswith("http") else f"https://www.osfi-bsif.gc.ca{href}"

        date_el = item.find("time") or item.find(class_=lambda c: c and "date" in str(c).lower())
        date_str = ""
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
        published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_enforcement",
            raw_company_name=None,
            source_url=source_url,
            signal_value={"title": title, "regulator": "OSFI"},
            signal_text=f"OSFI: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["banking_finance", "regulatory", "insurance"],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.85,
        )
