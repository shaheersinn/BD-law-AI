"""Federal Court of Canada decisions scraper."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class FederalCourtScraper(BaseScraper):
    source_id = "legal_federal_court"
    source_name = "Federal Court of Canada"
    CATEGORY = "legal"
    signal_types = ["litigation_judgment"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get("https://www.fct-cf.gc.ca/rss/decisions-en.xml")
            if resp.status_code != 200:
                return results
            root = ET.fromstring(resp.text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="litigation_judgment",
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=f"Federal Court: {title}",
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["litigation", "immigration", "administrative"],
                        raw_payload={"title": title},
                    )
                )
        except Exception as exc:
            log.error("federal_court_error", error=str(exc))
        return results
