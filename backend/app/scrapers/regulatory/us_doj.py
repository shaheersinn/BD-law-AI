"""
app/scrapers/regulatory/us_doj.py — US Department of Justice scraper.

Data source: https://www.justice.gov/feeds/opa/justice-news.xml (RSS)
Approach: RSS feed parsing; filter for Canadian company mentions
Signal value: HIGH — DOJ actions predict cross-border litigation/M&A mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_DOJ_RSS_URL = "https://www.justice.gov/feeds/opa/justice-news.xml"

_CANADIAN_MARKERS = [
    "canada",
    "canadian",
    "ontario",
    "quebec",
    "british columbia",
    "alberta",
    "toronto",
    "vancouver",
    "montreal",
    "calgary",
    "ottawa",
    "tsx",
    "tsx-v",
    "tsxv",
]


@register
class USDOJScraper(BaseScraper):
    """
    US Department of Justice scraper.

    Scrapes DOJ press releases via RSS and filters for
    items mentioning Canadian companies or jurisdictions.
    """

    source_id = "regulatory_us_doj"
    source_name = "US Department of Justice"
    signal_types = ["regulatory_enforcement", "regulatory_doj_action"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape DOJ press releases for Canadian-relevant actions."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            feed = await self.get_rss(_DOJ_RSS_URL)
            if not feed or not feed.get("entries"):
                log.warning("doj_rss_empty")
                return results

            for entry in feed["entries"][:50]:
                result = self._parse_entry(entry, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("doj_scrape_error", error=str(exc))

        log.info("doj_scrape_complete", count=len(results))
        return results

    def _parse_entry(
        self, entry: dict[str, Any], cutoff: datetime
    ) -> ScraperResult | None:
        title = entry.get("title", "")
        if not title or len(title) < 5:
            return None

        description = entry.get("description", "") or entry.get("summary", "")
        link = entry.get("link", "") or entry.get("href", "")

        combined_text = f"{title} {description}".lower()
        if not self._has_canadian_connection(combined_text):
            return None

        pub_date = entry.get("published", "") or entry.get("pubDate", "")
        published_at = self._parse_date(pub_date)

        if published_at and published_at < cutoff:
            return None

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_doj_action",
            raw_company_name=None,
            source_url=link or None,
            signal_value={
                "title": title,
                "description": description[:500],
                "regulator": "US DOJ",
            },
            signal_text=f"DOJ: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["litigation", "ma", "competition"],
            raw_payload={
                "title": title,
                "description": description,
                "link": link,
            },
            confidence_score=0.75,
        )

    @staticmethod
    def _has_canadian_connection(text: str) -> bool:
        return any(marker in text for marker in _CANADIAN_MARKERS)
