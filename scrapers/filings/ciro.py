"""app/scrapers/filings/ciro.py — CIRO (formerly IIROC) enforcement and member notices."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class CiroScraper(BaseScraper):
    NAME = "ciro_enforcement"
    CATEGORY = "filings"
    SOURCE_URL = "https://www.ciro.ca"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.95

    _ENFORCEMENT_URL = "https://www.ciro.ca/enforcement/disciplinary-proceedings"

    async def run(self) -> list[SignalData]:
        signals: list[SignalData] = []
        soup = await self.get_soup(self._ENFORCEMENT_URL)
        if soup is None:
            return signals
        # Parse disciplinary proceedings
        cases = soup.select("article.enforcement-case, div.case-listing, table tbody tr")
        for case in cases[:30]:
            title = self.safe_text(case.find("h3") or case.find("td"))
            link_tag = case.find("a")
            link = link_tag.get("href", "") if link_tag else ""
            date_tag = case.find("time") or case.find(class_="date")
            date_str = self.safe_text(date_tag)
            if not title:
                continue
            if link and not link.startswith("http"):
                link = f"{self.SOURCE_URL}{link}"
            signals.append(SignalData(
                scraper_name=self.NAME,
                signal_type="enforcement_action",
                raw_entity_name=title,
                title=f"CIRO enforcement: {title}",
                summary=f"CIRO disciplinary proceeding: {title}",
                source_url=link,
                published_at=self.parse_date(date_str),
                practice_areas=["financial_regulatory", "securities_capital_markets", "regulatory_compliance"],
                signal_strength=0.85,
                metadata={"regulator": "CIRO"},
            ))
        return signals
