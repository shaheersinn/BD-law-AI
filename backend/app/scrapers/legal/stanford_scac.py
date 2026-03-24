"""app/scrapers/legal/stanford_scac.py — Stanford Securities Class Action Clearinghouse."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class StanfordScacScraper(BaseScraper):
    NAME = "stanford_scac"
    CATEGORY = "legal"
    SOURCE_URL = "https://securities.stanford.edu"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.90

    async def run(self) -> list[SignalData]:
        """Scrape recent securities class action filings from Stanford SCAC."""
        signals: list[SignalData] = []
        soup = await self.get_soup(f"{self.SOURCE_URL}/class-action-filings/all.html")
        if not soup:
            return signals
        rows = soup.select("table.filing-table tbody tr, table tbody tr")
        for row in rows[:30]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            company = self.safe_text(cells[0])
            date_str = self.safe_text(cells[1])
            exchange = self.safe_text(cells[2]) if len(cells) > 2 else ""
            link_tag = row.find("a")
            link = link_tag.get("href", "") if link_tag else ""
            if link and not link.startswith("http"):
                link = f"{self.SOURCE_URL}{link}"
            if not company:
                continue
            signals.append(
                SignalData(
                    scraper_name=self.NAME,
                    signal_type="class_action_filed",
                    raw_entity_name=company,
                    title=f"Securities class action: {company}",
                    summary=f"Securities class action filed against {company} ({exchange})",
                    source_url=link,
                    published_at=self.parse_date(date_str),
                    practice_areas=["class_actions", "securities_capital_markets", "litigation"],
                    signal_strength=0.90,
                    metadata={"exchange": exchange, "source": "Stanford SCAC"},
                )
            )
        return signals
