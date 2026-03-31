"""
app/scrapers/class_actions/cba_class_actions.py — Canadian Bar Association class action publications.

Data source: https://www.cba.org/ (search class action publications)
Approach: HTML scraping with BeautifulSoup
Signal value: MEDIUM — trend intelligence on which sectors are heating up
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.cba.org"
_SEARCH_URL = f"{_BASE_URL}/Sections/Class-Actions/Articles"


@register
class CBAClassActionsScraper(BaseScraper):
    """
    Canadian Bar Association class action publications scraper.

    Provides trend intelligence — which sectors are heating up
    for class action litigation. Rate limit: 0.5 rps.
    """

    source_id = "class_action_cba"
    source_name = "Canadian Bar Association — Class Actions"
    signal_types = ["class_action_analysis"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_SEARCH_URL)
            if resp.status_code != 200:
                log.warning("cba_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article")
                or soup.select("div.search-result")
                or soup.select("div.views-row")
                or soup.select("ul.results li")
                or soup.select("div.card, li.list-group-item")
            )

            for item in items[:20]:
                result = self._parse_article(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("cba_scrape_error", error=str(exc))

        log.info("cba_scrape_complete", count=len(results))
        return results

    def _parse_article(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title or len(title) < 10:
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

        summary_el = item.find("p") or item.find(class_="summary")
        summary = self.safe_text(summary_el) if summary_el else ""

        practice_areas = self._infer_practice_areas(title, summary)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="class_action_analysis",
            raw_company_name=None,
            source_url=source_url,
            signal_value={
                "title": title,
                "summary": summary[:500],
                "source": "CBA",
            },
            signal_text=f"CBA Class Action Analysis: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={"title": title, "summary": summary, "url": source_url},
            confidence_score=0.60,
        )

    @staticmethod
    def _infer_practice_areas(title: str, summary: str) -> list[str]:
        areas: list[str] = ["class_actions", "litigation"]
        combined = f"{title} {summary}".lower()
        mapping = {
            "securities": ["securities_capital_markets"],
            "product": ["product_liability"],
            "privacy": ["privacy_cybersecurity"],
            "employ": ["employment_labour"],
            "environ": ["environmental_indigenous_energy"],
            "competi": ["competition_antitrust"],
            "pension": ["pension_benefits"],
            "insur": ["insurance_reinsurance"],
        }
        for keyword, hints in mapping.items():
            if keyword in combined:
                areas.extend(hints)
        return list(dict.fromkeys(areas))
