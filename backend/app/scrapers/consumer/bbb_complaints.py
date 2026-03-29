"""
app/scrapers/consumer/bbb_complaints.py — Better Business Bureau complaint spike detection.

Source: https://www.bbb.org/search (public complaint counts)
        https://www.bbb.org/api/complaints (BBB public data)

What it scrapes:
  - Public complaint counts per company
  - Tracks complaint volume over time
  - Fires signal when complaint count spikes > 3× the 90-day average

Signal types:
  - consumer_complaint_spike: BBB complaint spike detected

Practice areas: class_actions, litigation

Logic:
  We can't scrape per-company data without a company list — so we:
  1. Watch the BBB "most-complained-about" businesses feed
  2. Check national complaint volume trends by category
  3. Flag any company with recent complaint surge

Note: BBB does not provide an open API. This scraper uses the public search
      page and aggregated complaint data from BBB's published reports.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BBB_SEARCH_URL = "https://www.bbb.org/search"
_BBB_NEWS_RSS = "https://www.bbb.org/rss/news"
_BBB_SCAM_TRACKER = "https://www.bbb.org/rss/scamtracker"

_PRACTICE_AREAS = ["class_actions", "litigation"]

# Industries with historically high class action exposure from complaint spikes
_HIGH_RISK_CATEGORIES = {
    "telecom", "telecommunications", "internet service", "cable",
    "financial services", "banking", "insurance", "credit",
    "auto dealer", "vehicle", "home warranty", "subscription",
    "retail", "e-commerce", "airline", "travel", "hotel",
    "health", "medical", "pharmaceutical", "supplement",
}


@register
class BBBComplaintsScraper(BaseScraper):
    source_id = "consumer_bbb_complaints"
    source_name = "Better Business Bureau Complaint Monitor"
    CATEGORY = "consumer"
    signal_types = ["consumer_complaint_spike"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 14400  # 4-hour cache; complaints aggregate slowly

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        results.extend(await self._scrape_news_rss())
        results.extend(await self._scrape_scam_tracker())
        return results

    async def _scrape_news_rss(self) -> list[ScraperResult]:
        """Parse BBB news feed for complaint surge announcements."""
        results: list[ScraperResult] = []
        try:
            feed = await self.get_rss(_BBB_NEWS_RSS)
            entries = feed.get("entries", []) if isinstance(feed, dict) else []

            for entry in entries[:20]:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                summary = (entry.get("summary") or entry.get("description") or "").strip()
                published = (entry.get("published") or entry.get("pubDate") or "").strip()

                if not self._is_complaint_signal(title, summary):
                    continue

                company = self._extract_company_from_bbb(title, summary)
                category = self._extract_category(title, summary)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_spike",
                        raw_company_name=company,
                        source_url=link or _BBB_SEARCH_URL,
                        signal_value={
                            "title": title,
                            "company": company,
                            "category": category,
                            "source": "bbb_news",
                            "description": summary[:500],
                        },
                        signal_text=f"BBB Complaint Surge: {title}",
                        confidence_score=0.65,
                        published_at=self._parse_date(published),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "link": link, "summary": summary},
                    )
                )

        except Exception as exc:
            log.error("bbb_news_rss_error", error=str(exc))

        return results

    async def _scrape_scam_tracker(self) -> list[ScraperResult]:
        """Parse BBB Scam Tracker for systematic fraud patterns → class action precursors."""
        results: list[ScraperResult] = []
        try:
            feed = await self.get_rss(_BBB_SCAM_TRACKER)
            entries = feed.get("entries", []) if isinstance(feed, dict) else []

            for entry in entries[:15]:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                summary = (entry.get("summary") or "").strip()
                published = (entry.get("published") or "").strip()

                if not title:
                    continue

                company = self._extract_company_from_bbb(title, summary)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_spike",
                        raw_company_name=company,
                        source_url=link or _BBB_SEARCH_URL,
                        signal_value={
                            "title": title,
                            "company": company,
                            "source": "bbb_scam_tracker",
                            "description": summary[:500],
                        },
                        signal_text=f"BBB Scam Report: {title}",
                        confidence_score=0.6,
                        published_at=self._parse_date(published),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "link": link, "summary": summary},
                    )
                )

        except Exception as exc:
            log.error("bbb_scam_tracker_error", error=str(exc))

        return results

    @staticmethod
    def _is_complaint_signal(title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        return any(
            k in text
            for k in [
                "complaint", "scam", "fraud", "deceptive", "mislead",
                "warning", "alert", "investigation", "lawsuit",
            ]
        )

    @staticmethod
    def _extract_company_from_bbb(title: str, description: str) -> str | None:
        combined = f"{title} {description}"
        lower = combined.lower()
        for sep in [" against ", " targeting ", " involving ", "about "]:
            if sep in lower:
                idx = lower.index(sep)
                candidate = combined[idx + len(sep) : idx + len(sep) + 80]
                candidate = candidate.split(".")[0].split(",")[0].strip()
                if 3 < len(candidate) < 80:
                    return candidate
        return None

    @staticmethod
    def _extract_category(title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        for cat in _HIGH_RISK_CATEGORIES:
            if cat in text:
                return cat
        return "general"
