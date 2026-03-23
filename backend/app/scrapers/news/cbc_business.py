"""app/scrapers/news/cbc_business.py — CBC Business news RSS."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class CbcBusinessScraper(BaseScraper):
    NAME = "cbc_business"
    CATEGORY = "news"
    SOURCE_URL = "https://www.cbc.ca"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.80

    _RSS_URL = "https://www.cbc.ca/cmlink/rss-business"

    async def run(self) -> list[SignalData]:
        signals = []
        feed = await self.get_rss(self._RSS_URL)
        if not feed:
            return signals
        for entry in feed.get("entries", [])[:20]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")[:400]
            published = self.parse_date(entry.get("published"))
            if not title:
                continue
            areas = ["securities_capital_markets"]
            strength = 0.55
            title_lower = title.lower()
            if "investigation" in title_lower or "charged" in title_lower:
                areas.insert(0, "litigation"); strength = 0.75
            signals.append(SignalData(
                scraper_name=self.NAME, signal_type="news_mention",
                raw_entity_name=title, title=f"CBC: {title}",
                summary=summary, source_url=link, published_at=published,
                practice_areas=areas, signal_strength=strength,
                metadata={"source": "CBC Business"},
            ))
        return signals
