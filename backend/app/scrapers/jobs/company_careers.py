"""app/scrapers/jobs/company_careers.py — Direct company career page monitoring."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData

# Target companies with career page URLs for direct monitoring
# Expanded in Phase 1C based on scraper performance review
CAREER_PAGES = {
    "Royal Bank of Canada": "https://jobs.rbc.com/ca/en/search-results?keywords=legal",
    "TD Bank": "https://jobs.td.com/en-CA/search/#q=legal&t=",
    "Suncor Energy": "https://www.suncor.com/en-ca/careers/search?q=legal",
    "Shopify": "https://www.shopify.com/careers/search?keywords=legal",
    "Brookfield": "https://brk.wd1.myworkdayjobs.com/External/jobs?q=legal",
}


class CompanyCareersScraper(BaseScraper):
    source_id = "jobs_company_careers"
    source_name = "Company Careers"
    CATEGORY = "jobs"
    signal_types = ["job_posting"]
    SOURCE_URL = "https://careers.oracle-bd.internal"
    rate_limit_rps = 0.2
    concurrency = 1
    SOURCE_RELIABILITY = 0.80

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        for company_name, career_url in CAREER_PAGES.items():
            try:
                soup = await self.get_soup(career_url)
                if not soup:
                    continue
                jobs = soup.select("li[data-automation=job-title], div.job-listing, article.job")
                for job in jobs[:5]:
                    title = self.safe_text(job.find("a") or job.find("h3") or job)
                    if not title or len(title) < 5:
                        continue
                    signals.append(
                        SignalData(
                            source_id=self.source_id,
                            signal_type="job_posting",
                            raw_company_name=company_name,
                            signal_text=f"Legal job posting on {company_name} careers page: {title}",
                            source_url=career_url,
                            practice_area_hints=["employment_labour", "regulatory_compliance"],
                            confidence_score=0.70,
                            signal_value={
                                "company": company_name,
                                "source": "direct_careers",
                                "title": f"Career: {title} at {company_name}",
                            },
                        )
                    )
            except Exception as exc:
                self.log.debug("Careers: error on %s: %s", company_name, exc)
        return signals
