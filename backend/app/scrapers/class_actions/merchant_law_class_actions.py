"""
app/scrapers/class_actions/merchant_law_class_actions.py — Merchant Law Group LLP.

Data source: https://www.merchantlaw.com/class-actions
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — National class action firm with broad coverage
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.merchantlaw.com"
_CLASS_ACTIONS_URL = f"{_BASE_URL}/class-actions"


@register
class MerchantLawClassActionsScraper(BaseScraper):
    """
    Merchant Law Group LLP class actions scraper.

    National class action firm. Scrapes active investigations.
    Rate limit: 0.5 rps (commercial law firm site).
    """

    source_id = "class_action_merchant_law"
    source_name = "Merchant Law Group LLP — Class Actions"
    signal_types = ["class_action_investigation"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=180)

        try:
            resp = await self.get(_CLASS_ACTIONS_URL)
            if resp.status_code != 200:
                log.warning("merchant_law_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article")
                or soup.select("div.case-item")
                or soup.select("div.views-row")
                or soup.select("ul li a[href*='class']")
                or soup.select("div.card, li.list-group-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("merchant_law_scrape_error", error=str(exc))

        log.info("merchant_law_scrape_complete", count=len(results))
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

        company = self._extract_company(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="class_action_investigation",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "title": title,
                "firm": "Merchant Law Group LLP",
                "case_type": "class_action",
            },
            signal_text=f"Merchant Law investigation: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["class_actions", "litigation"],
            raw_payload={"title": title, "firm": "Merchant Law Group LLP", "url": source_url},
            confidence_score=0.75,
        )

    @staticmethod
    def _extract_company(title: str) -> str | None:
        for sep in [" v. ", " vs. ", " against ", " re "]:
            if sep in title.lower():
                idx = title.lower().index(sep) + len(sep)
                name = title[idx:].split(",")[0].split("(")[0].strip()
                if name and len(name) > 2:
                    return name
        return None
