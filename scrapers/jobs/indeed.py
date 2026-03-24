"""app/scrapers/jobs/indeed.py — Indeed RSS job postings scraper."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

# Legal/compliance job keywords → signals mandate need
LEGAL_JOB_KEYWORDS = {
    "litigation": ["litigation counsel", "litigation associate", "dispute resolution"],
    "regulatory_compliance": ["compliance officer", "regulatory counsel", "legal compliance", "chief compliance"],
    "privacy_cybersecurity": ["privacy counsel", "data protection", "cybersecurity counsel"],
    "employment_labour": ["labour relations", "employment counsel", "hr legal"],
    "insolvency_restructuring": ["insolvency counsel", "restructuring", "creditor"],
    "ma_corporate": ["m&a counsel", "corporate counsel", "mergers and acquisitions"],
    "securities_capital_markets": ["securities counsel", "capital markets", "securities lawyer"],
}

class IndeedScraper(BaseScraper):
    NAME = "indeed_jobs"
    CATEGORY = "jobs"
    SOURCE_URL = "https://ca.indeed.com"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.75

    async def run(self) -> list[SignalData]:
        signals = []
        for area, keywords in LEGAL_JOB_KEYWORDS.items():
            for keyword in keywords[:2]:  # 2 keywords per area to respect rate limit
                rss_url = f"{self.SOURCE_URL}/rss?q={keyword.replace(" ", "+")}&l=Canada&radius=100"
                feed = await self.get_rss(rss_url)
                if not feed:
                    continue
                for entry in feed.get("entries", [])[:5]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = entry.get("summary", "")[:300]
                    published = self.parse_date(entry.get("published"))
                    company = entry.get("author", "")
                    if not title:
                        continue
                    signals.append(SignalData(
                        scraper_name=self.NAME, signal_type="job_posting",
                        raw_entity_name=company or title,
                        title=f"Indeed job: {title}",
                        summary=f"Legal job posting: {title} — {summary}",
                        source_url=link, published_at=published,
                        practice_areas=[area, "employment_labour"],
                        signal_strength=0.60,
                        metadata={"keyword": keyword, "platform": "Indeed"},
                    ))
        return signals
