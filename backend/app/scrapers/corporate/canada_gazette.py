"""
app/scrapers/corporate/canada_gazette.py — Canada Gazette scraper.

Source: https://canadagazette.gc.ca/rp-pr/p2/index-eng.html (Part II — Regulations)
        https://canadagazette.gc.ca/rp-pr/p1/index-eng.html (Part I — Notices)
        RSS feeds available at both parts.

What it scrapes:
  - Regulatory amendments affecting specific industries
  - Notices of proposed rule changes
  - Final regulations with compliance deadlines

Signal types:
  - regulatory_gazette_notice: proposed rule change
  - regulatory_gazette_final: final regulation published

Rate limit: 0.1 rps (government site, RSS preferred)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_GAZETTE_RSS_P1 = "https://canadagazette.gc.ca/rss/p1.xml"
_GAZETTE_RSS_P2 = "https://canadagazette.gc.ca/rss/p2.xml"

_LEGAL_KEYWORDS = [
    "act",
    "regulation",
    "compliance",
    "penalty",
    "enforcement",
    "prohibition",
    "financial",
    "banking",
    "environment",
    "privacy",
    "competition",
    "tax",
    "employment",
    "securities",
    "disclosure",
    "registration",
    "licensing",
]


@register
class CanadaGazetteScraper(BaseScraper):
    source_id = "corporate_canada_gazette"
    CATEGORY = "corporate"
    source_name = "Canada Gazette"
    signal_types = ["regulatory_gazette_notice", "regulatory_gazette_final"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400  # 24 hours — gazette doesn't change minute-to-minute

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for feed_url, signal_type in [
            (_GAZETTE_RSS_P1, "regulatory_gazette_notice"),
            (_GAZETTE_RSS_P2, "regulatory_gazette_final"),
        ]:
            try:
                response = await self.get(feed_url)
                if response.status_code != 200:
                    continue
                items = self._parse_rss(response.text)
                for item in items:
                    title = item.get("title", "").lower()
                    if not any(kw in title for kw in _LEGAL_KEYWORDS):
                        continue
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            source_url=item.get("link"),
                            signal_value={
                                "title": item.get("title"),
                                "pub_date": item.get("pub_date"),
                                "feed": feed_url,
                            },
                            signal_text=item.get("title"),
                            published_at=self._parse_date(item.get("pub_date")),
                            practice_area_hints=self._hints(item.get("title", "")),
                            raw_payload=item,
                        )
                    )
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("gazette_feed_error", feed=feed_url, error=str(exc))
        return results

    def _parse_rss(self, xml_text: str) -> list[dict]:
        items = []
        try:
            root = ET.fromstring(xml_text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                items.append(
                    {
                        "title": (item.findtext("title") or "").strip(),
                        "link": (item.findtext("link") or "").strip(),
                        "description": (item.findtext("description") or "").strip(),
                        "pub_date": (item.findtext("pubDate") or "").strip(),
                    }
                )
        except ET.ParseError as e:
            log.warning("gazette_rss_parse_error", error=str(e))
        return items

    def _hints(self, title: str) -> list[str]:
        title_lower = title.lower()
        hints = []
        mappings = {
            "financial": ["banking"],
            "privacy": ["privacy"],
            "competition": ["competition"],
            "tax": ["tax"],
            "employment": ["employment"],
            "environment": ["environmental"],
            "securities": ["securities"],
            "immigration": ["immigration"],
        }
        for keyword, areas in mappings.items():
            if keyword in title_lower:
                hints.extend(areas)
        return hints
