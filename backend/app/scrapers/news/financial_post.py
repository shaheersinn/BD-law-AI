"""app/scrapers/news/financial_post.py — Financial Post news RSS."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class FinancialPostScraper(BaseScraper):
    NAME = "financial_post"
    CATEGORY = "news"
    SOURCE_URL = "https://financialpost.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://financialpost.com/category/news/rss.xml",
        "https://financialpost.com/category/financial-times/rss.xml",
    ]

    async def run(self) -> list[SignalData]:
        signals = []
        for rss_url in self._RSS_URLS:
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
                title_lower = title.lower()
                areas = ["securities_capital_markets"]
                strength = 0.60
                for kw, area in [("lawsuit", "litigation"), ("acquisition", "ma_corporate"),
                                  ("bankruptcy", "insolvency_restructuring"), ("regulatory", "regulatory_compliance")]:
                    if kw in title_lower:
                        areas.insert(0, area); strength = 0.70; break
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title, title=f"Financial Post: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=areas, signal_strength=strength,
                    metadata={"source": "Financial Post"},
                ))
        return signals
