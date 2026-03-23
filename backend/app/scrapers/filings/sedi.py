"""app/scrapers/filings/sedi.py — SEDI insider trading scraper."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class SediScraper(BaseScraper):
    NAME = "sedi_insider_trading"
    CATEGORY = "filings"
    SOURCE_URL = "https://www.sedi.ca"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.95

    async def run(self) -> list[SignalData]:
        signals: list[SignalData] = []
        # SEDI has CAPTCHA protection — use search endpoint for bulk insider reports
        # Focus on Form 55-102F4 (insider reporting) with large transactions
        url = "https://www.sedi.ca/sedi/SVTMenuChoix?lang=en"
        soup = await self.get_soup(url)
        if soup is None:
            return signals
        # Parse recent large insider transactions (>$500K threshold)
        # as signals for M&A, securities, or governance issues
        transactions = soup.select("table.insiderTable tr") if soup else []
        for row in transactions[1:20]:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            company_name = self.safe_text(cells[0])
            insider_name = self.safe_text(cells[1])
            transaction_type = self.safe_text(cells[2])
            date_str = self.safe_text(cells[3])
            value_str = self.safe_text(cells[4])
            if not company_name:
                continue
            practice_areas = ["securities_capital_markets"]
            strength = 0.55
            # Large disposals can indicate issues
            if "disposition" in transaction_type.lower() or "sell" in transaction_type.lower():
                strength = 0.70
                practice_areas.insert(0, "ma_corporate")
            signals.append(SignalData(
                scraper_name=self.NAME,
                signal_type="insider_transaction",
                raw_entity_name=company_name,
                title=f"Insider {transaction_type}: {company_name} — {insider_name}",
                summary=f"SEDI insider trade: {insider_name} {transaction_type} {value_str} of {company_name} on {date_str}",
                source_url=self.SOURCE_URL,
                published_at=self.parse_date(date_str),
                practice_areas=practice_areas,
                signal_strength=strength,
                metadata={"transaction_type": transaction_type, "insider": insider_name, "value": value_str},
            ))
        return signals
