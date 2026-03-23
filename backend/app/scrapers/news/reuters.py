"""app/scrapers/news/reuters.py — Reuters Canada business/legal news."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class ReutersScraper(BaseScraper):
    NAME = "reuters_news"
    CATEGORY = "news"
    SOURCE_URL = "https://feeds.reuters.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://feeds.reuters.com/reuters/CATopNews",
        "https://feeds.reuters.com/reuters/businessNews",
    ]

    async def run(self) -> list[SignalData]:
        signals = []
        legal_keywords = ["lawsuit", "sued", "settlement", "investigation", "fine",
                          "penalty", "bankruptcy", "acquisition", "merger", "regulatory"]
        for rss_url in self._RSS_URLS:
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:20]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:400]
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                title_lower = title.lower() + " " + summary.lower()
                matched_areas, strength = [], 0.50
                if any(k in title_lower for k in ["lawsuit", "sued", "class action", "settlement"]):
                    matched_areas.append("litigation"); strength = max(strength, 0.75)
                if any(k in title_lower for k in ["acquisition", "merger", "takeover"]):
                    matched_areas.append("ma_corporate"); strength = max(strength, 0.70)
                if any(k in title_lower for k in ["bankruptcy", "ccaa", "insolvency", "restructuring"]):
                    matched_areas.append("insolvency_restructuring"); strength = max(strength, 0.80)
                if any(k in title_lower for k in ["regulatory", "investigation", "fine", "penalty"]):
                    matched_areas.append("regulatory_compliance"); strength = max(strength, 0.70)
                if not matched_areas:
                    continue
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title, title=f"Reuters: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=matched_areas or ["litigation"], signal_strength=strength,
                    metadata={"source": "Reuters"},
                ))
        return signals
