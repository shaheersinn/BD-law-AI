"""
app/services/linkedin_trigger.py — LinkedIn On-Demand Trigger (Agent 067 support).

Phase 5: Conserves Proxycurl credits by only firing on confirmed C-suite departure
signals, not on a batch schedule.

Trigger flow:
  1. Agent 067 (Executive Behaviour) detects a C-suite departure from news/filings
  2. Calls linkedin_trigger.run(signal_data) with executive name + company
  3. This module checks the daily Redis budget counter (MAX_DAILY_LOOKUPS=5)
  4. If budget available: calls Proxycurl Person Lookup API
  5. Returns enriched profile dict (name, headline, current role)

Budget:
  - Proxycurl free tier: 10 credits/month
  - We cap at 5/day via Redis counter to avoid exhausting monthly budget
  - Daily counter key: oracle:proxycurl:budget:{YYYY-MM-DD}
  - Counter expires after 25 hours to handle timezone edge cases

Proxycurl API: https://nubela.co/proxycurl/api/v2/linkedin
Authentication: Bearer token in Authorization header
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ── Constants ──────────────────────────────────────────────────────────────────
PROXYCURL_API_URL = "https://nubela.co/proxycurl/api/v2/linkedin"
DAILY_BUDGET_KEY_PREFIX = "oracle:proxycurl:budget"
MAX_DAILY_LOOKUPS = 5
BUDGET_KEY_TTL = 90_000  # 25 hours — covers timezone variations


class LinkedInTrigger:
    """
    On-demand LinkedIn profile lookup via Proxycurl.

    Conserves credits by:
      - Only running when a confirmed C-suite departure is detected
      - Hard cap of MAX_DAILY_LOOKUPS per calendar day
      - Skipping when proxycurl_api_key is not configured

    All HTTP calls are async (httpx.AsyncClient).
    """

    def _today_budget_key(self) -> str:
        """Redis key for today's usage counter."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"{DAILY_BUDGET_KEY_PREFIX}:{today}"

    async def _get_budget_used(self) -> int:
        """Return number of Proxycurl lookups consumed today (0 on error)."""
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            try:
                value = await client.get(self._today_budget_key())
                return int(value) if value is not None else 0
            finally:
                await client.aclose()

        except Exception as exc:
            log.warning("linkedin_budget_read_failed", error=str(exc))
            return 0

    async def _increment_budget(self) -> None:
        """Atomically increment today's usage counter by 1."""
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            try:
                pipe = client.pipeline()
                pipe.incr(self._today_budget_key())
                pipe.expire(self._today_budget_key(), BUDGET_KEY_TTL)
                await pipe.execute()
            finally:
                await client.aclose()

        except Exception as exc:
            log.warning("linkedin_budget_increment_failed", error=str(exc))

    async def check_budget(self) -> tuple[bool, int]:
        """
        Check whether the daily Proxycurl budget allows another lookup.

        Returns:
            (has_budget: bool, remaining: int)
        """
        used = await self._get_budget_used()
        remaining = MAX_DAILY_LOOKUPS - used
        return remaining > 0, remaining

    async def lookup_executive(
        self,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch a LinkedIn profile via Proxycurl Person Lookup API.

        At least one of the following parameter sets must be provided:
          - linkedin_url: direct profile URL (e.g. https://linkedin.com/in/jane-doe)
          - full_name + company_name: Proxycurl resolves via name+company lookup

        Budget check is NOT performed here — callers must call check_budget() first
        or use the higher-level run() method which handles budget management.

        Returns:
            Profile dict on success (keys: full_name, headline, experiences, etc.)
            None on API error, 404, or misconfiguration.
        """
        if not settings.proxycurl_api_key:
            log.warning("linkedin_trigger_no_api_key_configured")
            return None

        params: dict[str, str] = {}
        if linkedin_url:
            params["url"] = linkedin_url
        elif full_name and company_name:
            params["full_name"] = full_name
            params["current_company_name"] = company_name
        else:
            log.warning(
                "linkedin_trigger_missing_params", linkedin_url=linkedin_url, full_name=full_name
            )
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    PROXYCURL_API_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {settings.proxycurl_api_key}"},
                )

            if response.status_code == 200:
                profile: dict[str, Any] = response.json()
                log.info(
                    "linkedin_lookup_success",
                    name=profile.get("full_name"),
                    headline=profile.get("headline"),
                )
                return profile

            if response.status_code == 404:
                log.info("linkedin_profile_not_found", params=params)
            elif response.status_code == 429:
                log.warning(
                    "linkedin_rate_limited",
                    retry_after=response.headers.get("Retry-After"),
                )
            elif response.status_code in (401, 403):
                log.error("linkedin_auth_failed", status=response.status_code)
            else:
                log.warning(
                    "linkedin_unexpected_status",
                    status=response.status_code,
                    body=response.text[:200],
                )
            return None

        except httpx.TimeoutException as exc:
            log.warning("linkedin_timeout", error=str(exc))
            return None
        except httpx.HTTPError as exc:
            log.error("linkedin_http_error", error=str(exc))
            return None

    async def run(self, signal_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process a C-suite departure signal and perform a LinkedIn lookup.

        Called by Agent 067 (Executive Behaviour) when a confirmed departure
        is detected from news or SEDAR filings.

        Args:
            signal_data: Dict with at least one of:
                - "linkedin_url": str
                - "executive_name" (str) + "company_name" (str)
                Optional context keys: "company_id", "signal_id"

        Returns:
            Result dict with keys:
                status: "success" | "not_found" | "budget_exhausted" | "error"
                budget_remaining: int
                executive_name: str (when found)
                headline: str (when found)
                current_company: str (when found)
        """
        has_budget, remaining = await self.check_budget()
        if not has_budget:
            log.warning("linkedin_daily_budget_exhausted", max=MAX_DAILY_LOOKUPS)
            return {"status": "budget_exhausted", "budget_remaining": 0}

        linkedin_url = signal_data.get("linkedin_url")
        executive_name = signal_data.get("executive_name")
        company_name = signal_data.get("company_name")

        profile = await self.lookup_executive(
            linkedin_url=linkedin_url,
            full_name=executive_name,
            company_name=company_name,
        )

        if profile is None:
            return {"status": "not_found", "budget_remaining": remaining}

        # Increment budget only on successful lookup
        await self._increment_budget()

        # Extract current company from first experience entry
        experiences: list[dict[str, Any]] = profile.get("experiences") or []
        current_company = experiences[0].get("company") if experiences else None

        _, new_remaining = await self.check_budget()
        return {
            "status": "success",
            "executive_name": profile.get("full_name"),
            "headline": profile.get("headline"),
            "current_company": current_company,
            "budget_remaining": new_remaining,
        }


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this in other modules:
#   from app.services.linkedin_trigger import linkedin_trigger
linkedin_trigger = LinkedInTrigger()
