"""app/scrapers/news/globe_mail.py — Globe and Mail business/legal news."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class GlobeMailScraper(BaseScraper):
    source_id = "news_globe"
    source_name = "Globe and Mail"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://www.theglobeandmail.com"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://www.theglobeandmail.com/business/?service=rss",
        "https://www.theglobeandmail.com/news/national/?service=rss",
    ]

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                    areas.insert(0, "litigation")
                    strength = 0.75
                elif "acquisition" in title_lower or "merger" in title_lower:
                    areas.insert(0, "ma_corporate")
                    strength = 0.70
                elif (
                    "insolvency" in title_lower
                    or "bankruptcy" in title_lower
                    or "ccaa" in title_lower
                ):
                    areas.insert(0, "insolvency_restructuring")
                    strength = 0.80
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
                            "source": "Globe and Mail",
                            "title": f"Globe and Mail: {title}",
                        },
                    )
                )
        return signals
