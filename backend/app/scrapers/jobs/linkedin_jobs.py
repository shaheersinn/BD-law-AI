"""app/scrapers/jobs/linkedin_jobs.py — LinkedIn job postings via Proxycurl."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData
from app.scrapers.budget_manager import get_budget_manager


class LinkedInJobsScraper(BaseScraper):
    source_id = "jobs_linkedin"
    source_name = "LinkedIn Jobs"
    CATEGORY = "jobs"
    signal_types = ["job_posting"]
    SOURCE_URL = "https://nubela.co/proxycurl/api"
    rate_limit_rps = 0.2
    concurrency = 1
    SOURCE_RELIABILITY = 0.80
    API_KEY_ENV_VAR = "PROXYCURL_API_KEY"

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        if not self._api_key:
            self.log.warning("LinkedIn Jobs: no Proxycurl API key")
            return signals
        bm = get_budget_manager()
        if not await bm.check_budget("proxycurl", amount=1):
            self.log.info("LinkedIn Jobs: monthly budget exhausted")
            return signals
        # Search for legal roles at target companies
        companies = await self._load_priority_companies()
        for company in companies[:5]:  # Conservative - Proxycurl costs
            url = f"{self.SOURCE_URL}/v2/linkedin/company/job"
            params = {
                "search_id": company.get("linkedin_id", ""),
                "keyword": "legal counsel",
                "geo_id": "101174742",  # Canada
            }
            data = await self.get_json(
                url, headers={"Authorization": f"Bearer {self._api_key}"}, params=params
            )
            if not data:
                continue
            await bm.consume("proxycurl", 1)
            for job in data.get("job", [])[:3]:
                title = job.get("title", "")
                company_name = job.get("company", {}).get("name", company.get("name", ""))
                if not title:
                    continue
                signals.append(
                    SignalData(
                        source_id=self.source_id,
                        signal_type="job_posting",
                        raw_company_name=company_name,
                        signal_text=f"Legal job posting on LinkedIn: {title}",
                        source_url=job.get("url", self.SOURCE_URL),
                        practice_area_hints=["employment_labour", "regulatory_compliance"],
                        confidence_score=0.65,
                        signal_value={
                            "platform": "LinkedIn",
                            "company": company_name,
                            "title": f"LinkedIn: {title} at {company_name}",
                        },
                    )
                )
        return signals

    async def _load_priority_companies(self) -> list[dict]:
        try:
            from sqlalchemy import select

            from app.database import AsyncSessionLocal
            from app.models.company import Company

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company.id, Company.name)
                    .where(Company.is_active)
                    .where(Company.watchlist_priority == 1)
                    .limit(10)
                )
                return [{"id": r.id, "name": r.name} for r in result.all()]
        except Exception:
            return []
