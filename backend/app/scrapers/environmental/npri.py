"""
NPRI pollution spike scraper.

Source: Environment Canada NPRI Open Data (annual CSV/Excel).
Signal: npri_pollution_spike — fires when watchlist companies show > 50% YoY
increase in pollutant releases (compliance crisis ahead).
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_NPRI_DATA_URL = (
    "https://open.canada.ca/data/en/dataset/"
    "40e01423-7728-429c-ac9d-2954571b9341/resource/download/npri-releases.csv"
)

_YOY_SPIKE_THRESHOLD = 0.50  # 50% increase


@register
class NPRIScraper(BaseScraper):
    source_id = "environmental_npri"
    source_name = "NPRI Pollution Data"
    signal_types = ["npri_pollution_spike"]
    CATEGORY = "environmental"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_NPRI_DATA_URL)
            if resp.status_code != 200:
                log.warning("npri_http_error", status=resp.status_code)
                return results

            results.extend(self._parse_npri_csv(resp.text))
        except Exception as exc:
            log.error("npri_scrape_error", error=str(exc))

        return results

    def _parse_npri_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        # Group releases by facility/company and year
        facility_releases: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        facility_info: dict[str, dict[str, str]] = {}

        for row in reader:
            try:
                facility = (
                    row.get("FacilityName", "") or row.get("Facility Name", "") or ""
                ).strip()
                company = (row.get("CompanyName", "") or row.get("Company Name", "") or "").strip()
                year = (row.get("ReportingYear", "") or row.get("Reporting Year", "") or "").strip()
                quantity_str = row.get("TotalRelease", "") or row.get("Total Release", "") or "0"

                key = company or facility
                if not key or not year:
                    continue

                try:
                    quantity = float(quantity_str.replace(",", ""))
                except ValueError:
                    continue

                facility_releases[key][year] += quantity
                if key not in facility_info:
                    facility_info[key] = {
                        "facility": facility,
                        "company": company,
                        "province": (row.get("Province", "") or "").strip(),
                        "city": (row.get("City", "") or "").strip(),
                    }
            except Exception as exc:
                log.warning("npri_row_error", error=str(exc))

        # Detect YoY spikes
        for key, year_data in facility_releases.items():
            years = sorted(year_data.keys())
            if len(years) < 2:
                continue

            latest_year = years[-1]
            prev_year = years[-2]
            latest_total = year_data[latest_year]
            prev_total = year_data[prev_year]

            if prev_total <= 0:
                continue

            yoy_change = (latest_total - prev_total) / prev_total

            if yoy_change >= _YOY_SPIKE_THRESHOLD:
                info = facility_info.get(key, {})
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="npri_pollution_spike",
                        raw_company_name=info.get("company") or key,
                        source_url="https://www.canada.ca/en/services/environment/pollution-waste-management/national-pollutant-release-inventory.html",
                        signal_value={
                            "facility": info.get("facility", key),
                            "company": info.get("company", key),
                            "province": info.get("province", ""),
                            "latest_year": latest_year,
                            "latest_total_kg": latest_total,
                            "previous_total_kg": prev_total,
                            "yoy_change_pct": round(yoy_change * 100, 1),
                        },
                        signal_text=(
                            f"NPRI spike: {key} — releases up "
                            f"{round(yoy_change * 100, 1)}% YoY "
                            f"({int(prev_total)} → {int(latest_total)} kg)"
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Environmental"],
                        raw_payload={
                            "key": key,
                            "year_data": dict(year_data),
                        },
                        confidence_score=0.78,
                    )
                )

        return results
