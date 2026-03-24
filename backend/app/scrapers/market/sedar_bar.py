"""app/scrapers/market/sedar_bar.py — SEDAR Business Acquisition Reports cross-reference."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class SedarBarScraper(BaseScraper):
    source_id = "market_sedar_bar"
    source_name = "SEDAR BAR"
    CATEGORY = "market"
    signal_types = ["business_acquisition_report"]
    SOURCE_URL = "https://www.sedarplus.ca"
    rate_limit_rps = 0.33
    concurrency = 1
    SOURCE_RELIABILITY = 1.0

    async def scrape(self) -> list[SignalData]:
        """Scrape Business Acquisition Reports — highest-signal M&A indicator."""
        signals: list[SignalData] = []
        params = {"search": "Business Acquisition Report", "lang": "en"}
        soup = await self.get_soup(
            f"{self.SOURCE_URL}/csa-party/records/search.html", params=params
        )
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
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="business_acquisition_report",
                    raw_company_name=company,
                    signal_text=f"Business Acquisition Report filed by {company} on {date_str}",
                    source_url=link if link.startswith("http") else f"{self.SOURCE_URL}{link}",
                    published_at=self.parse_date(date_str),
                    practice_area_hints=["ma_corporate", "securities_capital_markets"],
                    confidence_score=0.90,
                    signal_value={
                        "filing_type": "BAR",
                        "source": "SEDAR+",
                        "title": f"BAR filed: {company}",
                    },
                )
            )
        return signals
