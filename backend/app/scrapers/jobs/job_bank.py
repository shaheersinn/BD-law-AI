"""app/scrapers/jobs/job_bank.py — Government of Canada Job Bank RSS."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class JobBankScraper(BaseScraper):
    source_id = "jobs_job_bank"
    source_name = "Job Bank Canada"
    CATEGORY = "jobs"
    signal_types = ["job_posting"]
    SOURCE_URL = "https://www.jobbank.gc.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.75

    _RSS_TEMPLATES = [
        "https://www.jobbank.gc.ca/jobsearch/rss?searchstring=legal+counsel&locationstring=Canada",
        "https://www.jobbank.gc.ca/jobsearch/rss?searchstring=compliance+officer&locationstring=Canada",
    ]

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
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
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="job_posting",
                        raw_company_name=company or title,
                        signal_text=summary,
                        source_url=link,
                        published_at=published,
                        practice_area_hints=["employment_labour", "regulatory_compliance"],
                        confidence_score=0.55,
                        signal_value={"platform": "Job Bank Canada", "title": f"Job Bank: {title}"},
                    )
                )
        return signals
