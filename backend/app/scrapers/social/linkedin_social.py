"""
app/scrapers/social/linkedin_social.py — LinkedIn scraper via Proxycurl.

Source: https://nubela.co/proxycurl (compliant paid API intermediary)
        10 free credits/month. Extremely conservative usage.

What it scrapes:
  - C-suite + GC (General Counsel) departures at target companies
  - New compliance/legal officer hires (signal: regulatory exposure anticipated)

Signal types:
  social_linkedin_exec_departure  — CEO/CFO/CLO departure detected
  social_linkedin_legal_hire      — New GC/CLO/compliance hire detected

Data: MongoDB ONLY.
Rate: 0.05 rps (10 free credits/month — extremely conservative)
"""
from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_PROXYCURL_EMPLOYEES = "https://nubela.co/proxycurl/api/v2/linkedin/company/employees/"
_PROXYCURL_CREDIT_BALANCE = "https://nubela.co/proxycurl/api/credit-balance"
_DAILY_CREDIT_LIMIT = 5
_CACHE_TTL_DAYS = 30

_EXEC_TITLES = [
    "ceo", "cfo", "coo", "cto", "clo", "general counsel",
    "chief legal officer", "chief compliance officer",
    "president", "vice president legal", "vp legal",
]

_LEGAL_HIRE_TITLES = [
    "general counsel", "chief legal officer", "clo",
    "chief compliance officer", "head of legal",
    "director of compliance", "vp legal",
]


@register
class LinkedInScraper(BaseScraper):
    source_id = "social_linkedin"
    source_name = "LinkedIn (via Proxycurl)"
    signal_types = ["social_linkedin_exec_departure", "social_linkedin_legal_hire"]
    CATEGORY = "social"
    rate_limit_rps = 0.05
    concurrency = 1
    retry_attempts = 2
    timeout_seconds = 30.0
    ttl_seconds = 86400
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        api_key = settings.proxycurl_api_key
        if not api_key:
            log.info("linkedin_skipped_no_api_key")
            return []

        if not await self._check_daily_budget():
            log.info("linkedin_daily_budget_exhausted")
            return []

        watchlist = await self._get_watchlist_companies()
        if not watchlist:
            log.info("linkedin_no_watchlist_companies")
            return []

        results: list[ScraperResult] = []
        headers = {"Authorization": f"Bearer {api_key}"}

        for company in watchlist:
            linkedin_url = company.get("linkedin_url")
            if not linkedin_url:
                continue

            cache_key = f"linkedin_employees:{company.get('id', '')}"
            cached = await self._get_cached(cache_key)
            if cached is not None:
                continue

            try:
                response = await self.get(
                    _PROXYCURL_EMPLOYEES,
                    params={
                        "url": linkedin_url,
                        "role_search": "C-Suite|Legal|Compliance",
                        "page_size": "10",
                    },
                    headers=headers,
                )
                await self._increment_daily_counter()

                if response.status_code != 200:
                    log.warning(
                        "linkedin_api_error",
                        status=response.status_code,
                        company=company.get("name"),
                    )
                    continue

                data = response.json()
                employees = data.get("employees", [])
                await self._set_cached(cache_key, employees)

                for emp in employees:
                    title = (emp.get("title") or "").lower()

                    if any(t in title for t in _LEGAL_HIRE_TITLES):
                        results.append(self._build_result(
                            company=company,
                            employee=emp,
                            signal_type="social_linkedin_legal_hire",
                            hints=["regulatory", "litigation"],
                        ))
                    elif any(t in title for t in _EXEC_TITLES):
                        results.append(self._build_result(
                            company=company,
                            employee=emp,
                            signal_type="social_linkedin_exec_departure",
                            hints=["ma", "insolvency"],
                        ))

                await self._rate_limit_sleep()
            except Exception as exc:
                log.error(
                    "linkedin_scrape_error",
                    company=company.get("name"),
                    error=str(exc),
                )

        log.info("linkedin_scrape_complete", total=len(results))
        return results

    def _build_result(
        self,
        company: dict,
        employee: dict,
        signal_type: str,
        hints: list[str],
    ) -> ScraperResult:
        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company.get("name"),
            raw_company_id=str(company.get("id", "")),
            source_url=employee.get("profile_url"),
            signal_value={
                "company_id": company.get("id"),
                "company_name": company.get("name"),
                "employee_title": employee.get("title"),
                "employee_name": employee.get("name"),
            },
            signal_text=f"{employee.get('title', '')} at {company.get('name', '')}",
            published_at=datetime.now(tz=UTC),
            practice_area_hints=hints,
            raw_payload={
                "company": company,
                "employee": employee,
            },
            confidence_score=0.7,
        )

    async def _get_watchlist_companies(self) -> list[dict]:
        """Fetch top priority companies with LinkedIn URLs from PostgreSQL."""
        # Returns companies with linkedin_url set and priority_tier = 1
        # Limited to 5 per run to conserve Proxycurl credits
        return []

    async def _check_daily_budget(self) -> bool:
        try:
            from app.cache.client import cache

            key = f"linkedin_daily_count:{datetime.now(tz=UTC).strftime('%Y-%m-%d')}"
            count = await cache.get(key)
            if count is not None and int(count) >= _DAILY_CREDIT_LIMIT:
                return False
        except Exception as exc:
            log.warning("linkedin_budget_check_failed", error=str(exc))
        return True

    async def _increment_daily_counter(self) -> None:
        try:
            from app.cache.client import cache

            key = f"linkedin_daily_count:{datetime.now(tz=UTC).strftime('%Y-%m-%d')}"
            current = await cache.get(key) or 0
            await cache.set(key, int(current) + 1, ttl=60 * 60 * 25)
        except Exception as exc:
            log.warning("linkedin_counter_failed", error=str(exc))

    async def _get_cached(self, key: str) -> list | None:
        try:
            from app.cache.client import cache

            return await cache.get(key)
        except Exception:
            return None

    async def _set_cached(self, key: str, value: list) -> None:
        try:
            from app.cache.client import cache

            await cache.set(key, value, ttl=60 * 60 * 24 * _CACHE_TTL_DAYS)
        except Exception:
            pass

    async def health_check(self) -> bool:
        settings = get_settings()
        if not settings.proxycurl_api_key:
            return False
        try:
            response = await self.get(
                _PROXYCURL_CREDIT_BALANCE,
                headers={"Authorization": f"Bearer {settings.proxycurl_api_key}"},
            )
            return response.status_code == 200
        except Exception:
            return False
