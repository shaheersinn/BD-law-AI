"""Office of the Privacy Commissioner — PIPEDA/privacy investigations."""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
log = structlog.get_logger(__name__)

@register
class OPCScraper(BaseScraper):
    source_id = "regulatory_opc"
    source_name = "Office of the Privacy Commissioner of Canada"
    signal_types = ["regulatory_privacy_finding", "regulatory_privacy_investigation"]
    rate_limit_rps = 0.1; concurrency = 1; ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results = []
        try:
            resp = await self.get("https://www.priv.gc.ca/en/rss/investigations.xml")
            if resp.status_code != 200: return results
            root = ET.fromstring(resp.text)
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                results.append(ScraperResult(
                    source_id=self.source_id, signal_type="regulatory_privacy_finding",
                    source_url=(item.findtext("link") or "").strip(),
                    signal_value={"title": title},
                    signal_text=title,
                    published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                    practice_area_hints=["privacy", "technology"],
                    raw_payload={"title": title},
                ))
        except Exception as exc:
            log.error("opc_error", error=str(exc))
        return results
