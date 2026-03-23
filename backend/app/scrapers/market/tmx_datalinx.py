"""app/scrapers/market/tmx_datalinx.py — TMX DataLinx market data."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class TmxDatalinxScraper(BaseScraper):
    NAME = "tmx_datalinx"
    CATEGORY = "market"
    SOURCE_URL = "https://api.tmxmoney.com"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 3
    SOURCE_RELIABILITY = 0.90

    async def run(self) -> list[SignalData]:
        signals = []
        companies = await self._load_tsx_companies()
        for company in companies[:50]:
            ticker = company.get("ticker", "")
            if not ticker:
                continue
            url = f"{self.SOURCE_URL}/en/json/search/searchMostActive.json"
            data = await self.get_json(url, params={"locale": "EN", "market": "T"})
            if not data:
                continue
            for item in data.get("mostactives", {}).get("security", []):
                symbol = item.get("symbol", "")
                pctchange = float(item.get("pctchange", 0) or 0)
                volume = int(item.get("volume", 0) or 0)
                company_name = item.get("name", "")
                if abs(pctchange) < 5 and volume < 1000000:
                    continue
                strength = min(0.90, 0.50 + abs(pctchange) / 20)
                areas = ["securities_capital_markets"]
                if pctchange < -10:
                    areas.append("insolvency_restructuring")
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="market_signal",
                    raw_entity_name=company_name,
                    title=f"TMX: {symbol} {pctchange:+.1f}% on {volume:,} volume",
                    summary=f"Unusual market activity: {company_name} ({symbol}) {pctchange:+.1f}% change",
                    source_url=f"https://money.tmx.com/en/quote/{symbol}",
                    practice_areas=areas, signal_strength=float(strength),
                    metadata={"ticker": symbol, "pct_change": pctchange, "volume": volume},
                ))
            break  # One API call returns top actives
        return signals

    async def _load_tsx_companies(self) -> list[dict]:
        try:
            from app.database import AsyncSessionLocal
            from app.models.company import Company
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company.id, Company.name, Company.ticker)
                    .where(Company.is_active == True).where(Company.exchange == "TSX")
                    .limit(100)
                )
                return [{"id": r.id, "name": r.name, "ticker": r.ticker} for r in result.all()]
        except Exception:
            return []
