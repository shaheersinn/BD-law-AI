"""
app/scrapers/class_actions/alberta_class_proceedings.py — Alberta Court class proceedings.

Data source: https://www.albertacourts.ca/kb/class-proceedings
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — Alberta class actions often involve energy/resource companies
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.albertacourts.ca"
_CLASS_ACTIONS_URL = f"{_BASE_URL}/kb/class-proceedings"


@register
class AlbertaClassProceedingsScraper(BaseScraper):
    """
    Alberta Court of King's Bench class proceedings scraper.

    Scrapes class proceedings from the Alberta courts website.
    Rate limit: 0.2 rps (government court site).
    """

    source_id = "class_action_alberta"
    source_name = "Alberta Court of King's Bench — Class Proceedings"
    signal_types = ["class_action_filed"]
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
                log.warning("alberta_ca_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.select("div.view-content div.views-row")
                or soup.select("ul li a")
                or soup.select("article, div.card")
            )

            for item in items[:50]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("alberta_ca_scrape_error", error=str(exc))

        log.info("alberta_ca_scrape_complete", count=len(results))
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
                if item.name == "a":
                    title_el = item
                else:
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

        link_el = item.find("a", href=True) if item.name != "a" else item
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        company = self._extract_defendant(case_name)
        practice_areas: list[str] = ["class_actions", "litigation"]
        lower = case_name.lower()
        if any(kw in lower for kw in ["oil", "gas", "energy", "pipeline"]):
            practice_areas.append("environmental_indigenous_energy")
        if "securities" in lower or "fraud" in lower:
            practice_areas.append("securities_capital_markets")

        return ScraperResult(
            source_id=self.source_id,
            signal_type="class_action_filed",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": case_name,
                "case_number": case_number,
                "jurisdiction": "AB",
                "court": "Alberta Court of King's Bench",
                "status": "filed",
                "case_type": "class_action",
            },
            signal_text=f"Alberta class action: {case_name}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
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
