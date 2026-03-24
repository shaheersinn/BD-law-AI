"""
CIRO (formerly IIROC) scraper — investment dealer regulatory actions.
Source: https://www.ciro.ca/news-and-publications/disciplinary-proceedings
Signals: regulatory_ciro_proceeding, regulatory_ciro_settlement
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

@register
class CIROScraper(BaseScraper):
    source_id = "corporate_ciro"
    source_name = "CIRO (Investment Industry Regulatory Organization)"
    signal_types = ["regulatory_ciro_proceeding", "regulatory_ciro_settlement"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # CIRO publishes disciplinary decisions via press release RSS
            feeds = [
                "https://www.ciro.ca/rss/disciplinary-proceedings",
                "https://www.ciro.ca/rss/news",
            ]
            for feed in feeds:
                try:
                    resp = await self.get(feed)
                    if resp.status_code != 200:
                        continue
                    root = ET.fromstring(resp.text)
                    for item in root.iter("item"):
                        title = (item.findtext("title") or "").strip()
                        title_lower = title.lower()
                        is_settlement = "settlement" in title_lower or "penalty" in title_lower
                        signal_type = "regulatory_ciro_settlement" if is_settlement else "regulatory_ciro_proceeding"
                        results.append(ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            source_url=(item.findtext("link") or "").strip(),
                            signal_value={"title": title},
                            signal_text=title,
                            published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                            practice_area_hints=["securities", "financial_regulatory"],
                            raw_payload={"title": title},
                        ))
                    await self._rate_limit_sleep()
                except Exception:
                    continue
        except Exception as exc:
            log.error("ciro_error", error=str(exc))
        return results
