"""
CMHC housing starts scraper.

Source: CMHC Housing Market Information Portal.
Signal: cmhc_housing_starts_decline — fires when YoY housing starts
decline > 20% in CMAs where watchlist developers operate.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CMHC_DATA_URL = (
    "https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/"
    "housing-data/data-tables/housing-market-data/housing-starts-completions"
)
_CMHC_OPEN_DATA_URL = (
    "https://open.canada.ca/data/en/dataset/"
    "43dea6c6-71c4-4105-84ed-32b766e4cfaa"
)

_YOY_DECLINE_THRESHOLD = -0.20  # 20% decline


@register
class CMHCScraper(BaseScraper):
    source_id = "macro_cmhc"
    source_name = "CMHC Housing Data"
    signal_types = ["cmhc_housing_starts_decline"]
    CATEGORY = "macro"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_CMHC_DATA_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("cmhc_fetch_error", error=str(exc))
            return results

        # Look for data tables with housing starts
        tables = soup.find_all("table")
        for table in tables:
            try:
                rows = table.select("tbody tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    cma_name = self.safe_text(cells[0]).strip()
                    if not cma_name:
                        continue

                    # Try to extract current and previous values
                    current_val = self._parse_number(self.safe_text(cells[-1]))
                    prev_val = self._parse_number(self.safe_text(cells[-2]))

                    if current_val is None or prev_val is None or prev_val == 0:
                        continue

                    yoy_change = (current_val - prev_val) / prev_val

                    if yoy_change <= _YOY_DECLINE_THRESHOLD:
                        results.append(
                            ScraperResult(
                                source_id=self.source_id,
                                signal_type="cmhc_housing_starts_decline",
                                source_url=_CMHC_DATA_URL,
                                signal_value={
                                    "cma": cma_name,
                                    "current_starts": current_val,
                                    "previous_starts": prev_val,
                                    "yoy_change_pct": round(yoy_change * 100, 1),
                                },
                                signal_text=(
                                    f"CMHC: {cma_name} housing starts "
                                    f"{round(yoy_change * 100, 1)}% YoY "
                                    f"({int(prev_val)} → {int(current_val)})"
                                ),
                                published_at=self._now_utc(),
                                practice_area_hints=[
                                    "Real Estate & Construction",
                                ],
                                raw_payload={
                                    "cma": cma_name,
                                    "current": current_val,
                                    "previous": prev_val,
                                },
                                confidence_score=0.70,
                            )
                        )
            except Exception as exc:
                log.warning("cmhc_table_error", error=str(exc))

        return results

    @staticmethod
    def _parse_number(text: str) -> float | None:
        """Parse a number from text, handling commas and other formatting."""
        cleaned = re.sub(r"[^\d.\-]", "", text)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
