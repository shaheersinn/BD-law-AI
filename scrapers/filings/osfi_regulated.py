"""app/scrapers/filings/osfi_regulated.py — OSFI regulated entities list."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class OsfiRegulatedEntitiesScraper(BaseScraper):
    NAME = "osfi_regulated_entities"
    CATEGORY = "filings"
    SOURCE_URL = "https://www.osfi-bsif.gc.ca/Eng/wt-ow/Pages/wt-eo.aspx"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.95

    async def run(self) -> list[SignalData]:
        """Scrape OSFI list for new/removed regulated entities — signals financial regulatory issues."""
        signals: list[SignalData] = []
        data = await self.get_json("https://www.osfi-bsif.gc.ca/Eng/wt-ow/Pages/wt-eo.aspx")
        if data is None:
            soup = await self.get_soup(self.SOURCE_URL)
            if soup is None:
                return signals
            rows = soup.select("table.wikitable tbody tr") if soup else []
            for row in rows[:50]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                entity_name = self.safe_text(cells[0])
                category = self.safe_text(cells[1])
                if not entity_name:
                    continue
                signals.append(SignalData(
                    scraper_name=self.NAME,
                    signal_type="regulated_entity",
                    raw_entity_name=entity_name,
                    title=f"OSFI regulated: {entity_name} ({category})",
                    summary=f"OSFI regulated entity: {entity_name}, category: {category}",
                    source_url=self.SOURCE_URL,
                    practice_areas=["financial_regulatory", "banking_finance", "regulatory_compliance"],
                    signal_strength=0.60,
                    metadata={"category": category, "regulator": "OSFI"},
                ))
        return signals
