"""
Canada Labour Code naming scraper.

Source: ESDC employer compliance naming page (Part III).
Signal: labour_code_payment_order — fires when payment orders > $10,000
are issued against employers.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_ESDC_NAMING_URL = (
    "https://www.canada.ca/en/employment-social-development/services/"
    "labour-standards/reports/employer-compliance-part3.html"
)

_HIGH_VALUE_THRESHOLD = 10_000  # $10K


@register
class CanadaLabourCodeNamingScraper(BaseScraper):
    source_id = "labour_code_naming"
    source_name = "ESDC Labour Code Naming"
    signal_types = ["labour_code_payment_order"]
    CATEGORY = "labour"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_ESDC_NAMING_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("labour_code_naming_error", error=str(exc))
            return results

        # Parse the naming page table
        tables = soup.find_all("table")
        for table in tables:
            try:
                rows = table.select("tbody tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    employer = self.safe_text(cells[0]).strip()
                    if not employer:
                        continue

                    # Extract amount
                    amount = None
                    for cell in cells:
                        cell_text = self.safe_text(cell)
                        extracted = self._extract_amount(cell_text)
                        if extracted is not None:
                            amount = extracted
                            break

                    is_high_value = amount is not None and amount >= _HIGH_VALUE_THRESHOLD

                    # Extract violation type
                    violation = ""
                    for cell in cells[1:]:
                        text = self.safe_text(cell)
                        if text and not text.startswith("$"):
                            violation = text
                            break

                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="labour_code_payment_order",
                            raw_company_name=employer,
                            source_url=_ESDC_NAMING_URL,
                            signal_value={
                                "employer": employer,
                                "amount_cad": amount,
                                "violation": violation,
                                "is_high_value": is_high_value,
                            },
                            signal_text=(
                                f"Labour Code order: {employer}"
                                + (f" — ${amount:,}" if amount else "")
                            ),
                            published_at=self._now_utc(),
                            practice_area_hints=["Employment & Labour"],
                            raw_payload={
                                "employer": employer,
                                "violation": violation,
                                "amount": amount,
                            },
                            confidence_score=0.80 if is_high_value else 0.70,
                        )
                    )
            except Exception as exc:
                log.warning("labour_code_table_error", error=str(exc))

        return results

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        """Extract dollar amount from cell text."""
        match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if match:
            try:
                return int(float(match.group(1).replace(",", "")))
            except ValueError:
                return None
        return None
