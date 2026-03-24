"""app/scrapers/filings/osfi_regulated.py — OSFI regulated entities list."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class OsfiRegulatedEntitiesScraper(BaseScraper):
    source_id = "corporate_osfi_regulated"
    source_name = "OSFI Regulated Entities"
    CATEGORY = "corporate"
    signal_types = ["regulated_entity"]
    SOURCE_URL = "https://www.osfi-bsif.gc.ca/Eng/wt-ow/Pages/wt-eo.aspx"
    rate_limit_rps = 1.0
    concurrency = 1
    SOURCE_RELIABILITY = 0.95

    async def scrape(self) -> list[SignalData]:
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
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="regulated_entity",
                        raw_company_name=entity_name,
                        signal_text=f"OSFI regulated entity: {entity_name}, category: {category}",
                        source_url=self.SOURCE_URL,
                        practice_area_hints=[
                            "financial_regulatory",
                            "banking_finance",
                            "regulatory_compliance",
                        ],
                        confidence_score=0.60,
                        signal_value={
                            "category": category,
                            "regulator": "OSFI",
                            "title": f"OSFI regulated: {entity_name} ({category})",
                        },
                    )
                )
        return signals
