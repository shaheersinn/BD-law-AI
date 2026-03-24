"""app/scrapers/news/reuters.py — Reuters Canada business/legal news."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class ReutersScraper(BaseScraper):
    source_id = "news_reuters"
    source_name = "Reuters News"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://feeds.reuters.com"
    rate_limit_rps = 0.5
    concurrency = 2
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://feeds.reuters.com/reuters/CATopNews",
        "https://feeds.reuters.com/reuters/businessNews",
    ]

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                    matched_areas.append("litigation")
                    strength = max(strength, 0.75)
                if any(k in title_lower for k in ["acquisition", "merger", "takeover"]):
                    matched_areas.append("ma_corporate")
                    strength = max(strength, 0.70)
                if any(
                    k in title_lower for k in ["bankruptcy", "ccaa", "insolvency", "restructuring"]
                ):
                    matched_areas.append("insolvency_restructuring")
                    strength = max(strength, 0.80)
                if any(
                    k in title_lower for k in ["regulatory", "investigation", "fine", "penalty"]
                ):
                    matched_areas.append("regulatory_compliance")
                    strength = max(strength, 0.70)
                if not matched_areas:
                    continue
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="news_mention",
                        raw_company_name=title,
                        signal_text=summary,
                        source_url=link,
                        published_at=published,
                        practice_area_hints=matched_areas or ["litigation"],
                        confidence_score=strength,
                        signal_value={"source": "Reuters", "title": f"Reuters: {title}"},
                    )
                )
        return signals
