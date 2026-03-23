"""app/scrapers/regulatory/competition_bureau.py — Competition Bureau scraper."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class CompetitionBureauScraper(BaseScraper):
    NAME = "competition_bureau"
    CATEGORY = "regulatory"
    SOURCE_URL = "https://www.canada.ca/en/competition-bureau"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.95
    _URL = "https://www.canada.ca/en/competition-bureau/news/recent-actions.html"

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
                    raw_entity_name=title, title=f"Competition Bureau: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=["competition_antitrust", "regulatory_compliance"],
                    signal_strength=0.95,
                    metadata={"regulator": "Competition Bureau"},
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
                raw_entity_name=title, title=f"Competition Bureau: {title}",
                summary=f"Competition Bureau action: {title}",
                source_url=link, published_at=self.parse_date(date_str),
                practice_areas=["competition_antitrust", "regulatory_compliance"],
                signal_strength=0.95,
                metadata={"regulator": "Competition Bureau"},
            ))
        return signals
