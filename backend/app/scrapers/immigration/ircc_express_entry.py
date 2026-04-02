"""
IRCC Express Entry draw scraper.

Source: IRCC Open Data (Open Canada).
Signal: immigration_express_entry_draw — macro context signal for sector-specific
immigration trends (not company-specific).
"""

from __future__ import annotations

import csv
import io

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_IRCC_DRAWS_URL = (
    "https://open.canada.ca/data/dataset/92fceba4-d7a7-47e4-b7b4-99f5c4a44c64/"
    "resource/download/express-entry-draws.csv"
)


@register
class IRCCExpressEntryScraper(BaseScraper):
    source_id = "immigration_ircc"
    source_name = "IRCC Express Entry"
    signal_types = ["immigration_express_entry_draw"]
    CATEGORY = "immigration"
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_IRCC_DRAWS_URL)
            if resp.status_code != 200:
                log.warning("ircc_express_entry_http_error", status=resp.status_code)
                return results

            results.extend(self._parse_draws_csv(resp.text))
        except Exception as exc:
            log.error("ircc_express_entry_error", error=str(exc))

        return results

    def _parse_draws_csv(self, csv_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        reader = csv.DictReader(io.StringIO(csv_text))

        rows = list(reader)
        if not rows:
            return results

        # Focus on recent draws (last 5)
        recent = rows[-5:] if len(rows) > 5 else rows

        for row in recent:
            try:
                draw_number = (row.get("Draw Number", "") or row.get("draw_number", "") or "").strip()
                draw_date = (row.get("Date", "") or row.get("draw_date", "") or "").strip()
                draw_type = (row.get("Draw Type", "") or row.get("category", "") or "").strip()
                invitations = (row.get("Number of Invitations", "") or row.get("invitations", "") or "").strip()
                crs_cutoff = (row.get("CRS Cut-Off", "") or row.get("crs_score", "") or "").strip()

                if not draw_date:
                    continue

                published_at = self._parse_date(draw_date)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="immigration_express_entry_draw",
                        source_url="https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/submit-profile/rounds-invitations.html",
                        signal_value={
                            "draw_number": draw_number,
                            "draw_date": draw_date,
                            "draw_type": draw_type,
                            "invitations": invitations,
                            "crs_cutoff": crs_cutoff,
                        },
                        signal_text=(
                            f"Express Entry draw #{draw_number}: "
                            f"{invitations} invitations, CRS {crs_cutoff} ({draw_type})"
                        ),
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=["Corporate Immigration"],
                        raw_payload=dict(row),
                        confidence_score=0.55,
                    )
                )
            except Exception as exc:
                log.warning("ircc_draw_parse_error", error=str(exc))

        return results
