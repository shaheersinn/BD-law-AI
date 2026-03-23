"""
IAAC (Impact Assessment Agency of Canada) scraper.
Source: https://iaac-aeic.gc.ca/050/evaluations/index?culture=en-CA
Signals: regulatory_environmental_assessment
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

@register
class IAACscraper(BaseScraper):
    source_id = "corporate_iaac"
    source_name = "Impact Assessment Agency of Canada"
    signal_types = ["regulatory_environmental_assessment"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # IAAC has open data on active project assessments
            url = "https://iaac-aeic.gc.ca/050/evaluations/rss?culture=en-CA"
            response = await self.get(url)
            if response.status_code != 200:
                return results
            root = ET.fromstring(response.text)
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type="regulatory_environmental_assessment",
                    source_url=(item.findtext("link") or "").strip(),
                    signal_value={"title": title, "date": (item.findtext("pubDate") or "")},
                    signal_text=f"IAAC Assessment: {title}",
                    published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                    practice_area_hints=["environmental", "mining", "infrastructure"],
                    raw_payload={"title": title},
                ))
        except Exception as exc:
            log.error("iaac_error", error=str(exc))
        return results
