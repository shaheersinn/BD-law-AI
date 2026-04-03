"""
CRA Charities director change scraper.

Source: CRA Charities Listings bulk data (T3010 annual filings).
Signal: hnwi_foundation_director_change — fires when private foundations
with assets > $5M show director changes or grants > $1M.
"""

from __future__ import annotations

import csv
import io

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CRA_CHARITIES_SEARCH_URL = "https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/dsplyBscSrch"
_CRA_CHARITIES_BULK_URL = (
    "https://open.canada.ca/data/dataset/f4cad712-4382-4184-93b3-4c39b370dcb0/"
    "resource/download/t3010-charities.csv"
)

_ASSET_THRESHOLD = 5_000_000  # $5M
_GRANT_THRESHOLD = 1_000_000  # $1M


@register
class CRACharitiesScraper(BaseScraper):
    source_id = "hnwi_cra_charities"
    source_name = "CRA Charities Listings"
    signal_types = ["hnwi_foundation_director_change"]
    CATEGORY = "hnwi"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_CRA_CHARITIES_BULK_URL)
            if resp.status_code != 200:
                log.warning("cra_charities_http_error", status=resp.status_code)
                return results

            results.extend(self._parse_charities_csv(resp.text))
        except Exception as exc:
            log.error("cra_charities_scrape_error", error=str(exc))

        return results

    def _parse_charities_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                designation = (row.get("Designation Type", "") or "").strip().lower()
                if "private" not in designation:
                    continue

                name = (row.get("Legal Name", "") or row.get("Operating Name", "") or "").strip()
                if not name:
                    continue

                # Check asset threshold
                total_assets_str = row.get("Total Assets", "") or "0"
                try:
                    total_assets = int(float(total_assets_str.replace(",", "")))
                except (ValueError, TypeError):
                    total_assets = 0

                if total_assets < _ASSET_THRESHOLD:
                    continue

                # Check for director changes or large grants
                signal_reasons = []
                directors_changed = row.get("Directors Changed", "") or ""
                if directors_changed.strip().lower() in ("yes", "y", "true", "1"):
                    signal_reasons.append("director_change")

                total_grants_str = row.get("Total Expenditures on Charitable Activities", "") or "0"
                try:
                    total_grants = int(float(total_grants_str.replace(",", "")))
                except (ValueError, TypeError):
                    total_grants = 0

                if total_grants >= _GRANT_THRESHOLD:
                    signal_reasons.append("large_grant")

                if not signal_reasons:
                    continue

                bn = (row.get("BN/Registration Number", "") or "").strip()

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="hnwi_foundation_director_change",
                        raw_company_name=name,
                        source_url=f"{_CRA_CHARITIES_SEARCH_URL}?q={bn}"
                        if bn
                        else _CRA_CHARITIES_SEARCH_URL,
                        signal_value={
                            "foundation_name": name,
                            "bn_registration": bn,
                            "total_assets_cad": total_assets,
                            "total_grants_cad": total_grants,
                            "reasons": signal_reasons,
                            "designation": designation,
                        },
                        signal_text=(
                            f"Private foundation '{name}' (assets ${total_assets:,}): "
                            f"{', '.join(signal_reasons)}"
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=[
                            "Wills / Estates",
                            "Tax",
                            "Corporate / Governance",
                        ],
                        raw_payload=dict(row),
                        confidence_score=0.78,
                    )
                )
            except Exception as exc:
                log.warning("cra_charities_row_error", error=str(exc))

        return results
