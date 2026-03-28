"""
app/scrapers/regulatory/opc.py — Office of the Privacy Commissioner scraper.

Data source: https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — OPC findings directly predict privacy law mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OPC_INVESTIGATIONS_URL = (
    "https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/"
)
_OPC_FINDINGS_URL = (
    "https://www.priv.gc.ca/en/opc-actions-and-decisions/"
    "investigations/investigations-into-businesses/"
)


@register
class OPCScraper(BaseScraper):
    """
    Office of the Privacy Commissioner of Canada scraper.

    Scrapes investigation findings and enforcement decisions.
    Filters out French-language records.
    """

    source_id = "regulatory_opc"
    source_name = "Office of the Privacy Commissioner of Canada"
    signal_types = ["regulatory_enforcement", "regulatory_privacy_finding"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape OPC investigation findings."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        for url, signal_type in [
            (_OPC_FINDINGS_URL, "regulatory_privacy_finding"),
            (_OPC_INVESTIGATIONS_URL, "regulatory_enforcement"),
        ]:
            try:
                page_results = await self._scrape_page(url, signal_type, cutoff)
                results.extend(page_results)
            except Exception as exc:
                log.error("opc_page_error", url=url, error=str(exc))

        log.info("opc_scrape_complete", count=len(results))
        return results

    async def _scrape_page(
        self, url: str, signal_type: str, cutoff: datetime
    ) -> list[ScraperResult]:
        resp = await self.get(url)
        if resp.status_code != 200:
            log.warning("opc_fetch_failed", url=url, status=resp.status_code)
            return []

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[ScraperResult] = []

        items = (
            soup.find_all("article")
            or soup.select("table tbody tr")
            or soup.find_all("div", class_="views-row")
            or soup.select("ul li, div.card")
        )

        for item in items[:30]:
            result = self._parse_item(item, signal_type, cutoff)
            if result:
                results.append(result)

        return results

    def _parse_item(
        self, item: Any, signal_type: str, cutoff: datetime
    ) -> ScraperResult | None:
        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            cells = item.find_all("td")
            if cells and len(cells) >= 2:
                return self._parse_table_row(cells, signal_type, cutoff)
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
                else f"https://www.priv.gc.ca{href}"
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

        company_name = self._extract_respondent(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company_name,
            source_url=source_url,
            signal_value={"title": title, "regulator": "OPC"},
            signal_text=f"OPC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["privacy_data", "regulatory", "litigation"],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.90,
        )

    def _parse_table_row(
        self, cells: list[Any], signal_type: str, cutoff: datetime
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
                else f"https://www.priv.gc.ca{href}"
            )

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=None,
            source_url=source_url,
            signal_value={"title": title, "regulator": "OPC"},
            signal_text=f"OPC: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["privacy_data", "regulatory", "litigation"],
            raw_payload={"title": title},
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_respondent(title: str) -> str | None:
        lower = title.lower()
        for prefix in [
            "investigation into ",
            "complaint against ",
            "report of findings — ",
            "report of findings - ",
        ]:
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                name = title[idx:].split(" — ")[0].split(" - ")[0].strip()
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
