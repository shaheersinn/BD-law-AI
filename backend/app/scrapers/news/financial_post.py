"""app/scrapers/news/financial_post.py — Financial Post news RSS."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class FinancialPostScraper(BaseScraper):
    source_id = "news_fp"
    source_name = "Financial Post"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://financialpost.com"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.85

    _RSS_URLS = [
        "https://financialpost.com/category/news/rss.xml",
        "https://financialpost.com/category/financial-times/rss.xml",
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
                areas = ["securities_capital_markets"]
                strength = 0.60
                for kw, area in [
                    ("lawsuit", "litigation"),
                    ("acquisition", "ma_corporate"),
                    ("bankruptcy", "insolvency_restructuring"),
                    ("regulatory", "regulatory_compliance"),
                ]:
                    if kw in title_lower:
                        areas.insert(0, area)
                        strength = 0.70
                        break
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
                            "source": "Financial Post",
                            "title": f"Financial Post: {title}",
                        },
                    )
                )
        return signals
