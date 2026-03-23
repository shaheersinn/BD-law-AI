"""app/scrapers/market/sedar_bar.py — SEDAR Business Acquisition Reports cross-reference."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class SedarBarScraper(BaseScraper):
    NAME = "sedar_bar"
    CATEGORY = "market"
    SOURCE_URL = "https://www.sedarplus.ca"
    RATE_LIMIT_RPS = 0.33
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 1.0

    async def run(self) -> list[SignalData]:
        """Scrape Business Acquisition Reports — highest-signal M&A indicator."""
        signals = []
        params = {"search": "Business Acquisition Report", "lang": "en"}
        soup = await self.get_soup(f"{self.SOURCE_URL}/csa-party/records/search.html", params=params)
        if not soup:
            return signals
        rows = soup.select("table.results-table tbody tr")
        for row in rows[:20]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            filing_type = self.safe_text(cells[0])
            date_str = self.safe_text(cells[1])
            company = self.safe_text(cells[2])
            link_tag = cells[0].find("a")
            link = link_tag.get("href", "") if link_tag else ""
            if not company or "Business Acquisition" not in filing_type:
                continue
            signals.append(SignalData(
                scraper_name=self.NAME, signal_type="business_acquisition_report",
                raw_entity_name=company,
                title=f"BAR filed: {company}",
                summary=f"Business Acquisition Report filed by {company} on {date_str}",
                source_url=link if link.startswith("http") else f"{self.SOURCE_URL}{link}",
                published_at=self.parse_date(date_str),
                practice_areas=["ma_corporate", "securities_capital_markets"],
                signal_strength=0.90,
                metadata={"filing_type": "BAR", "source": "SEDAR+"},
            ))
        return signals
