"""
app/scrapers/regulatory/doj.py — Canada Department of Justice scraper.

Data source: https://www.justice.gc.ca/eng/news-nouv.html
Approach: HTML scraping with BeautifulSoup
Signal value: MEDIUM — Federal DOJ news predicts regulatory/compliance mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_DOJ_URL = "https://www.justice.gc.ca/eng/news-nouv.html"
_DOJ_BASE = "https://www.justice.gc.ca"


@register
class CanadaDOJScraper(BaseScraper):
    """
    Canada Department of Justice scraper.

    Scrapes news releases and enforcement announcements from
    the federal Department of Justice.
    Rate limit: 0.2 rps (government site).
    """

    source_id = "regulatory_doj_canada"
    source_name = "Canada Department of Justice"
    signal_types = ["regulatory_federal"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Canada DOJ news page for enforcement announcements."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_DOJ_URL)
            if resp.status_code != 200:
                log.warning("doj_canada_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article")
                or soup.select("ul.feeds-cont li")
                or soup.select("div.views-row")
                or soup.select("table tbody tr")
                or soup.select("div.item, li.list-group-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("doj_canada_scrape_error", error=str(exc))

        log.info("doj_canada_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
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
            source_url = href if href.startswith("http") else f"{_DOJ_BASE}{href}"

        date_el = item.find("time") or item.find(
            class_=lambda c: c and "date" in str(c).lower()
        )
        published_at = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        practice_areas = self._infer_practice_areas(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_federal",
            raw_company_name=None,
            source_url=source_url,
            signal_value={"title": title, "regulator": "Canada DOJ"},
            signal_text=f"Canada DOJ: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.70,
        )

    @staticmethod
    def _infer_practice_areas(title: str) -> list[str]:
        lower = title.lower()
        areas: list[str] = ["regulatory_compliance", "administrative_public_law"]
        keyword_map = {
            "criminal": ["litigation"],
            "fraud": ["litigation", "securities_capital_markets"],
            "competition": ["competition_antitrust"],
            "privacy": ["privacy_cybersecurity"],
            "immigration": ["immigration_corporate"],
            "tax": ["tax"],
            "environment": ["environmental_indigenous_energy"],
            "indigenous": ["environmental_indigenous_energy"],
            "trade": ["international_trade_customs"],
            "insolvency": ["insolvency_restructuring"],
            "bankruptcy": ["insolvency_restructuring"],
        }
        for keyword, hints in keyword_map.items():
            if keyword in lower:
                areas.extend(hints)
        return list(dict.fromkeys(areas))
