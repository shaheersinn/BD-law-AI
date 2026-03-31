"""
app/scrapers/class_actions/koskie_minsky_class_actions.py — Koskie Minsky LLP.

Data source: https://www.kmlaw.ca/cases
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — Leading pension/employment class action firm
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.kmlaw.ca"
_CASES_URL = f"{_BASE_URL}/cases"


@register
class KoskieMinskyClassActionsScraper(BaseScraper):
    """
    Koskie Minsky LLP class actions scraper.

    Leading pension and employment class action firm.
    Scrapes active cases and investigations.
    Rate limit: 0.5 rps (commercial law firm site).
    """

    source_id = "class_action_koskie_minsky"
    source_name = "Koskie Minsky LLP — Class Actions"
    signal_types = ["class_action_filed", "class_action_investigation"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=180)

        try:
            resp = await self.get(_CASES_URL)
            if resp.status_code != 200:
                log.warning("koskie_minsky_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article")
                or soup.select("div.case-item")
                or soup.select("div.views-row")
                or soup.select("ul li a[href*='case']")
                or soup.select("div.card, li.list-group-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("koskie_minsky_scrape_error", error=str(exc))

        log.info("koskie_minsky_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            if item.name == "a":
                title_el = item
            else:
                return None
        title = self.safe_text(title_el)
        if not title or len(title) < 5:
            return None

        link_el = item.find("a", href=True) if item.name != "a" else item
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

        signal_type = self._classify_signal(title)
        company = self._extract_company(title)
        practice_areas = self._infer_practice_areas(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "title": title,
                "firm": "Koskie Minsky LLP",
                "case_type": "class_action",
                "status": "investigation" if "investigation" in signal_type else "filed",
            },
            signal_text=f"Koskie Minsky: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={"title": title, "firm": "Koskie Minsky LLP", "url": source_url},
            confidence_score=0.80,
        )

    @staticmethod
    def _classify_signal(title: str) -> str:
        lower = title.lower()
        if "investigation" in lower or "investigating" in lower:
            return "class_action_investigation"
        return "class_action_filed"

    @staticmethod
    def _extract_company(title: str) -> str | None:
        for sep in [" v. ", " vs. ", " against ", " re "]:
            if sep in title.lower():
                idx = title.lower().index(sep) + len(sep)
                name = title[idx:].split(",")[0].split("(")[0].strip()
                if name and len(name) > 2:
                    return name
        return None

    @staticmethod
    def _infer_practice_areas(title: str) -> list[str]:
        areas: list[str] = ["class_actions", "litigation"]
        lower = title.lower()
        if "pension" in lower or "benefit" in lower:
            areas.append("pension_benefits")
        if "employ" in lower or "wage" in lower or "labour" in lower:
            areas.append("employment_labour")
        if "securities" in lower or "shareholder" in lower:
            areas.append("securities_capital_markets")
        if "insur" in lower:
            areas.append("insurance_reinsurance")
        return list(dict.fromkeys(areas))
