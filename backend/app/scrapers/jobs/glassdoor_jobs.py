"""app/scrapers/jobs/glassdoor_jobs.py — Glassdoor legal job postings."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class GlassdoorJobsScraper(BaseScraper):
    source_id = "jobs_glassdoor"
    source_name = "Glassdoor Jobs"
    CATEGORY = "jobs"
    signal_types = ["job_posting"]
    SOURCE_URL = "https://www.glassdoor.ca"
    rate_limit_rps = 0.3
    concurrency = 1
    SOURCE_RELIABILITY = 0.70

    async def scrape(self) -> list[SignalData]:
        """Glassdoor blocks automated scraping heavily — returns minimal signals."""
        signals: list[SignalData] = []
        # Glassdoor has aggressive bot detection; use with caution
        # Search for corporate counsel roles as proxy for legal department activity
        url = f"{self.SOURCE_URL}/Job/canada-legal-counsel-jobs-SRCH_IL.0,6_IN3_KO7,21.htm"
        soup = await self.get_soup(url)
        if not soup:
            return signals
        job_cards = soup.select("li[data-test='jobListing'], article.jobCard")
        for card in job_cards[:10]:
            title = self.safe_text(card.find(class_="job-title") or card.find("a"))
            company = self.safe_text(
                card.find(class_="employer-name") or card.find(class_="company")
            )
            if not title or not company:
                continue
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="job_posting",
                    raw_company_name=company,
                    signal_text=f"Legal job posting: {title} at {company}",
                    source_url=self.SOURCE_URL,
                    practice_area_hints=["employment_labour", "regulatory_compliance"],
                    confidence_score=0.55,
                    signal_value={
                        "platform": "Glassdoor",
                        "title": f"Glassdoor: {title} at {company}",
                    },
                )
            )
        return signals
