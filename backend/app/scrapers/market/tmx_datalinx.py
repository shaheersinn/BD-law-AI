"""app/scrapers/market/tmx_datalinx.py — TMX DataLinx market data."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class TmxDatalinxScraper(BaseScraper):
    source_id = "market_tmx"
    source_name = "TMX DataLinx"
    CATEGORY = "market"
    signal_types = ["market_signal"]
    SOURCE_URL = "https://api.tmxmoney.com"
    rate_limit_rps = 1.0
    concurrency = 3
    SOURCE_RELIABILITY = 0.90

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="market_signal",
                        raw_company_name=company_name,
                        signal_text=f"Unusual market activity: {company_name} ({symbol}) {pctchange:+.1f}% change",
                        source_url=f"https://money.tmx.com/en/quote/{symbol}",
                        practice_area_hints=areas,
                        confidence_score=float(strength),
                        signal_value={
                            "ticker": symbol,
                            "pct_change": pctchange,
                            "volume": volume,
                            "title": f"TMX: {symbol} {pctchange:+.1f}% on {volume:,} volume",
                        },
                    )
                )
            break  # One API call returns top actives
        return signals

    async def _load_tsx_companies(self) -> list[dict]:
        try:
            from sqlalchemy import select

            from app.database import AsyncSessionLocal
            from app.models.company import Company

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company.id, Company.name, Company.ticker)
                    .where(Company.is_active)
                    .where(Company.exchange == "TSX")
                    .limit(100)
                )
                return [{"id": r.id, "name": r.name, "ticker": r.ticker} for r in result.all()]
        except Exception:
            return []
