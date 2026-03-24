"""app/scrapers/market/yahoo_finance.py — Yahoo Finance RSS and market data."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class YahooFinanceScraper(BaseScraper):
    NAME = "yahoo_finance"
    CATEGORY = "market"
    SOURCE_URL = "https://finance.yahoo.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.80

    _RSS_TEMPLATES = [
        "https://finance.yahoo.com/rss/topstories",
        "https://finance.yahoo.com/news/rss",
    ]

    async def run(self) -> list[SignalData]:
        signals = []
        for rss_url in self._RSS_TEMPLATES:
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:15]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:400]
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                # Detect Canadian companies in headlines
                ca_keywords = ["tsx", "canadian", "canada", "toronto", "calgary", "vancouver"]
                legal_keywords = ["lawsuit", "sued", "settlement", "regulatory", "investigation",
                                  "bankruptcy", "ccaa", "restructuring", "fine", "penalty"]
                title_lower = title.lower()
                if not any(kw in title_lower for kw in ca_keywords + legal_keywords):
                    continue
                areas = ["securities_capital_markets"]
                strength = 0.55
                for kw in legal_keywords:
                    if kw in title_lower:
                        strength = 0.70
                        areas.insert(0, "litigation")
                        break
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title,
                    title=f"Yahoo Finance: {title}", summary=summary,
                    source_url=link, published_at=published,
                    practice_areas=areas, signal_strength=strength,
                    metadata={"source": "yahoo_finance"},
                ))
        return signals
