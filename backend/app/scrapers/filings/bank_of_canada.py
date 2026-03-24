"""app/scrapers/filings/bank_of_canada.py — Bank of Canada rate decisions + financial stability."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class BankOfCanadaScraper(BaseScraper):
    source_id = "corporate_boc"
    source_name = "Bank of Canada"
    CATEGORY = "corporate"
    signal_types = ["macro_indicator"]
    SOURCE_URL = "https://www.bankofcanada.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 1.0

    _RSS_URL = "https://www.bankofcanada.ca/feed/"

    async def scrape(self) -> list[SignalData]:
        """Scrape BoC news feed for rate decisions and financial stability reports."""
        signals: list[SignalData] = []
        feed = await self.get_rss(self._RSS_URL)
        if feed is None:
            return signals
        for entry in feed.get("entries", [])[:20]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            published = self.parse_date(entry.get("published"))
            # Rate decisions → insolvency lag signal
            practice_areas = ["banking_finance"]
            strength = 0.50
            title_lower = title.lower()
            if "policy interest rate" in title_lower or "overnight rate" in title_lower:
                practice_areas = [
                    "insolvency_restructuring",
                    "banking_finance",
                    "real_estate_construction",
                ]
                strength = 0.75
            elif "financial stability" in title_lower:
                practice_areas = [
                    "banking_finance",
                    "insolvency_restructuring",
                    "financial_regulatory",
                ]
                strength = 0.70
            elif "inflation" in title_lower:
                practice_areas = ["insolvency_restructuring", "employment_labour"]
                strength = 0.60
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="macro_indicator",
                    raw_company_name="Bank of Canada",
                    signal_text=summary[:500],
                    source_url=link,
                    published_at=published,
                    practice_area_hints=practice_areas,
                    confidence_score=strength,
                    signal_value={"source": "bank_of_canada_rss", "title": title},
                )
            )
        return signals
