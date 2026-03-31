"""
app/scrapers/class_actions/federal_court_class_proceedings.py — Federal Court class proceedings.

Data source: https://www.fct-cf.gc.ca/en/pages/law-and-practice/class-proceedings
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — Federal class actions often involve national-scope issues
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.fct-cf.gc.ca"
_CLASS_ACTIONS_URL = f"{_BASE_URL}/en/pages/law-and-practice/class-proceedings"


@register
class FederalCourtClassProceedingsScraper(BaseScraper):
    """
    Federal Court of Canada class proceedings scraper.

    Scrapes class proceedings information from the Federal Court.
    Rate limit: 0.2 rps (government court site).
    """

    source_id = "class_action_federal"
    source_name = "Federal Court of Canada — Class Proceedings"
    signal_types = ["class_action_filed_federal"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=180)

        try:
            resp = await self.get(_CLASS_ACTIONS_URL)
            if resp.status_code != 200:
                log.warning("federal_ca_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.select("div.view-content div.views-row")
                or soup.select("ul.list-unstyled li")
                or soup.select("article, div.card")
            )

            for item in items[:50]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("federal_ca_scrape_error", error=str(exc))

        log.info("federal_ca_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        cells = item.find_all("td")
        if cells and len(cells) >= 2:
            case_name = self.safe_text(cells[0])
            case_number = self.safe_text(cells[1]) if len(cells) > 1 else ""
            date_str = self.safe_text(cells[-1]) if len(cells) > 2 else ""
        else:
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                return None
            case_name = self.safe_text(title_el)
            case_number = ""
            date_el = item.find("time") or item.find(
                class_=lambda c: c and "date" in str(c).lower()
            )
            date_str = ""
            if date_el:
                date_str = date_el.get("datetime") or self.safe_text(date_el)

        if not case_name or len(case_name) < 5:
            return None

        published_at = self._parse_date(date_str)
        if published_at and published_at < cutoff:
            return None

        link_el = item.find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        company = self._extract_defendant(case_name)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="class_action_filed_federal",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": case_name,
                "case_number": case_number,
                "jurisdiction": "FED",
                "court": "Federal Court of Canada",
                "status": "filed",
                "case_type": "class_action",
            },
            signal_text=f"Federal Court class action: {case_name}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["class_actions", "litigation", "administrative_public_law"],
            raw_payload={"case_name": case_name, "case_number": case_number},
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_defendant(case_name: str) -> str | None:
        for sep in [" v. ", " v ", " vs. "]:
            if sep in case_name:
                parts = case_name.split(sep, 1)
                return parts[1].split(",")[0].split("(")[0].strip() if len(parts) > 1 else None
        return None
