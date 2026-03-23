"""
Corporations Canada scraper — business registry changes.
Source: https://ised-isde.canada.ca/cc/lgcy/fdrlCrpSrch.html
Signals: company_registration, company_dissolution, name_change
"""
from __future__ import annotations
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

@register
class CorpsCanadaScraper(BaseScraper):
    source_id = "corporate_corps_canada"
    source_name = "Corporations Canada Registry"
    signal_types = ["company_dissolution", "company_registration"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        # Corporations Canada provides bulk data download via Open Government
        # URL: https://open.canada.ca/data/en/dataset/...
        # We poll their open data CSV for recent dissolutions
        results: list[ScraperResult] = []
        try:
            # Open Government bulk data — corporations dissolved this month
            url = "https://open.canada.ca/data/en/dataset/2ef5c509-9c60-4ca4-a84b-18dd3d250b69/resource/3a2fd9e7-bf5e-4b14-b9e8-4cb0d3d36af5/download"
            response = await self.get(url)
            if response.status_code != 200:
                return results
            lines = response.text.strip().split("\n")
            headers = lines[0].split(",") if lines else []
            for line in lines[1:200]:  # Recent 200 records
                parts = line.split(",")
                if len(parts) < len(headers):
                    continue
                row = dict(zip(headers, parts))
                status = row.get("Status", "").strip()
                if status.lower() not in ("dissolved", "ceased"):
                    continue
                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type="company_dissolution",
                    raw_company_name=row.get("Legal Name", "").strip(),
                    raw_company_id=row.get("Corporation Number", "").strip(),
                    signal_value={"status": status, "date": row.get("Date Status Changed", "")},
                    signal_text=f"Corporation dissolved: {row.get('Legal Name', '')}",
                    practice_area_hints=["insolvency", "corporate"],
                    raw_payload=row,
                ))
        except Exception as exc:
            log.error("corps_canada_error", error=str(exc))
        return results
