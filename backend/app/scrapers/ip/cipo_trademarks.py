"""
CIPO trademark database scraper.

Source: Canadian Intellectual Property Office (CIPO) trademark DB + bulk CSV.
Signal: trademark_new_class_expansion — fires on new filings, new Nice
class expansions (within 90 days), and international designations.
"""

from __future__ import annotations

import csv
import io
import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CIPO_SEARCH_URL = "https://ised-isde.canada.ca/cipo/trademark-search/srch"
_CIPO_BULK_URL = (
    "https://ised-isde.canada.ca/cipo/trademark-search/data/trademarks-data.csv"
)


@register
class CIPOTrademarksScraper(BaseScraper):
    source_id = "ip_cipo_trademarks"
    source_name = "CIPO Trademark Database"
    signal_types = ["trademark_new_class_expansion"]
    CATEGORY = "ip"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_CIPO_BULK_URL)
            if resp.status_code != 200:
                log.warning("cipo_http_error", status=resp.status_code)
                # Fallback to search page
                return await self._scrape_search_page()

            results.extend(self._parse_bulk_csv(resp.text))
        except Exception as exc:
            log.error("cipo_scrape_error", error=str(exc))

        return results

    def _parse_bulk_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            try:
                applicant = (
                    row.get("Applicant Name", "")
                    or row.get("Owner Name", "")
                    or ""
                ).strip()
                if not applicant:
                    continue

                trademark = (row.get("Trademark", "") or row.get("Mark", "") or "").strip()
                nice_classes = (row.get("Nice Classes", "") or row.get("Classes", "") or "").strip()
                filing_date = (row.get("Filing Date", "") or "").strip()
                status = (row.get("Status", "") or "").strip()
                app_number = (row.get("Application Number", "") or "").strip()

                # Only interested in recent or active filings
                if status.lower() in ("abandoned", "refused", "cancelled"):
                    continue

                # Determine signal reason
                is_international = bool(
                    row.get("International Registration", "")
                    or row.get("Madrid Protocol", "")
                )
                class_count = len(nice_classes.split(",")) if nice_classes else 0

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="trademark_new_class_expansion",
                        raw_company_name=applicant,
                        source_url=f"{_CIPO_SEARCH_URL}?appNo={app_number}" if app_number else _CIPO_SEARCH_URL,
                        signal_value={
                            "applicant": applicant,
                            "trademark": trademark,
                            "nice_classes": nice_classes,
                            "class_count": class_count,
                            "filing_date": filing_date,
                            "is_international": is_international,
                            "application_number": app_number,
                        },
                        signal_text=(
                            f"CIPO TM: {applicant} — '{trademark}' "
                            f"({class_count} class{'es' if class_count != 1 else ''})"
                        ),
                        published_at=self._parse_date(filing_date),
                        practice_area_hints=["IP", "Corporate / M&A"],
                        raw_payload=dict(row),
                        confidence_score=0.75 if class_count > 1 else 0.65,
                    )
                )
            except Exception as exc:
                log.warning("cipo_row_error", error=str(exc))

        return results

    async def _scrape_search_page(self) -> list[ScraperResult]:
        """Fallback: scrape CIPO search page for recent filings."""
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_CIPO_SEARCH_URL)
            if not soup:
                return results
        except Exception as exc:
            log.warning("cipo_search_fetch_error", error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"result|trademark", re.I))
        )

        for entry in entries[:30]:
            try:
                text = self.safe_text(entry)
                if not text:
                    continue

                applicant = self._extract_field(text, ["applicant", "owner"])
                trademark = self._extract_field(text, ["mark", "trademark"])

                if applicant:
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="trademark_new_class_expansion",
                            raw_company_name=applicant,
                            source_url=_CIPO_SEARCH_URL,
                            signal_value={
                                "applicant": applicant,
                                "trademark": trademark,
                            },
                            signal_text=f"CIPO TM: {applicant} — '{trademark or 'unknown'}'",
                            published_at=self._now_utc(),
                            practice_area_hints=["IP", "Corporate / M&A"],
                            raw_payload={"text": text[:500]},
                            confidence_score=0.65,
                        )
                    )
            except Exception as exc:
                log.warning("cipo_search_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_field(text: str, labels: list[str]) -> str | None:
        """Extract field value after a label."""
        for label in labels:
            pattern = rf"{label}\s*[:]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1).strip()
        return None
