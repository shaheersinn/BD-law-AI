"""
Trust deemed-disposition aging scraper.

Sources: CRA T3010 bulk data (open.canada.ca) + SEDI insider trust filings.
Signal: trust_deemed_disposition_approaching — fires when a private foundation
approaches the 21-year deemed disposition under ITA s.104(4).
"""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CRA_T3010_BULK_URL = (
    "https://open.canada.ca/data/dataset/f4cad712-4382-4184-93b3-4c39b370dcb0/"
    "resource/download/t3010-charities.csv"
)
_SEDI_SEARCH_URL = "https://www.sedi.ca/sedi/SVTGPPublicSearchFormload.do"

# 21-year rule window: flag foundations 19–22 years old
_MIN_AGE_YEARS = 19
_MAX_AGE_YEARS = 22


@register
class TrustAgingScraper(BaseScraper):
    source_id = "hnwi_trust_aging"
    source_name = "CRA T3010 Trust Aging"
    signal_types = ["trust_deemed_disposition_approaching"]
    CATEGORY = "hnwi"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400  # 24h — annual data

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        now = datetime.now(tz=UTC)
        current_year = now.year

        # --- CRA T3010 bulk CSV ---
        try:
            resp = await self.get(_CRA_T3010_BULK_URL)
            if resp.status_code == 200:
                results.extend(self._parse_t3010(resp.text, current_year))
            else:
                log.warning("trust_aging_t3010_http_error", status=resp.status_code)
        except Exception as exc:
            log.error("trust_aging_t3010_error", error=str(exc))

        # --- SEDI trust name year patterns ---
        try:
            sedi_results = await self._scrape_sedi_trusts(current_year)
            results.extend(sedi_results)
        except Exception as exc:
            log.error("trust_aging_sedi_error", error=str(exc))

        return results

    def _parse_t3010(self, csv_text: str, current_year: int) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                # Look for private foundations with inception year data
                designation = (row.get("Designation Type", "") or "").strip().lower()
                if "private" not in designation and "foundation" not in designation:
                    continue

                name = (row.get("Legal Name", "") or row.get("Operating Name", "") or "").strip()
                if not name:
                    continue

                # Try to extract fiscal period start year as proxy for inception
                fiscal_start = row.get("Fiscal Period Start", "") or ""
                inception_year = self._extract_year(fiscal_start)
                if not inception_year:
                    continue

                age = current_year - inception_year
                if _MIN_AGE_YEARS <= age <= _MAX_AGE_YEARS:
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="trust_deemed_disposition_approaching",
                            raw_company_name=name,
                            source_url="https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/dsplyBscSrch",
                            signal_value={
                                "foundation_name": name,
                                "inception_year": inception_year,
                                "age_years": age,
                                "deemed_disposition_year": inception_year + 21,
                                "designation": designation,
                            },
                            signal_text=(
                                f"Private foundation '{name}' (est. {inception_year}) "
                                f"approaching 21-year deemed disposition in {inception_year + 21}"
                            ),
                            published_at=self._now_utc(),
                            practice_area_hints=["Tax", "Wills / Estates"],
                            raw_payload=dict(row),
                            confidence_score=0.80,
                        )
                    )
            except Exception as exc:
                log.warning("trust_aging_row_parse_error", error=str(exc))

        return results

    async def _scrape_sedi_trusts(self, current_year: int) -> list[ScraperResult]:
        """Scan SEDI for trust names containing year patterns (e.g. 'Smith Family Trust 2004')."""
        results: list[ScraperResult] = []
        year_pattern = re.compile(r"\b(19|20)\d{2}\b")

        try:
            resp = await self.get(_SEDI_SEARCH_URL)
            if resp.status_code != 200:
                return results

            soup = await self.get_soup(_SEDI_SEARCH_URL)
            if not soup:
                return results

            # Look for trust-related entries with year patterns
            for link in soup.find_all("a", string=year_pattern):
                text = self.safe_text(link)
                if not text or "trust" not in text.lower():
                    continue

                match = year_pattern.search(text)
                if not match:
                    continue

                year = int(match.group())
                age = current_year - year
                if _MIN_AGE_YEARS <= age <= _MAX_AGE_YEARS:
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="trust_deemed_disposition_approaching",
                            raw_company_name=text,
                            source_url="https://www.sedi.ca",
                            signal_value={
                                "trust_name": text,
                                "year_in_name": year,
                                "age_years": age,
                                "source": "sedi",
                            },
                            signal_text=(
                                f"SEDI trust '{text}' (year {year}) "
                                f"approaching 21-year deemed disposition"
                            ),
                            published_at=self._now_utc(),
                            practice_area_hints=["Tax", "Wills / Estates"],
                            raw_payload={"trust_name": text, "year": year},
                            confidence_score=0.70,
                        )
                    )
        except Exception as exc:
            log.warning("trust_aging_sedi_parse_error", error=str(exc))

        return results

    @staticmethod
    def _extract_year(date_str: str) -> int | None:
        """Extract a 4-digit year from a date string."""
        match = re.search(r"\b(19|20)\d{2}\b", date_str)
        return int(match.group()) if match else None
