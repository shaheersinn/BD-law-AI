"""
app/scrapers/social/linkedin.py — LinkedIn scraper via Proxycurl.

Source: https://nubela.co/proxycurl (compliant paid API intermediary)
        10 free credits/month. Decision to scale at Phase 1 review.

What it scrapes:
  - C-suite + GC (General Counsel) departures at target companies
  - New compliance/legal officer hires (signal: regulatory exposure anticipated)
  - Law firm partner hires from target company (signal: anticipated mandate)

Signal types:
  social_linkedin_exec_departure  — CEO/CFO/CLO departure
  social_linkedin_legal_hire      — New GC/CLO/compliance hire
  social_linkedin_lawfirm_hire    — Employee hired by law firm (from company)

Data: MongoDB ONLY.
Rate: 0.05 rps (10 free credits/month — extremely conservative)
"""
from __future__ import annotations
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
from app.config import get_settings

log = structlog.get_logger(__name__)

_PROXYCURL_SEARCH = "https://nubela.co/proxycurl/api/v2/linkedin/company/employees/"
_PROXYCURL_PROFILE = "https://nubela.co/proxycurl/api/v2/linkedin"


@register
class LinkedInScraper(BaseScraper):
    source_id = "social_linkedin"
    source_name = "LinkedIn (via Proxycurl)"
    signal_types = ["social_linkedin_exec_departure", "social_linkedin_legal_hire"]
    rate_limit_rps = 0.05
    concurrency = 1
    retry_attempts = 2
    timeout_seconds = 30.0
    ttl_seconds = 86400
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        api_key = getattr(settings, "proxycurl_api_key", None)
        if not api_key:
            log.warning("proxycurl_no_api_key")
            return []

        # With only 10 free credits/month, we only run this on explicit trigger
        # (Agent 004 Blog Monitor flags a company for deep LinkedIn check)
        # In scheduled scrape mode, this returns empty — called by Phase 5 live feed
        log.info("linkedin_scraper_stub_mode",
                 note="LinkedIn requires targeted company list from live feed trigger. "
                      "Will activate in Phase 5 on-demand mode.")
        return []

    async def health_check(self) -> bool:
        settings = get_settings()
        if not getattr(settings, "proxycurl_api_key", None):
            return False
        try:
            response = await self.get(
                "https://nubela.co/proxycurl/api/credit-balance",
                headers={"Authorization": f"Bearer {getattr(settings, 'proxycurl_api_key', '')}"},
            )
            return response.status_code == 200
        except Exception:
            return False
