"""Competition Tribunal scraper — consent agreements and orders."""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
log = structlog.get_logger(__name__)

@register
class CompetitionTribunalScraper(BaseScraper):
    source_id = "legal_competition_tribunal"
    source_name = "Competition Tribunal"
    signal_types = ["litigation_competition"]
    rate_limit_rps = 0.1; concurrency = 1; ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results = []
        try:
            resp = await self.get("https://www.ct-tc.gc.ca/CMFiles/whatsnew.xml")
            if resp.status_code != 200: return results
            root = ET.fromstring(resp.text)
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                results.append(ScraperResult(
                    source_id=self.source_id, signal_type="litigation_competition",
                    source_url=(item.findtext("link") or "").strip(),
                    signal_value={"title": title},
                    signal_text=f"Competition Tribunal: {title}",
                    published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                    practice_area_hints=["competition", "ma"], raw_payload={"title": title},
                ))
        except Exception as exc:
            log.error("ct_error", error=str(exc))
        return results
