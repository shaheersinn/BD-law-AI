"""app/scrapers/filings/canada_gazette.py — Canada Gazette regulations scraper."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData

# Practice area keywords in regulation titles
GAZETTE_KEYWORDS = {
    "privacy_cybersecurity": ["personal information", "privacy", "cybersecurity", "data breach"],
    "environmental_indigenous_energy": [
        "environment",
        "carbon",
        "emissions",
        "indigenous",
        "energy",
    ],
    "financial_regulatory": ["bank act", "insurance", "trust", "loan", "financial institutions"],
    "health_life_sciences": ["food", "drug", "medical device", "health", "therapeutic"],
    "employment_labour": ["employment", "labour", "workplace", "pension", "benefits"],
    "competition_antitrust": ["competition act", "merger", "abuse of dominance"],
    "tax": ["income tax", "excise", "gst", "hst", "customs tariff"],
}


class CanadaGazetteScraper(BaseScraper):
    source_id = "corporate_gazette"
    source_name = "Canada Gazette"
    CATEGORY = "corporate"
    signal_types = ["regulation_published"]
    SOURCE_URL = "https://gazette.gc.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.95

    _RSS_URL = "https://gazette.gc.ca/rss/p2-eng.xml"  # Part II = final regulations

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        feed = await self.get_rss(self._RSS_URL)
        if feed is None:
            return signals
        for entry in feed.get("entries", [])[:30]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            published = self.parse_date(entry.get("published"))
            if not title:
                continue
            # Detect practice areas from regulation title
            practice_areas = ["regulatory_compliance", "administrative_public_law"]
            strength = 0.55
            title_lower = title.lower()
            for area, keywords in GAZETTE_KEYWORDS.items():
                if any(kw in title_lower for kw in keywords):
                    practice_areas.insert(0, area)
                    strength = 0.70
                    break
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="regulation_published",
                    raw_company_name="Canada Gazette",
                    signal_text=summary[:500],
                    source_url=link,
                    published_at=published,
                    practice_area_hints=practice_areas,
                    confidence_score=strength,
                    signal_value={"gazette_part": "II", "source": "canada_gazette", "title": title},
                )
            )
        return signals
