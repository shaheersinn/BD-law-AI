"""app/scrapers/news/bnn_bloomberg.py — BNN Bloomberg Canadian financial news."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class BnnBloombergScraper(BaseScraper):
    source_id = "news_bnn"
    source_name = "BNN Bloomberg"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://www.bnnbloomberg.ca"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.85

    _RSS_URL = "https://www.bnnbloomberg.ca/personalization/rss/home"

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        feed = await self.get_rss(self._RSS_URL)
        if not feed:
            return signals
        for entry in feed.get("entries", [])[:15]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")[:400]
            published = self.parse_date(entry.get("published"))
            if not title:
                continue
            title_lower = title.lower()
            areas = ["securities_capital_markets"]
            strength = 0.65
            if any(k in title_lower for k in ["lawsuit", "sued", "settlement"]):
                areas.insert(0, "litigation")
                strength = 0.75
            elif any(k in title_lower for k in ["acquisition", "deal", "takeover"]):
                areas.insert(0, "ma_corporate")
                strength = 0.70
            elif any(k in title_lower for k in ["bankruptcy", "insolvency", "ccaa"]):
                areas.insert(0, "insolvency_restructuring")
                strength = 0.82
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
                    signal_value={"source": "BNN Bloomberg", "title": f"BNN Bloomberg: {title}"},
                )
            )
        return signals
