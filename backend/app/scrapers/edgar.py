"""
app/scrapers/edgar.py — SEC EDGAR full-text search scraper.
Free REST API — no key required. Schedule: hourly.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.scrapers.base import BaseScraper, RawSignal

log = logging.getLogger(__name__)

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_COMPANY_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="

EDGAR_TRIGGERS: dict[str, tuple[str, int, float]] = {
    "CT ORDER":  ("Corporate / M&A",  92, 0.89),
    "SC 13D":    ("Corporate / M&A",  85, 0.85),
    "DEFM14A":   ("Corporate / M&A",  95, 0.96),
    "S-4":       ("Corporate / M&A",  95, 0.96),
    "8-K":       ("Securities",       75, 0.75),
}


class EdgarScraper(BaseScraper):
    source_name = "EDGAR"
    request_delay_seconds = 0.5   # SEC allows reasonable crawling

    async def fetch_new(self, days_back: int = 2) -> list[RawSignal]:
        date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )
        signals: list[RawSignal] = []

        for form_type, (practice, urgency, weight) in EDGAR_TRIGGERS.items():
            try:
                batch = await self._fetch_form_type(
                    form_type, date_from, practice, urgency, weight
                )
                signals.extend(batch)
            except Exception as e:
                log.warning("EDGAR scrape error for %s: %s", form_type, e)

        log.info("EDGAR: %d signals", len(signals))
        return signals

    async def _fetch_form_type(
        self,
        form_type: str,
        date_from: str,
        practice: str,
        urgency: int,
        weight: float,
    ) -> list[RawSignal]:
        params = {
            "q": '"confidential" OR "material"',
            "dateRange": "custom",
            "startdt": date_from,
            "forms": form_type,
            "hits.hits._source": "period_of_report,display_names,entity_id,file_date",
        }
        resp = await self._get(EDGAR_SEARCH, params=params)
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        results = []
        for hit in hits[:20]:
            src = hit.get("_source", {})
            names = src.get("display_names", [])
            company = names[0] if names else "Unknown Issuer"
            entity_id = src.get("entity_id", "")
            file_date = src.get("file_date", date_from)

            try:
                filed_at = datetime.strptime(file_date, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                filed_at = datetime.now(timezone.utc)

            results.append(
                RawSignal(
                    source="EDGAR",
                    trigger_type=form_type,
                    company_name=company,
                    title=f"{company} — {form_type} filed {file_date}",
                    practice_area=practice,
                    urgency=urgency,
                    filed_at=filed_at,
                    description=f"SEC {form_type} filing detected. Entity ID: {entity_id}.",
                    url=f"{EDGAR_COMPANY_URL}{entity_id}",
                    base_weight=weight,
                )
            )
        return results
