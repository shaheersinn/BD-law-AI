"""
WorkSafeBC penalties scraper.

Source: WorkSafeBC enforcement orders and penalties listing.
Signal: worksafebc_penalty — fires when watchlist companies receive penalties.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_WORKSAFEBC_URL = (
    "https://www.worksafebc.com/en/health-safety/enforcement-orders-and-penalties"
)


@register
class WorkSafeBCScraper(BaseScraper):
    source_id = "labour_worksafebc"
    source_name = "WorkSafeBC Penalties"
    signal_types = ["worksafebc_penalty"]
    CATEGORY = "labour"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_WORKSAFEBC_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("worksafebc_fetch_error", error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"penalty|result|order", re.I))
            or soup.find_all("article")
        )

        for entry in entries[:40]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                cells = entry.find_all(["td", "th"])

                employer = ""
                if cells:
                    employer = self.safe_text(cells[0]).strip()
                if not employer:
                    employer = text[:80]

                # Extract penalty amount
                amount = self._extract_amount(text)

                # Extract date
                date_text = None
                for cell in cells:
                    cell_text = self.safe_text(cell)
                    parsed = self._parse_date(cell_text)
                    if parsed:
                        date_text = parsed
                        break

                link_el = entry.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        source_url = f"https://www.worksafebc.com{href}"

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="worksafebc_penalty",
                        raw_company_name=employer,
                        source_url=source_url or _WORKSAFEBC_URL,
                        signal_value={
                            "employer": employer,
                            "amount_cad": amount,
                            "type": "penalty",
                        },
                        signal_text=(
                            f"WorkSafeBC penalty: {employer}"
                            + (f" — ${amount:,}" if amount else "")
                        ),
                        published_at=date_text or self._now_utc(),
                        practice_area_hints=[
                            "Employment & Labour",
                            "Regulatory",
                        ],
                        raw_payload={"employer": employer, "text": text[:500]},
                        confidence_score=0.78,
                    )
                )
            except Exception as exc:
                log.warning("worksafebc_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        """Extract penalty amount from text."""
        match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if match:
            try:
                return int(float(match.group(1).replace(",", "")))
            except ValueError:
                return None
        return None
