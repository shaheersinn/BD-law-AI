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
    ("environmental fine Canada", ["environmental_indigenous_energy", "regulatory_compliance"], 0.70),
]

class GoogleNewsScraper(BaseScraper):
    NAME = "google_news"
    CATEGORY = "news"
    SOURCE_URL = "https://news.google.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.70

    async def run(self) -> list[SignalData]:
        signals = []
        for query, areas, strength in SEARCH_QUERIES:
            rss_url = f"https://news.google.com/rss/search?q={query.replace(" ", "+")}&hl=en-CA&gl=CA&ceid=CA:en"
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="news_mention",
                    raw_entity_name=title,
                    title=title, summary=f"Google News ({query}): {title}",
                    source_url=link, published_at=published,
                    practice_areas=areas, signal_strength=strength,
                    metadata={"query": query},
                ))
        return signals
