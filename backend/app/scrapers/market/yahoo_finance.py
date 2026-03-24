"""app/scrapers/market/yahoo_finance.py — Yahoo Finance RSS and market data."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class YahooFinanceScraper(BaseScraper):
    source_id = "market_yahoo"
    source_name = "Yahoo Finance"
    CATEGORY = "market"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://finance.yahoo.com"
    rate_limit_rps = 0.5
    concurrency = 2
    SOURCE_RELIABILITY = 0.80

    _RSS_TEMPLATES = [
        "https://finance.yahoo.com/rss/topstories",
        "https://finance.yahoo.com/news/rss",
    ]

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                legal_keywords = [
                    "lawsuit",
                    "sued",
                    "settlement",
                    "regulatory",
                    "investigation",
                    "bankruptcy",
                    "ccaa",
                    "restructuring",
                    "fine",
                    "penalty",
                ]
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
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="news_mention",
                        raw_company_name=title,
                        signal_text=summary,
                        source_url=link,
                        published_at=published,
                        practice_area_hints=areas,
                        confidence_score=strength,
                        signal_value={
                            "source": "yahoo_finance",
                            "title": f"Yahoo Finance: {title}",
                        },
                    )
                )
        return signals
