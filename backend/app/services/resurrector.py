"""
app/services/resurrector.py — Dead Signal Resurrector (Agent 022).

Phase 5: Monitors scrapers that have gone silent beyond their expected interval
and triggers immediate re-runs to restore data pipeline health.

Algorithm:
  1. Query scraper_health table for all non-disabled scrapers
  2. For each: compute silence_seconds = now - last_success_at
  3. If silence_seconds > 2 × expected_interval_seconds: scraper is "dead"
  4. Dispatch an immediate re-run via Celery (high priority, scrapers queue)
  5. If consecutive_failures >= 3: log at ERROR level (future: PagerDuty)

Expected interval map:
  Live feed scrapers (5-10 min) → alert threshold 10-20 min
  Batch scrapers (hourly to weekly) → 2× their normal interval

The resurrector does NOT modify scraper_health records — that is the
scraper's own responsibility after each run.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ── Expected interval map (seconds per scraper_name) ──────────────────────────
# Alert threshold = 2 × expected_interval
# Add new scrapers here when they are introduced.
EXPECTED_INTERVALS: dict[str, int] = {
    # ── Phase 5 live feed scrapers ─────────────────────────────────────────────
    "sedar_live": 300,  # polls every 5 min → alert if silent > 10 min
    "osc_live": 600,  # polls every 10 min → alert if silent > 20 min
    "canlii_live": 900,  # polls every 15 min → alert if silent > 30 min
    "news_live": 300,  # polls every 5 min → alert if silent > 10 min
    "scc_live": 1800,  # polls every 30 min → alert if silent > 60 min
    "edgar_live": 300,  # polls every 5 min → alert if silent > 10 min
    # ── Phase 1B canary ───────────────────────────────────────────────────────
    "canary": 1800,  # fires every 30 min → alert if silent > 60 min
    # ── Phase 1 batch scrapers ────────────────────────────────────────────────
    "sedar": 7200,  # every 2h during business hours
    "sedar_plus": 7200,
    "edgar": 3600,  # every hour
    "osc_enforcement": 14400,  # every 4h
    "osfi_enforcement": 14400,
    "competition_bureau": 14400,
    "fintrac": 14400,
    "eccc": 14400,
    "opc": 14400,
    "canlii": 86400,  # daily
    "opensky": 86400,
    "indeed": 86400,
    "linkedin_jobs": 86400,
    "job_bank": 86400,
    "reddit": 21600,  # every 6h
    "twitter": 21600,
    "stockhouse": 21600,
    "firm_blogs": 21600,
    "law_firm_blogs": 21600,
    "osb_insolvency": 604800,  # weekly
    "google_trends": 21600,
    "globe_mail": 1800,  # every 30 min (news)
    "financial_post": 1800,
    "reuters": 1800,
    "bnn_bloomberg": 1800,
    "cbc_business": 1800,
    "seeking_alpha": 21600,
    "google_news": 3600,
    "alpha_vantage": 3600,
    "yahoo_finance": 3600,
    "tmx_datalinx": 86400,
    "stats_canada": 604800,
}

DEFAULT_EXPECTED_INTERVAL = 86400  # 24h default for unlisted scrapers

# ── Category → Celery task map ────────────────────────────────────────────────
# Used to dispatch re-runs to the correct task when a dead scraper is detected.
CATEGORY_TASK_MAP: dict[str, str] = {
    "corporate": "app.tasks.scraper_tasks.run_corporate_scrapers",
    "filings": "app.tasks.scraper_tasks.run_filings_scrapers",
    "legal": "app.tasks.scraper_tasks.run_legal_scrapers",
    "regulatory": "app.tasks.scraper_tasks.run_regulatory_scrapers",
    "jobs": "app.tasks.scraper_tasks.run_jobs_scrapers",
    "market": "app.tasks.scraper_tasks.run_market_scrapers",
    "news": "app.tasks.scraper_tasks.run_news_scrapers",
    "social": "app.tasks.scraper_tasks.run_social_scrapers",
    "geo": "app.tasks.scraper_tasks.run_geo_scrapers",
    "lawblog": "app.tasks.scraper_tasks.run_lawblog_scrapers",
    "lawfirms": "app.tasks.scraper_tasks.run_lawblog_scrapers",
}


class DeadSignalResurrector:
    """
    Monitors scraper_health for silent scrapers and triggers re-runs.

    A scraper is "dead" when:
      (now - last_success_at) > 2 × EXPECTED_INTERVALS.get(scraper_name, DEFAULT)

    Critical scrapers (consecutive_failures >= 3) are logged at ERROR level.
    All dead scrapers trigger an immediate category-level re-run via Celery.
    """

    async def run(self) -> dict[str, Any]:
        """
        Main entry point — called by the Celery resurrector task (Agent 022).

        Queries scraper_health, identifies dead scrapers, and dispatches re-runs.

        Returns:
            Summary dict: n_checked, n_silent, n_triggered, n_critical, silent_scrapers.
        """
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models.scraper_health import ScraperHealth

        summary: dict[str, Any] = {
            "n_checked": 0,
            "n_silent": 0,
            "n_triggered": 0,
            "n_critical": 0,
            "silent_scrapers": [],
        }

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ScraperHealth).where(ScraperHealth.status != "disabled")
                )
                scrapers = list(result.scalars().all())

        except Exception as exc:
            log.error("resurrector_db_query_failed", error=str(exc))
            summary["error"] = str(exc)
            return summary

        now = datetime.now(UTC)

        for scraper in scrapers:
            summary["n_checked"] += 1

            # Skip scrapers that have never succeeded (not yet run)
            if scraper.last_success_at is None:
                continue

            expected_s = EXPECTED_INTERVALS.get(scraper.scraper_name, DEFAULT_EXPECTED_INTERVAL)
            silence_s = (now - scraper.last_success_at).total_seconds()
            threshold_s = expected_s * 2

            if silence_s <= threshold_s:
                continue  # Scraper is healthy — move on

            summary["n_silent"] += 1
            scraper_info = {
                "scraper_name": scraper.scraper_name,
                "category": scraper.scraper_category,
                "silence_seconds": int(silence_s),
                "threshold_seconds": int(threshold_s),
                "consecutive_failures": scraper.consecutive_failures,
            }
            summary["silent_scrapers"].append(scraper_info)

            if scraper.consecutive_failures >= 3:
                summary["n_critical"] += 1
                log.error(
                    "scraper_critical_dead",
                    scraper=scraper.scraper_name,
                    silence_hours=round(silence_s / 3600, 2),
                    consecutive_failures=scraper.consecutive_failures,
                )
            else:
                log.warning(
                    "scraper_silent_triggering_rerun",
                    scraper=scraper.scraper_name,
                    silence_hours=round(silence_s / 3600, 2),
                )

            triggered = await self._trigger_rerun(
                scraper.scraper_name,
                scraper.scraper_category,
            )
            if triggered:
                summary["n_triggered"] += 1

        log.info(
            "resurrector_complete",
            n_checked=summary["n_checked"],
            n_silent=summary["n_silent"],
            n_triggered=summary["n_triggered"],
            n_critical=summary["n_critical"],
        )
        return summary

    async def _trigger_rerun(self, scraper_name: str, category: str) -> bool:
        """
        Dispatch an immediate scraper category re-run via Celery.

        Uses send_task to avoid importing the task function directly
        (avoids circular imports between tasks and services).

        Returns:
            True if dispatched successfully, False otherwise.
        """
        task_name = CATEGORY_TASK_MAP.get(category)
        if not task_name:
            log.warning(
                "resurrector_no_task_for_category",
                category=category,
                scraper=scraper_name,
            )
            return False

        try:
            from app.tasks.celery_app import celery_app

            celery_app.send_task(
                task_name,
                queue="scrapers",
                priority=9,  # Highest Celery priority (0-9 scale)
            )
            log.info(
                "resurrector_rerun_dispatched",
                scraper=scraper_name,
                task=task_name,
            )
            return True

        except Exception as exc:
            log.error(
                "resurrector_trigger_failed",
                scraper=scraper_name,
                category=category,
                error=str(exc),
            )
            return False


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this in other modules:
#   from app.services.resurrector import resurrector
resurrector = DeadSignalResurrector()
