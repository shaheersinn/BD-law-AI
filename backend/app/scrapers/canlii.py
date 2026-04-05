"""
app/scrapers/canlii.py — CanLII REST API for new Canadian litigation.
Register for a free API key at developer.canlii.org.
Schedule: daily at 7am.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.scrapers.base import BaseScraper, RawSignal

log = logging.getLogger(__name__)
settings = get_settings()

CANLII_API = "https://api.canlii.org/v1"


class CanLIIScraper(BaseScraper):
    source_id = "legal_canlii"
    source_name = "CANLII"
    request_delay_seconds = 1.5

    async def search_company(self, company_name: str, days_back: int = 7) -> list[RawSignal]:
        """Search for recent cases naming a company as party."""
        if not settings.canlii_api_key:
            log.warning("CANLII_API_KEY not set — skipping CanLII scrape")
            return []

        date_after = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "api_key": settings.canlii_api_key,
            "resultCount": 20,
            "searchText": company_name,
            "decisionDateAfter": date_after,
        }

        try:
            resp = await self._get(f"{CANLII_API}/caseBrowse/en/", params=params)
        except Exception as e:
            log.warning("CanLII request failed for %s: %s", company_name, e)
            return []

        data = resp.json()
        cases = data.get("cases", [])
        signals = []

        for case in cases:
            title = case.get("title", "")
            case_url = case.get("url", "")
            date_str = case.get("decisionDate", "")

            # Determine defendant vs plaintiff
            parts = title.split(" v. ")
            is_defendant = len(parts) > 1 and company_name.lower() in parts[-1].lower()

            practice = "Litigation — Defense" if is_defendant else "Litigation — Advisory"
            urgency = 80 if is_defendant else 60
            weight = 0.88 if is_defendant else 0.72

            trigger_type = "litigation_defendant" if is_defendant else "litigation_plaintiff"

            try:
                filed_at = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError:
                filed_at = datetime.now(UTC)

            signals.append(
                RawSignal(
                    source="CANLII",
                    trigger_type=trigger_type,
                    company_name=company_name,
                    title=title,
                    practice_area=practice,
                    urgency=urgency,
                    filed_at=filed_at,
                    description=f"CanLII case: {title}. {'Company named as defendant.' if is_defendant else 'Company named as plaintiff.'}",
                    url=case_url,
                    base_weight=weight,
                )
            )

        return signals

    async def fetch_new(self) -> list[RawSignal]:
        """
        Scheduled method: search all watchlist companies.
        Actual watchlist comes from the database — called by the Celery task.
        This stub returns empty; the task injects the company list.
        """
        return []
