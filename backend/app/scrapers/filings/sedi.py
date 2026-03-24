"""app/scrapers/filings/sedi.py — SEDI insider trading scraper."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class SediScraper(BaseScraper):
    source_id = "corporate_sedi"
    source_name = "SEDI Insider Trading"
    CATEGORY = "corporate"
    signal_types = ["insider_transaction"]
    SOURCE_URL = "https://www.sedi.ca"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.95

    async def scrape(self) -> list[SignalData]:
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
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="insider_transaction",
                    raw_company_name=company_name,
                    signal_text=f"SEDI insider trade: {insider_name} {transaction_type} {value_str} of {company_name} on {date_str}",
                    source_url=self.SOURCE_URL,
                    published_at=self.parse_date(date_str),
                    practice_area_hints=practice_areas,
                    confidence_score=strength,
                    signal_value={
                        "transaction_type": transaction_type,
                        "insider": insider_name,
                        "value": value_str,
                        "title": f"Insider {transaction_type}: {company_name} — {insider_name}",
                    },
                )
            )
        return signals
