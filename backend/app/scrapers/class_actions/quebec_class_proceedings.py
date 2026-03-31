"""
app/scrapers/class_actions/quebec_class_proceedings.py — Quebec class proceedings registry.

Data source: https://www.registredesactionscollectives.gouv.qc.ca/en
Approach: HTML scraping with BeautifulSoup (English section only)
Signal value: HIGH — Quebec has most class-action-friendly regime in Canada
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.registredesactionscollectives.gouv.qc.ca"
_REGISTRY_URL = f"{_BASE_URL}/en/Consulter/Recherche"


@register
class QuebecClassProceedingsScraper(BaseScraper):
    """
    Quebec Registre des actions collectives scraper.

    English section only per project rules. Scrapes the class action
    registry for filed and certified collective actions.
    Rate limit: 0.2 rps (government site).
    """

    source_id = "class_action_quebec"
    source_name = "Quebec Class Action Registry"
    signal_types = ["class_action_filed", "class_action_certified"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=180)

        try:
            resp = await self.get(_REGISTRY_URL)
            if resp.status_code != 200:
                log.warning("quebec_ca_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.select("div.search-results div.result-item")
                or soup.select("ul.results li")
                or soup.select("article, div.card")
            )

            for item in items[:50]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("quebec_ca_scrape_error", error=str(exc))

        log.info("quebec_ca_scrape_complete", count=len(results))
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
            source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        date_el = item.find("time") or item.find(
            class_=lambda c: c and "date" in str(c).lower()
        )
        published_at = None
        if date_el:
            published_at = self._parse_date(
                date_el.get("datetime") or self.safe_text(date_el)
            )

        if published_at and published_at < cutoff:
            return None

        status = self._infer_status(title)
        company = self._extract_defendant(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=f"class_action_{status}",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": title,
                "jurisdiction": "QC",
                "court": "Quebec Superior Court",
                "status": status,
                "case_type": "collective_action",
            },
            signal_text=f"Quebec collective action ({status}): {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["class_actions", "litigation"],
            raw_payload={"case_name": title, "url": source_url},
            confidence_score=0.85,
        )

    def _parse_table_row(
        self, cells: list[Any], cutoff: datetime
    ) -> ScraperResult | None:
        case_name = self.safe_text(cells[0])
        if not case_name or len(case_name) < 5:
            return None

        case_number = self.safe_text(cells[1]) if len(cells) > 1 else ""
        date_str = self.safe_text(cells[-1]) if len(cells) > 2 else ""
        published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        link_el = cells[0].find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        status = self._infer_status(case_name)
        company = self._extract_defendant(case_name)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=f"class_action_{status}",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": case_name,
                "case_number": case_number,
                "jurisdiction": "QC",
                "court": "Quebec Superior Court",
                "status": status,
            },
            signal_text=f"Quebec collective action ({status}): {case_name}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["class_actions", "litigation"],
            raw_payload={"case_name": case_name, "case_number": case_number},
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_defendant(case_name: str) -> str | None:
        for sep in [" v. ", " c. ", " v ", " vs. "]:
            if sep in case_name:
                parts = case_name.split(sep, 1)
                return parts[1].split(",")[0].split("(")[0].strip() if len(parts) > 1 else None
        return None

    @staticmethod
    def _infer_status(text: str) -> str:
        lower = text.lower()
        if "settl" in lower or "approv" in lower:
            return "settled"
        if "certif" in lower or "autoris" in lower:
            return "certified"
        if "dismiss" in lower or "rejet" in lower:
            return "dismissed"
        return "filed"
