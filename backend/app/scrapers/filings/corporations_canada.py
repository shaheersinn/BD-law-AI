"""app/scrapers/filings/corporations_canada.py — Corporations Canada federal registry."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class CorporationsCanadaScraper(BaseScraper):
    NAME = "corporations_canada"
    CATEGORY = "filings"
    SOURCE_URL = "https://www.ic.gc.ca/app/scr/cc/CorporationsCanada"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.9

    async def run(self) -> list[SignalData]:
        signals: list[SignalData] = []
        # Search for recent federal corporate changes (amalgamations, dissolutions, name changes)
        # These signal M&A activity and restructuring
        search_url = "https://www.ic.gc.ca/app/scr/cc/CorporationsCanada/fdrlCrpSrch.html"
        params = {"V_TOKEN": "", "LANG": "eng", "SEARCH_TYPE": "recent_changes"}
        soup = await self.get_soup(search_url, params=params)
        if soup is None:
            return signals
        rows = soup.select("table#searchResults tbody tr") if soup else []
        for row in rows[:30]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            corp_name = self.safe_text(cells[0])
            corp_num = self.safe_text(cells[1])
            status = self.safe_text(cells[2])
            if not corp_name:
                continue
            practice_areas = ["ma_corporate"]
            strength = 0.50
            if "dissolved" in status.lower() or "amalgamated" in status.lower():
                strength = 0.70
                practice_areas.append("insolvency_restructuring")
            signals.append(SignalData(
                scraper_name=self.NAME,
                signal_type="corporate_status_change",
                raw_entity_name=corp_name,
                title=f"Federal corp status: {corp_name} — {status}",
                summary=f"Corporations Canada: {corp_name} (#{corp_num}) status changed to {status}",
                source_url=self.SOURCE_URL,
                practice_areas=practice_areas,
                signal_strength=strength,
                metadata={"corp_number": corp_num, "status": status},
            ))
        return signals
