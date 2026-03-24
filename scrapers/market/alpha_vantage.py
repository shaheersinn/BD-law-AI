"""app/scrapers/market/alpha_vantage.py — Alpha Vantage market data (25 req/day free)."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData
from app.scrapers.budget_manager import get_budget_manager

class AlphaVantageScraper(BaseScraper):
    NAME = "alpha_vantage"
    CATEGORY = "market"
    SOURCE_URL = "https://www.alphavantage.co/query"
    RATE_LIMIT_RPS = 0.2
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.85
    API_KEY_ENV_VAR = "ALPHA_VANTAGE_API_KEY"

    async def run(self) -> list[SignalData]:
        signals = []
        if not self._api_key:
            return signals
        bm = get_budget_manager()
        companies = await self._load_top_companies()
        for company in companies[:5]:  # Max 5 lookups per run (budget)
            if not await bm.check_budget("alpha_vantage", 1):
                break
            ticker = company.get("ticker", "")
            if not ticker:
                continue
            data = await self.get_json(self.SOURCE_URL, params={
                "function": "GLOBAL_QUOTE",
                "symbol": f"{ticker}.TRT",  # Toronto Stock Exchange suffix
                "apikey": self._api_key,
            })
            if not data:
                continue
            await bm.consume("alpha_vantage", 1)
            quote = data.get("Global Quote", {})
            change_pct = float(quote.get("10. change percent", "0%").replace("%", "") or 0)
            if abs(change_pct) < 5:
                continue
            signals.append(SignalData(
                scraper_name=self.NAME, signal_type="market_signal",
                raw_entity_name=company.get("name", ticker),
                title=f"Alpha Vantage: {ticker} {change_pct:+.1f}%",
                summary=f"Significant price movement: {company.get("name", ticker)} {change_pct:+.1f}%",
                source_url=f"https://finance.yahoo.com/quote/{ticker}",
                practice_areas=["securities_capital_markets"],
                signal_strength=min(0.85, 0.50 + abs(change_pct) / 20),
                metadata={"ticker": ticker, "change_pct": change_pct, "quote": quote},
            ))
        return signals

    async def _load_top_companies(self) -> list[dict]:
        try:
            from app.database import AsyncSessionLocal
            from app.models.company import Company
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company.id, Company.name, Company.ticker)
                    .where(Company.is_active == True).where(Company.watchlist_priority == 1)
                    .limit(20)
                )
                return [{"id": r.id, "name": r.name, "ticker": r.ticker} for r in result.all()]
        except Exception:
            return []
