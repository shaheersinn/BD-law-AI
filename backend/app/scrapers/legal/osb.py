"""
app/scrapers/legal/osb.py — Office of the Superintendent of Bankruptcy.

Source: https://www.ic.gc.ca/app/scr/bsf-osb/ins/login.html
        OSB publishes insolvency statistics via open data (CSV/Excel)

What it scrapes:
  - Corporate insolvency filings (CCAA, Division 1 Proposals, Receiverships)
  - Monthly insolvency statistics by province + industry
  - Individual insolvency filings (proxy for economic distress by sector)

Signal types:
  - insolvency_corporate_filing: CCAA, BIA Division 1 Proposal
  - insolvency_receivership: receivership appointment
  - insolvency_stats_spike: statistical spike in sector

Rate limit: 0.1 rps (government open data)
"""

from __future__ import annotations

import csv
import io

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

# OSB open data — corporate insolvency filings
_OSB_CORPORATE_DATA = "https://www.ic.gc.ca/app/scr/bsf-osb/ins/insolvencies-download.html"
_OSB_STATS_CSV = "https://www.ic.gc.ca/app/scr/bsf-osb/ins/statistics/statistics.csv"


@register
class OSBScraper(BaseScraper):
    source_id = "legal_osb"
    source_name = "OSB (Office of the Superintendent of Bankruptcy)"
    CATEGORY = "legal"
    signal_types = ["insolvency_corporate_filing", "insolvency_receivership"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # OSB provides downloadable CSV of recent insolvency filings
            response = await self.get(_OSB_STATS_CSV)
            if response.status_code == 200:
                reader = csv.DictReader(io.StringIO(response.text))
                for row in reader:
                    estate_type = row.get("Estate Type", "").strip()
                    if estate_type.lower() not in ("commercial", "corporation", "corporate"):
                        continue
                    debtor_name = row.get("Debtor Name", "").strip()
                    if not debtor_name:
                        continue
                    filing_type = row.get("Filing Type", "").strip()
                    is_receivership = "receivership" in filing_type.lower()
                    signal_type = (
                        "insolvency_receivership"
                        if is_receivership
                        else "insolvency_corporate_filing"
                    )

                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            raw_company_name=debtor_name,
                            signal_value={
                                "filing_type": filing_type,
                                "filing_date": row.get("Date Filed", ""),
                                "district": row.get("District", ""),
                                "trustee": row.get("Trustee Name", ""),
                                "estate_number": row.get("Estate Number", ""),
                            },
                            signal_text=f"Insolvency: {debtor_name} — {filing_type}",
                            published_at=self._parse_date(row.get("Date Filed", "")),
                            practice_area_hints=["insolvency", "banking", "employment"],
                            raw_payload=dict(row),
                        )
                    )
        except Exception as exc:
            log.error("osb_error", error=str(exc))
        log.info("osb_scrape_complete", total=len(results))
        return results
