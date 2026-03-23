"""app/scrapers/jobs/job_bank.py — Government of Canada Job Bank RSS."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class JobBankScraper(BaseScraper):
    NAME = "job_bank"
    CATEGORY = "jobs"
    SOURCE_URL = "https://www.jobbank.gc.ca"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.75

    _RSS_TEMPLATES = [
        "https://www.jobbank.gc.ca/jobsearch/rss?searchstring=legal+counsel&locationstring=Canada",
        "https://www.jobbank.gc.ca/jobsearch/rss?searchstring=compliance+officer&locationstring=Canada",
    ]

    async def run(self) -> list[SignalData]:
        signals = []
        for rss_url in self._RSS_TEMPLATES:
            feed = await self.get_rss(rss_url)
            if not feed:
                continue
            for entry in feed.get("entries", [])[:10]:
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
                    title=f"Job Bank: {title}",
                    summary=summary, source_url=link, published_at=published,
                    practice_areas=["employment_labour", "regulatory_compliance"],
                    signal_strength=0.55,
                    metadata={"platform": "Job Bank Canada"},
                ))
        return signals
