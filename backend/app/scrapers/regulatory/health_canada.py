"""Health Canada recalls, warnings and enforcement."""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class HealthCanadaScraper(BaseScraper):
    source_id = "regulatory_health_canada"
    source_name = "Health Canada Recalls and Advisories"
    CATEGORY = "regulatory"
    signal_types = ["regulatory_health_recall", "regulatory_health_enforcement"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results = []
        try:
            resp = await self.get(
                "https://healthycanadians.gc.ca/recall-alert-rappel-avis/api/recent/en"
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", {}).get("ALL", [])[:50]:
                    title = item.get("title", "").strip()
                    company = item.get("organization", "").strip()
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="regulatory_health_recall",
                            raw_company_name=company or None,
                            source_url=item.get("url"),
                            signal_value={
                                "title": title,
                                "category": item.get("category"),
                                "date": item.get("date_published"),
                            },
                            signal_text=f"Health Canada: {title}"
                            + (f" — {company}" if company else ""),
                            published_at=self._parse_date(item.get("date_published", "")),
                            practice_area_hints=["health_life_sciences", "product_liability"],
                            raw_payload=item,
                        )
                    )
        except Exception as exc:
            log.error("health_canada_error", error=str(exc))
        return results
