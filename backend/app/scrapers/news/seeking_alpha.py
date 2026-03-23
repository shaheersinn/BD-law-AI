"""app/scrapers/news/seeking_alpha.py — Seeking Alpha / Motley Fool Canadian news."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class SeekingAlphaScraper(BaseScraper):
    NAME = "seeking_alpha"
    CATEGORY = "news"
    SOURCE_URL = "https://seekingalpha.com"
    RATE_LIMIT_RPS = 0.3
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.65

    _RSS_URLS = [
        "https://seekingalpha.com/tag/canada.xml",
        "https://seekingalpha.com/market-news/rss.xml",
    ]

    async def run(self) -> list[SignalData]:
        signals = []
        for rss_url in self._RSS_URLS:
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:300]
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                title_lower = title.lower()
                areas = ["securities_capital_markets"]
                strength = 0.55
                if any(k in title_lower for k in ["lawsuit", "class action"]):
                    areas.insert(0, "class_actions"); strength = 0.70
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title, title=f"Seeking Alpha: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=areas, signal_strength=strength,
                    metadata={"source": "Seeking Alpha"},
                ))
        return signals
