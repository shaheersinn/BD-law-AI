"""Tribunals Ontario — LTB, HRTO, and other tribunal decisions."""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

# Tribunals Ontario Open Data (CSV)
_TRIBUNALS_OPEN_DATA = "https://data.ontario.ca/api/3/action/datastore_search?resource_id=e2d9e575-9d1b-4e1f-9a7a-caa7d7a46ac5&limit=100&sort=date desc"


@register
class TribunalsOntarioScraper(BaseScraper):
    source_id = "legal_tribunals_ontario"
    source_name = "Tribunals Ontario (LTB/HRTO/OLT)"
    CATEGORY = "legal"
    signal_types = ["litigation_tribunal_decision"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_TRIBUNALS_OPEN_DATA)
            if resp.status_code != 200:
                return results
            data = resp.json()
            for rec in data.get("result", {}).get("records", []):
                tribunal = rec.get("tribunal", "")
                is_employment = "hrto" in tribunal.lower() or "labour" in tribunal.lower()
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="litigation_tribunal_decision",
                        signal_value={
                            "tribunal": tribunal,
                            "date": rec.get("date"),
                            "applicant": rec.get("applicant_type"),
                        },
                        signal_text=f"{tribunal} decision",
                        published_at=self._parse_date(rec.get("date", "")),
                        practice_area_hints=["employment"] if is_employment else ["administrative"],
                        raw_payload=rec,
                    )
                )
        except Exception as exc:
            log.error("tribunals_ontario_error", error=str(exc))
        return results
