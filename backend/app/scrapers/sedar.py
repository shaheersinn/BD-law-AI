"""
app/scrapers/sedar.py — SEDAR+ filing scraper.

Monitors SEDAR+ public search for high-signal filing types.
SEDAR+ does not expose an official REST API; we scrape the search results page.
Schedule: every 2 hours during business hours via Celery beat.
"""

import logging
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, RawSignal

log = logging.getLogger(__name__)

SEDAR_BASE = "https://www.sedarplus.ca"
SEARCH_URL = f"{SEDAR_BASE}/csa-party/public/search/results.html"

# Filing type → (practice area, urgency 0-100, base weight)
TRIGGER_MAP: dict[str, tuple[str, int, float]] = {
    "Material Change Report":             ("Corporate / M&A",           88, 0.88),
    "Business Acquisition Report":        ("Corporate / M&A",           92, 0.92),
    "Confidential Treatment Request":     ("Corporate / M&A",           91, 0.91),
    "Cease Trade Order":                  ("Securities",                 87, 0.87),
    "Annual Information Form":            ("Securities",                 40, 0.40),
    "Notice of Meeting":                  ("Corporate / Governance",     45, 0.45),
    "Going Concern Qualification":        ("Restructuring / Insolvency", 84, 0.84),
    "Auditor Change":                     ("Corporate / Governance",     79, 0.79),
    "Director or Officer Change":         ("Corporate / Governance",     76, 0.76),
    "Management Information Circular":    ("Corporate / Governance",     55, 0.55),
}


class SedarScraper(BaseScraper):
    source_name = "SEDAR"
    request_delay_seconds = 2.0

    async def fetch_new(self, days_back: int = 1) -> list[RawSignal]:
        """Scrape new SEDAR+ filings from the last `days_back` days."""
        date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )
        signals: list[RawSignal] = []

        for filing_type, (practice, urgency, weight) in TRIGGER_MAP.items():
            if urgency < 50:  # skip low-signal filings
                continue
            try:
                batch = await self._scrape_filing_type(
                    filing_type, date_from, practice, urgency, weight
                )
                signals.extend(batch)
            except Exception as e:
                log.warning("SEDAR scrape failed for %s: %s", filing_type, e)

        log.info("SEDAR: fetched %d raw signals", len(signals))
        return signals

    async def _scrape_filing_type(
        self,
        filing_type: str,
        date_from: str,
        practice: str,
        urgency: int,
        weight: float,
    ) -> list[RawSignal]:
        params = {
            "filing_type": filing_type,
            "date_from": date_from,
            "language": "E",
        }
        try:
            resp = await self._get(SEARCH_URL, params=params)
        except Exception as e:
            log.debug("SEDAR HTTP error for %s: %s", filing_type, e)
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        rows = soup.select("table.filing-results tr, table tr")  # CSS varies

        results: list[RawSignal] = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            company_name = cols[0].get_text(strip=True)
            doc_type = cols[1].get_text(strip=True) if len(cols) > 1 else filing_type
            date_str = cols[2].get_text(strip=True) if len(cols) > 2 else date_from
            link_tag = row.find("a", href=True)
            url = f"{SEDAR_BASE}{link_tag['href']}" if link_tag else SEARCH_URL

            if not company_name or company_name.lower() in ("company", "issuer", ""):
                continue

            try:
                filed_at = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                filed_at = datetime.now(timezone.utc)

            results.append(
                RawSignal(
                    source="SEDAR",
                    trigger_type=filing_type,
                    company_name=company_name,
                    title=f"{company_name} — {filing_type}",
                    practice_area=practice,
                    urgency=urgency,
                    filed_at=filed_at,
                    description=f"{filing_type} filed on SEDAR+. Review the full document for material terms.",
                    url=url,
                    base_weight=weight,
                )
            )

        return results
