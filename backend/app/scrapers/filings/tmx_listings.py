"""app/scrapers/filings/tmx_listings.py — TMX/TSX company listings for company table bootstrap."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class TmxListingsScraper(BaseScraper):
    source_id = "corporate_tmx"
    source_name = "TMX Listings"
    CATEGORY = "corporate"
    signal_types = ["signal"]
    SOURCE_URL = "https://www.tmx.com"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.95

    _LISTINGS_API = "https://api.tmxmoney.com/en/canaccord/getListings"

    async def scrape(self) -> list[SignalData]:
        """Fetch TSX/TSXV company listings to keep company table current."""
        signals: list[SignalData] = []
        data = await self.get_json(self._LISTINGS_API)
        if data is None:
            return signals
        companies = data if isinstance(data, list) else data.get("results", [])
        for company in companies[:500]:
            ticker = company.get("symbol", company.get("ticker", ""))
            name = company.get("name", company.get("issuerName", ""))
            exchange = company.get("exchange", "TSX")
            sector = company.get("sector", "")
            if not name or not ticker:
                continue
            # Upsert to company table
            await self._upsert_company(name, ticker, exchange, sector)
        self._log.info("TMX: processed %d listings", len(companies))
        return signals  # No signals — this is a company table bootstrap

    async def _upsert_company(self, name: str, ticker: str, exchange: str, sector: str) -> None:
        try:
            import re

            from sqlalchemy import select

            from app.database import AsyncSessionLocal
            from app.models.company import Company

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Company).where(Company.ticker == ticker))
                company = result.scalar_one_or_none()
                if company is None:
                    company = Company(
                        name=name,
                        name_normalized=re.sub(r"[^\w\s]", "", name).lower().strip(),
                        ticker=ticker,
                        exchange=exchange,
                        sector=sector,
                        jurisdiction="ON",
                        watchlist_priority=2 if exchange == "TSX" else 3,
                    )
                    db.add(company)
                else:
                    company.exchange = exchange
                    company.sector = sector or company.sector
                await db.commit()
        except Exception as exc:
            self._log.debug("TMX: upsert error %s: %s", ticker, exc)
