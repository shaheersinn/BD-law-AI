"""app/scrapers/news/google_news.py — Google News RSS for Canadian legal topics."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData

SEARCH_QUERIES = [
    ("lawsuit Canada corporate", ["litigation", "securities_capital_markets"], 0.65),
    ("CCAA insolvency Canada", ["insolvency_restructuring", "banking_finance"], 0.80),
    ("OSC enforcement action", ["securities_capital_markets", "financial_regulatory"], 0.85),
    ("class action Canada", ["class_actions", "litigation"], 0.75),
    ("M&A acquisition Canada", ["ma_corporate", "securities_capital_markets"], 0.65),
    ("regulatory investigation Canada", ["regulatory_compliance", "litigation"], 0.70),
    ("data breach privacy Canada", ["privacy_cybersecurity", "data_privacy_technology"], 0.75),
    (
        "environmental fine Canada",
        ["environmental_indigenous_energy", "regulatory_compliance"],
        0.70,
    ),
]


class GoogleNewsScraper(BaseScraper):
    source_id = "news_google"
    source_name = "Google News"
    CATEGORY = "news"
    signal_types = ["news_mention"]
    SOURCE_URL = "https://news.google.com"
    rate_limit_rps = 0.5
    concurrency = 2
    SOURCE_RELIABILITY = 0.70

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        for query, areas, strength in SEARCH_QUERIES:
            rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-CA&gl=CA&ceid=CA:en"
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="news_mention",
                        raw_company_name=title,
                        signal_text=f"Google News ({query}): {title}",
                        source_url=link,
                        published_at=published,
                        practice_area_hints=areas,
                        confidence_score=strength,
                        signal_value={"query": query, "title": title},
                    )
                )
        return signals
