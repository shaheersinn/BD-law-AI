"""app/scrapers/news/seeking_alpha.py — Seeking Alpha / Motley Fool Canadian news."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class SeekingAlphaScraper(BaseScraper):
    source_id = "news_seeking_alpha"
    source_name = "Seeking Alpha"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://seekingalpha.com"
    rate_limit_rps = 0.3
    concurrency = 1
    SOURCE_RELIABILITY = 0.65

    _RSS_URLS = [
        "https://seekingalpha.com/tag/canada.xml",
        "https://seekingalpha.com/market-news/rss.xml",
    ]

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                    areas.insert(0, "class_actions")
                    strength = 0.70
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
                            "source": "Seeking Alpha",
                            "title": f"Seeking Alpha: {title}",
                        },
                    )
                )
        return signals
