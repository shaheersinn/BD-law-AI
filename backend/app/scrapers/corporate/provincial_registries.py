"""
Provincial business registries scraper.
Sources: Ontario, BC, Alberta business registry open data (where available)
Signals: company_registration, company_dissolution, company_name_change
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


@register
class ProvincialRegistriesScraper(BaseScraper):
    source_id = "corporate_provincial_registries"
    source_name = "Provincial Business Registries (ON/BC/AB)"
    signal_types = ["company_dissolution", "company_registration"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    # Ontario Business Registry open data
    _ON_DISSOLUTION_URL = "https://data.ontario.ca/api/3/action/datastore_search?resource_id=c834e4c7-e9c2-4d33-a00e-6df92b50a8e3&limit=100&sort=date_of_dissolution+desc"

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            response = await self.get(self._ON_DISSOLUTION_URL)
            if response.status_code == 200:
                data = response.json()
                records = data.get("result", {}).get("records", [])
                for rec in records:
                    company_name = rec.get("company_name", "")
                    diss_date = rec.get("date_of_dissolution", "")
                    if not company_name:
                        continue
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="company_dissolution",
                            raw_company_name=company_name,
                            raw_company_id=rec.get("corporation_number"),
                            signal_value={
                                "dissolution_date": diss_date,
                                "province": "ON",
                                "status": rec.get("status"),
                            },
                            signal_text=f"Ontario corporation dissolved: {company_name}",
                            published_at=self._parse_date(diss_date),
                            practice_area_hints=["insolvency", "corporate"],
                            raw_payload=rec,
                        )
                    )
        except Exception as exc:
            log.error("provincial_registries_error", error=str(exc))
        return results
