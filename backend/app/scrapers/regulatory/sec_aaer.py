"""
app/scrapers/regulatory/sec_aaer.py — SEC AAER scraper.

Data source: https://www.sec.gov/litigation/admin.shtml
Approach: RSS feed preferred, HTML fallback; filter for Canadian companies
Signal value: HIGH — SEC AAER predicts securities litigation mandates
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SEC_AAER_URL = "https://www.sec.gov/litigation/admin.shtml"
_SEC_AAER_RSS_URL = "https://www.sec.gov/rss/litigation/admin.xml"

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
    "tsx",
    "tsx-v",
    "tsxv",
]


@register
class SECAAERScraper(BaseScraper):
    """
    SEC Accounting and Auditing Enforcement Releases scraper.

    Scrapes SEC AAER and filters for Canadian companies.
    """

    source_id = "regulatory_sec_aaer"
    source_name = "SEC Accounting and Auditing Enforcement Releases"
    signal_types = ["regulatory_enforcement", "regulatory_sec_aaer"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.1
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape SEC AAER for Canadian-relevant releases."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            rss_results = await self._scrape_rss(cutoff)
            if rss_results:
                results.extend(rss_results)
            else:
                html_results = await self._scrape_html(cutoff)
                results.extend(html_results)
        except Exception as exc:
            log.error("sec_aaer_scrape_error", error=str(exc))

        log.info("sec_aaer_scrape_complete", count=len(results))
        return results

    async def _scrape_rss(self, cutoff: datetime) -> list[ScraperResult]:
        feed = await self.get_rss(_SEC_AAER_RSS_URL)
        if not feed or not feed.get("entries"):
            return []

        results: list[ScraperResult] = []
        for entry in feed["entries"][:50]:
            title = entry.get("title", "")
            description = entry.get("description", "") or entry.get("summary", "")
            link = entry.get("link", "") or entry.get("href", "")

            if not title or len(title) < 5:
                continue

            combined = f"{title} {description}".lower()
            if not self._has_canadian_connection(combined):
                continue

            pub_date = entry.get("published", "") or entry.get("pubDate", "")
            published_at = self._parse_date(pub_date)

            if published_at and published_at < cutoff:
                continue

            results.append(
                ScraperResult(
                    source_id=self.source_id,
                    signal_type="regulatory_sec_aaer",
                    raw_company_name=None,
                    source_url=link or None,
                    signal_value={
                        "title": title,
                        "description": description[:500],
                        "regulator": "SEC",
                    },
                    signal_text=f"SEC AAER: {title}",
                    published_at=published_at or self._now_utc(),
                    practice_area_hints=["securities", "litigation", "regulatory"],
                    raw_payload={
                        "title": title,
                        "description": description,
                        "link": link,
                    },
                    confidence_score=0.80,
                )
            )
        return results

    async def _scrape_html(self, cutoff: datetime) -> list[ScraperResult]:
        resp = await self.get(
            _SEC_AAER_URL,
            headers={"Accept": "text/html"},
        )
        if resp.status_code != 200:
            log.warning("sec_aaer_fetch_failed", status=resp.status_code)
            return []

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[ScraperResult] = []

        items = (
            soup.select("table tbody tr")
            or soup.find_all("li")
            or soup.find_all("div", class_="views-row")
        )

        for item in items[:50]:
            result = self._parse_html_item(item, cutoff)
            if result:
                results.append(result)

        return results

    def _parse_html_item(self, item: Any, cutoff: datetime) -> ScraperResult | None:
        link_el = item.find("a", href=True)
        title = self.safe_text(link_el or item)
        if not title or len(title) < 5:
            return None

        combined = title.lower()
        if not self._has_canadian_connection(combined):
            return None

        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"https://www.sec.gov{href}"

        date_el = item.find("time") or item.find(class_=lambda c: c and "date" in str(c).lower())
        published_at = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_sec_aaer",
            raw_company_name=None,
            source_url=source_url,
            signal_value={"title": title, "regulator": "SEC"},
            signal_text=f"SEC AAER: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=["securities", "litigation", "regulatory"],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.80,
        )

    @staticmethod
    def _has_canadian_connection(text: str) -> bool:
        return any(marker in text for marker in _CANADIAN_MARKERS)
