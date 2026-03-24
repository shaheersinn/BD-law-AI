"""app/scrapers/filings/ciro.py — CIRO (formerly IIROC) enforcement and member notices."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class CiroScraper(BaseScraper):
    source_id = "corporate_ciro"
    source_name = "CIRO Enforcement"
    CATEGORY = "corporate"
    signal_types = ["enforcement_action"]
    SOURCE_URL = "https://www.ciro.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.95

    _ENFORCEMENT_URL = "https://www.ciro.ca/enforcement/disciplinary-proceedings"

    async def scrape(self) -> list[SignalData]:
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
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="enforcement_action",
                    raw_company_name=title,
                    signal_text=f"CIRO disciplinary proceeding: {title}",
                    source_url=link,
                    published_at=self.parse_date(date_str),
                    practice_area_hints=[
                        "financial_regulatory",
                        "securities_capital_markets",
                        "regulatory_compliance",
                    ],
                    confidence_score=0.85,
                    signal_value={"regulator": "CIRO", "title": f"CIRO enforcement: {title}"},
                )
            )
        return signals
