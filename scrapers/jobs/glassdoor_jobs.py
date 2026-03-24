"""app/scrapers/jobs/glassdoor_jobs.py — Glassdoor legal job postings."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class GlassdoorJobsScraper(BaseScraper):
    NAME = "glassdoor_jobs"
    CATEGORY = "jobs"
    SOURCE_URL = "https://www.glassdoor.ca"
    RATE_LIMIT_RPS = 0.3
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.70

    async def run(self) -> list[SignalData]:
        """Glassdoor blocks automated scraping heavily — returns minimal signals."""
        signals = []
        # Glassdoor has aggressive bot detection; use with caution
        # Search for corporate counsel roles as proxy for legal department activity
        url = f"{self.SOURCE_URL}/Job/canada-legal-counsel-jobs-SRCH_IL.0,6_IN3_KO7,21.htm"
        soup = await self.get_soup(url)
        if not soup:
            return signals
        job_cards = soup.select("li[data-test='jobListing'], article.jobCard")
        for card in job_cards[:10]:
            title = self.safe_text(card.find(class_="job-title") or card.find("a"))
            company = self.safe_text(card.find(class_="employer-name") or card.find(class_="company"))
            if not title or not company:
                continue
            signals.append(SignalData(
                scraper_name=self.NAME, signal_type="job_posting",
                raw_entity_name=company, title=f"Glassdoor: {title} at {company}",
                summary=f"Legal job posting: {title} at {company}",
                source_url=self.SOURCE_URL,
                practice_areas=["employment_labour", "regulatory_compliance"],
                signal_strength=0.55,
                metadata={"platform": "Glassdoor"},
            ))
        return signals
