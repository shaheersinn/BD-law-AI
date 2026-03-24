"""app/scrapers/regulatory/us_doj.py — US DOJ scraper."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class UsDojScraper(BaseScraper):
    NAME = "us_doj_actions"
    CATEGORY = "regulatory"
    SOURCE_URL = "https://www.justice.gov"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.85
    _URL = "https://www.justice.gov/news"

    async def run(self) -> list[SignalData]:
        signals: list[SignalData] = []
        # Try RSS first
        feed = await self.get_rss(self._URL)
        if feed and feed.get("entries"):
            for entry in feed.get("entries", [])[:20]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:500]
                published = self.parse_date(entry.get("published"))
                if not title:
                    continue
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="enforcement_action",
                    raw_entity_name=title, title=f"US DOJ: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=["litigation", "regulatory_compliance"],
                    signal_strength=0.85,
                    metadata={"regulator": "US DOJ"},
                ))
            return signals
        # HTML fallback
        soup = await self.get_soup(self._URL)
        if not soup:
            return signals
        items = soup.select("article, li.action-item, table tbody tr, div.enforcement-item, ul.results li")
        for item in items[:20]:
            link_tag = item.find("a")
            title_el = link_tag or item.find("h3") or item.find("h4") or item
            title = self.safe_text(title_el)
            link = link_tag.get("href", "") if link_tag else ""
            if link and not link.startswith("http"):
                link = f"{self.SOURCE_URL}{link}"
            date_el = item.find("time") or item.find(class_="date") or item.find(class_="published")
            date_str = self.safe_text(date_el)
            if not title or len(title) < 5:
                continue
            signals.append(SignalData(
                scraper_name=self.NAME, signal_type="enforcement_action",
                raw_entity_name=title, title=f"US DOJ: {title}",
                summary=f"US DOJ action: {title}",
                source_url=link, published_at=self.parse_date(date_str),
                practice_areas=["litigation", "regulatory_compliance"],
                signal_strength=0.85,
                metadata={"regulator": "US DOJ"},
            ))
        return signals
