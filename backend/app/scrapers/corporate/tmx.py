"""
TMX Group scraper — TSX/TSXV company news and trading halts.
Source: https://www.tmx.com/resource/en/440 (trading halts)
        TMX DataLinx for market data (requires subscription)
Signals: market_trading_halt, market_company_news
"""

from __future__ import annotations

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TMX_HALTS = "https://www.tsx.com/json/company-directory/search/tsx/^HALT"
_TMX_NEWS_RSS = "https://www.tmx.com/rss/tmxmoney/en/market_news.rss"


@register
class TMXScraper(BaseScraper):
    source_id = "corporate_tmx"
    source_name = "TMX Group (TSX/TSXV)"
    signal_types = ["market_trading_halt", "market_company_news"]
    rate_limit_rps = 0.3
    concurrency = 2
    ttl_seconds = 1800  # 30 min

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # Trading halts are very high signal — often precede material change disclosures
            response = await self.get(
                "https://www.tsx.com/trading/market-data-and-statistics/market-statistics-and-reports/market-alerts"
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Extract trading halt notices
                halt_tables = soup.find_all("table")
                for table in halt_tables:
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cells = row.find_all("td")
                        if len(cells) >= 3:
                            ticker = cells[0].get_text(strip=True)
                            company = cells[1].get_text(strip=True)
                            reason = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                            if ticker:
                                results.append(
                                    ScraperResult(
                                        source_id=self.source_id,
                                        signal_type="market_trading_halt",
                                        raw_company_name=company,
                                        signal_value={"ticker": ticker, "reason": reason},
                                        signal_text=f"Trading halt: {company} ({ticker}) — {reason}",
                                        practice_area_hints=["securities", "ma"],
                                        raw_payload={
                                            "ticker": ticker,
                                            "company": company,
                                            "reason": reason,
                                        },
                                    )
                                )
        except Exception as exc:
            log.error("tmx_error", error=str(exc))
        return results
