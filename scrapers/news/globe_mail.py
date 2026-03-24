"""app/scrapers/news/globe_mail.py — Globe and Mail business/legal news."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class GlobeMailScraper(BaseScraper):
    NAME = "globe_mail"
    CATEGORY = "news"
    SOURCE_URL = "https://www.theglobeandmail.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://www.theglobeandmail.com/business/?service=rss",
        "https://www.theglobeandmail.com/news/national/?service=rss",
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
                areas, strength = ["securities_capital_markets"], 0.60
                if "lawsuit" in title_lower or "sued" in title_lower:
                    areas.insert(0, "litigation"); strength = 0.75
                elif "acquisition" in title_lower or "merger" in title_lower:
                    areas.insert(0, "ma_corporate"); strength = 0.70
                elif "insolvency" in title_lower or "bankruptcy" in title_lower or "ccaa" in title_lower:
                    areas.insert(0, "insolvency_restructuring"); strength = 0.80
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title, title=f"Globe and Mail: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=areas, signal_strength=strength,
                    metadata={"source": "Globe and Mail"},
                ))
        return signals
