"""app/scrapers/jobs/indeed.py — Indeed RSS job postings scraper."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData

# Legal/compliance job keywords → signals mandate need
LEGAL_JOB_KEYWORDS = {
    "litigation": ["litigation counsel", "litigation associate", "dispute resolution"],
    "regulatory_compliance": [
        "compliance officer",
        "regulatory counsel",
        "legal compliance",
        "chief compliance",
    ],
    "privacy_cybersecurity": ["privacy counsel", "data protection", "cybersecurity counsel"],
    "employment_labour": ["labour relations", "employment counsel", "hr legal"],
    "insolvency_restructuring": ["insolvency counsel", "restructuring", "creditor"],
    "ma_corporate": ["m&a counsel", "corporate counsel", "mergers and acquisitions"],
    "securities_capital_markets": ["securities counsel", "capital markets", "securities lawyer"],
}


class IndeedScraper(BaseScraper):
    source_id = "jobs_indeed"
    source_name = "Indeed Jobs"
    CATEGORY = "jobs"
    signal_types = ["job_posting"]
    SOURCE_URL = "https://ca.indeed.com"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.75

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        for area, keywords in LEGAL_JOB_KEYWORDS.items():
            for keyword in keywords[:2]:  # 2 keywords per area to respect rate limit
                rss_url = f"{self.SOURCE_URL}/rss?q={keyword.replace(' ', '+')}&l=Canada&radius=100"
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
                    signals.append(
                        SignalData(
                            source_id=self.source_id,
                            signal_type="job_posting",
                            raw_company_name=company or title,
                            signal_text=f"Legal job posting: {title} — {summary}",
                            source_url=link,
                            published_at=published,
                            practice_area_hints=[area, "employment_labour"],
                            confidence_score=0.60,
                            signal_value={
                                "keyword": keyword,
                                "platform": "Indeed",
                                "title": f"Indeed job: {title}",
                            },
                        )
                    )
        return signals
