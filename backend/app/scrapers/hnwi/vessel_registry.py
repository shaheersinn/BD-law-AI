"""
Transport Canada vessel registry scraper.

Source: Transport Canada Vessel Registry bulk data + query service.
Signal: vessel_registry_change — fires when large vessels (>24m) registered
to individuals show transfers, new mortgages, or liens.
"""

from __future__ import annotations

import csv
import io
import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TC_VESSEL_QUERY_URL = "https://wwwapps.tc.gc.ca/Saf-Sec-Sur/4/vrqs-srib/"
_TC_VESSEL_BULK_URL = (
    "https://open.canada.ca/data/dataset/1be50ad8-f90c-4e24-a436-0af55c510eea/"
    "resource/download/vessel-registry.csv"
)

_MIN_LENGTH_METRES = 24


@register
class VesselRegistryScraper(BaseScraper):
    source_id = "hnwi_vessel_registry"
    source_name = "Transport Canada Vessel Registry"
    signal_types = ["vessel_registry_change"]
    CATEGORY = "hnwi"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_TC_VESSEL_BULK_URL)
            if resp.status_code != 200:
                log.warning("vessel_registry_http_error", status=resp.status_code)
                return results

            results.extend(self._parse_vessel_csv(resp.text))
        except Exception as exc:
            log.error("vessel_registry_error", error=str(exc))

        return results

    def _parse_vessel_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                # Filter for large vessels
                length_str = row.get("Length (m)", "") or row.get("Length", "") or "0"
                try:
                    length = float(re.sub(r"[^\d.]", "", length_str) or "0")
                except ValueError:
                    length = 0.0

                if length < _MIN_LENGTH_METRES:
                    continue

                owner = (row.get("Owner", "") or row.get("Registered Owner", "") or "").strip()
                if not owner:
                    continue

                # Look for individual owners (not corporations)
                owner_lower = owner.lower()
                if any(
                    corp in owner_lower
                    for corp in ["inc", "ltd", "corp", "llc", "company", "holdings"]
                ):
                    continue

                vessel_name = (row.get("Vessel Name", "") or row.get("Name", "") or "").strip()
                official_number = (row.get("Official Number", "") or "").strip()

                # Check for recent changes (mortgages, liens, transfers)
                change_indicators = []
                mortgage = row.get("Mortgage", "") or row.get("Mortgages", "") or ""
                if mortgage.strip():
                    change_indicators.append("mortgage")

                lien = row.get("Lien", "") or row.get("Liens", "") or ""
                if lien.strip():
                    change_indicators.append("lien")

                status = (row.get("Status", "") or "").strip().lower()
                if "transfer" in status:
                    change_indicators.append("transfer")

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="vessel_registry_change",
                        raw_company_name=owner,
                        source_url=f"{_TC_VESSEL_QUERY_URL}?on={official_number}" if official_number else _TC_VESSEL_QUERY_URL,
                        signal_value={
                            "vessel_name": vessel_name,
                            "official_number": official_number,
                            "owner": owner,
                            "length_m": length,
                            "change_indicators": change_indicators,
                        },
                        signal_text=(
                            f"Vessel '{vessel_name}' ({length}m) owned by {owner}"
                            + (f" — {', '.join(change_indicators)}" if change_indicators else "")
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Wills / Estates", "Banking & Finance"],
                        raw_payload=dict(row),
                        confidence_score=0.75 if change_indicators else 0.60,
                    )
                )
            except Exception as exc:
                log.warning("vessel_row_parse_error", error=str(exc))

        return results
