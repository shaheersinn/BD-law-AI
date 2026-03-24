"""
Bank of Canada scraper — rate decisions and financial system alerts.
Source: https://www.bankofcanada.ca/rss/ (RSS feeds)
Signals: monetary_policy_rate_change, financial_system_alert
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BOC_RSS_FEEDS = [
    ("https://www.bankofcanada.ca/rss/press-releases/", "monetary_policy_rate_change"),
    ("https://www.bankofcanada.ca/rss/publications/", "financial_system_alert"),
]


@register
class BankOfCanadaScraper(BaseScraper):
    source_id = "corporate_bank_of_canada"
    source_name = "Bank of Canada"
    signal_types = ["monetary_policy_rate_change", "financial_system_alert"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for feed_url, default_type in _BOC_RSS_FEEDS:
            try:
                response = await self.get(feed_url)
                if response.status_code != 200:
                    continue
                root = ET.fromstring(response.text)  # nosec B314 — trusted government/news RSS source
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    title_lower = title.lower()
                    is_rate = any(
                        k in title_lower for k in ["rate", "policy", "overnight", "basis point"]
                    )
                    signal_type = "monetary_policy_rate_change" if is_rate else default_type
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            source_url=(item.findtext("link") or "").strip(),
                            signal_value={
                                "title": title,
                                "date": (item.findtext("pubDate") or "").strip(),
                            },
                            signal_text=title,
                            published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                            practice_area_hints=["banking", "insolvency", "financial_regulatory"],
                            raw_payload={"title": title},
                        )
                    )
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("boc_feed_error", feed=feed_url, error=str(exc))
        return results
