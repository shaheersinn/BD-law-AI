"""app/scrapers/news/cbc_business.py — CBC Business news RSS."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class CbcBusinessScraper(BaseScraper):
    source_id = "news_cbc"
    source_name = "CBC Business"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://www.cbc.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.80

    _RSS_URL = "https://www.cbc.ca/cmlink/rss-business"

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                areas.insert(0, "litigation")
                strength = 0.75
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
                    signal_value={"source": "CBC Business", "title": f"CBC: {title}"},
                )
            )
        return signals
