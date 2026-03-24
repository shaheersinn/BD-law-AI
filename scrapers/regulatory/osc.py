"""OSC enforcement actions and regulatory notices."""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
log = structlog.get_logger(__name__)

@register
class OSCScraper(BaseScraper):
    source_id = "regulatory_osc"
    source_name = "Ontario Securities Commission"
    signal_types = ["regulatory_osc_enforcement", "regulatory_osc_notice"]
    rate_limit_rps = 0.2; concurrency = 1; ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results = []
        feeds = [
            ("https://www.osc.ca/en/rss/enforcement", "regulatory_osc_enforcement"),
            ("https://www.osc.ca/en/rss/news", "regulatory_osc_notice"),
        ]
        for feed_url, sig_type in feeds:
            try:
                resp = await self.get(feed_url)
                if resp.status_code != 200: continue
                root = ET.fromstring(resp.text)
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    results.append(ScraperResult(
                        source_id=self.source_id, signal_type=sig_type,
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=title,
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["securities", "financial_regulatory"],
                        raw_payload={"title": title},
                    ))
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("osc_error", feed=feed_url, error=str(exc))
        return results
