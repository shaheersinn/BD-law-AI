"""
LMIA positive employer list scraper.

Source: ESDC LMIA Positive Employer List (Open Canada bulk CSV).
Signal: immigration_lmia_spike — fires when a watchlist company first appears
or shows 3x YoY increase in LMIA count.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_LMIA_DATASET_URL = (
    "https://open.canada.ca/data/dataset/90bdfc09-2ff7-46d8-89dc-cbdd2f2bea50/"
    "resource/download/lmia-employers.csv"
)

_YOY_SPIKE_MULTIPLIER = 3


@register
class LMIAScraper(BaseScraper):
    source_id = "immigration_lmia"
    source_name = "ESDC LMIA Positive Employer List"
    signal_types = ["immigration_lmia_spike"]
    CATEGORY = "immigration"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_LMIA_DATASET_URL)
            if resp.status_code != 200:
                log.warning("lmia_http_error", status=resp.status_code)
                return results

            results.extend(self._parse_lmia_csv(resp.text))
        except Exception as exc:
            log.error("lmia_scrape_error", error=str(exc))

        return results

    def _parse_lmia_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        # Group by employer to detect spikes
        employer_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        rows_list = []
        for row in reader:
            rows_list.append(row)
            employer = (row.get("Employer", "") or row.get("employer_name", "") or "").strip()
            year = (row.get("Year", "") or row.get("year", "") or "").strip()
            if employer and year:
                try:
                    positions = int(row.get("Positions", "") or row.get("positions", "") or "1")
                except ValueError:
                    positions = 1
                employer_counts[employer][year] += positions

        # Detect spikes and first appearances
        for employer, year_data in employer_counts.items():
            years = sorted(year_data.keys())
            if not years:
                continue

            latest_year = years[-1]
            latest_count = year_data[latest_year]

            signal_reason = None
            if len(years) == 1:
                signal_reason = "first_appearance"
            elif len(years) >= 2:
                prev_year = years[-2]
                prev_count = year_data[prev_year]
                if prev_count > 0 and latest_count >= prev_count * _YOY_SPIKE_MULTIPLIER:
                    signal_reason = "yoy_spike"

            if signal_reason:
                province = ""
                for row in rows_list:
                    if (row.get("Employer", "") or row.get("employer_name", "")).strip() == employer:
                        province = (row.get("Province/Territory", "") or row.get("province", "") or "").strip()
                        break

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="immigration_lmia_spike",
                        raw_company_name=employer,
                        source_url="https://open.canada.ca/data/en/dataset/90bdfc09-2ff7-46d8-89dc-cbdd2f2bea50",
                        signal_value={
                            "employer": employer,
                            "province": province,
                            "latest_year": latest_year,
                            "latest_count": latest_count,
                            "reason": signal_reason,
                            "year_data": dict(year_data),
                        },
                        signal_text=(
                            f"LMIA {signal_reason}: {employer} — "
                            f"{latest_count} positions in {latest_year}"
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Corporate Immigration", "Employment & Labour"],
                        raw_payload={"employer": employer, "year_data": dict(year_data)},
                        confidence_score=0.80 if signal_reason == "yoy_spike" else 0.70,
                    )
                )

        return results
