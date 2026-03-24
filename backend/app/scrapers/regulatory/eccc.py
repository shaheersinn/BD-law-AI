"""Environment and Climate Change Canada — enforcement actions."""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class ECCCScraper(BaseScraper):
    source_id = "regulatory_eccc"
    source_name = "Environment and Climate Change Canada (ECCC)"
    CATEGORY = "regulatory"
    signal_types = ["regulatory_environmental_enforcement"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(
                "https://www.canada.ca/en/environment-climate-change/news/rss.xml"
            )
            if resp.status_code != 200:
                return results
            root = ET.fromstring(resp.text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                title_lower = title.lower()
                if not any(
                    k in title_lower
                    for k in ["penalty", "conviction", "fine", "violation", "enforcement"]
                ):
                    continue
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="regulatory_environmental_enforcement",
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=title,
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["environmental", "energy", "mining"],
                        raw_payload={"title": title},
                    )
                )
        except Exception as exc:
            log.error("eccc_error", error=str(exc))
        return results
