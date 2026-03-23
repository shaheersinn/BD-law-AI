"""
app/scrapers/geo/statscan.py — Statistics Canada economic indicators.

Source: https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload?pid=...
        Statistics Canada Web Data Service (WDS) API

Key tables for ORACLE:
  35-10-0027-01  — Court cases and charges, by type of offence
  14-10-0017-01  — Job vacancies by industry (layoff leading indicator)
  11-10-0007-01  — Consumer Price Index (economic stress)
  33-10-0006-01  — Survey on Financing of SMEs (credit tightening)

Signal types:
  geo_statscan_court_volume     — court filing volume spike by province
  geo_statscan_employment_stress — unemployment spike in sector
  geo_statscan_insolvency_leading — SME financing stress indicator

Rate: 0.1 rps (Stats Canada WDS allows bulk downloads)
"""
from __future__ import annotations
import csv
import io
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_STATSCAN_WDS = "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload"
_STATSCAN_API = "https://www150.statcan.gc.ca/t1/tbl1/en/dtbl/downloadTbl/csvDownload?pid="


_TABLES = [
    ("3510002701", "geo_statscan_court_volume", ["litigation", "class_actions"],
     "Court cases by type of offence"),
    ("1410001701", "geo_statscan_employment_stress", ["employment"],
     "Job vacancies by industry"),
]


@register
class StatsCanScraper(BaseScraper):
    source_id = "geo_statscan"
    source_name = "Statistics Canada (WDS)"
    signal_types = ["geo_statscan_court_volume", "geo_statscan_employment_stress"]
    rate_limit_rps = 0.1
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 60.0
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for pid, signal_type, hints, description in _TABLES:
            try:
                # Stats Canada provides direct CSV download
                response = await self.get(f"{_STATSCAN_API}{pid}")
                if response.status_code != 200:
                    log.warning("statscan_non200", pid=pid, status=response.status_code)
                    continue

                # Parse CSV — only take most recent rows
                reader = csv.DictReader(io.StringIO(response.text))
                rows = list(reader)
                if not rows:
                    continue

                recent = rows[-12:]  # Last 12 periods
                for row in recent:
                    if not any(row.values()):
                        continue
                    results.append(ScraperResult(
                        source_id=self.source_id,
                        signal_type=signal_type,
                        signal_value={
                            "table_pid": pid,
                            "description": description,
                            "period": row.get("REF_DATE") or row.get("Date", ""),
                            "value": row.get("VALUE") or row.get("Value", ""),
                            "geography": row.get("GEO") or row.get("Geography", ""),
                            "indicator": row.get("Statistics") or row.get("Indicator", ""),
                        },
                        signal_text=f"Stats Canada {description}: {row.get('VALUE', '')} ({row.get('REF_DATE', '')})",
                        published_at=self._parse_date(row.get("REF_DATE") or row.get("Date", "")),
                        practice_area_hints=hints,
                        raw_payload=dict(row),
                        confidence_score=0.9,
                    ))
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("statscan_table_error", pid=pid, error=str(exc))

        return results
