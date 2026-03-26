"""
app/tasks/phase9_tasks.py — Phase 9 Feedback Loop Celery tasks.

Implements Agents 030-032:
    Agent 030 — Accuracy Tracker (compute_prediction_accuracy — weekly)
    Agent 031 — Drift Detector  (run_drift_detector — weekly)
    Agent 032 — Confirmation Hunter (run_confirmation_hunter — daily)

Phase 10 hardening:
    - Sentry capture_exception() added in all except blocks.
    - These tasks call async service layers, so asyncio.run() is retained.
      The underlying services (accuracy_tracker, drift_detector,
      confirmation_hunter) use async SQLAlchemy and cannot trivially be
      made synchronous without duplicating the service layer.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.tasks.celery_app import celery_app

log = structlog.get_logger(__name__)


# ── Agent 030: Prediction Accuracy Tracker ─────────────────────────────────────


@celery_app.task(
    name="agents.compute_prediction_accuracy",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    time_limit=2100,
    soft_time_limit=1800,
    queue="agents",
    acks_late=True,
)
def compute_prediction_accuracy(self: Any) -> dict[str, Any]:
    """
    Agent 030 — Compute and persist prediction accuracy for all pending
    mandate confirmations.  Runs weekly (Sunday 01:00 UTC).

    Finds mandate_confirmations not yet logged in prediction_accuracy_log
    and computes was_correct + lead_days for each horizon (30/60/90).
    Idempotent: safe to re-run.
    """
    import asyncio

    from app.database import get_db
    from app.services.accuracy_tracker import compute_all_pending

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                return await compute_all_pending(db)

        result = asyncio.run(_run())
        log.info("agent_030_accuracy_tracker", **result)
        return result

    except Exception as exc:
        log.exception("agent_030_accuracy_tracker_failed", error=str(exc))
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except ImportError:
            pass
        raise self.retry(exc=exc) from exc


# ── Agent 031: Drift Detector ─────────────────────────────────────────────────


@celery_app.task(
    name="agents.run_drift_detector",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    time_limit=1800,
    soft_time_limit=1500,
    queue="agents",
    acks_late=True,
)
def run_drift_detector(self: Any) -> dict[str, Any]:
    """
    Agent 031 — Detect model accuracy drift per practice area.
    Runs weekly (Sunday 02:00 UTC).

    Compares rolling 30-day accuracy vs prior 30-day baseline.
    Runs KS test on score distributions.
    Inserts model_drift_alerts for any practice area with > 10pp accuracy drop.
    Triggers orchestrator re-evaluation for flagged practice areas.
    """
    import asyncio

    from app.database import get_db
    from app.ml.orchestrator import get_orchestrator
    from app.services.drift_detector import detect_drift

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                new_alerts = await detect_drift(db)

            flagged = [a.get("practice_area") for a in new_alerts if a]

            # Trigger orchestrator re-evaluation for flagged areas
            if flagged:
                try:
                    orchestrator = get_orchestrator()
                    if orchestrator._loaded:
                        orchestrator.update_from_registry([])
                        log.info("orchestrator re-evaluated after drift", areas=flagged)
                except Exception:
                    log.exception("orchestrator re-eval failed after drift")

            return {
                "new_alerts": len(new_alerts),
                "flagged_areas": flagged,
            }

        result = asyncio.run(_run())
        log.info("agent_031_drift_detector", **result)
        return result

    except Exception as exc:
        log.exception("agent_031_drift_detector_failed", error=str(exc))
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except ImportError:
            pass
        raise self.retry(exc=exc) from exc


# ── Agent 032: Mandate Confirmation Hunter ────────────────────────────────────


@celery_app.task(
    name="agents.run_confirmation_hunter",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300,
    queue="agents",
    acks_late=True,
)
def run_confirmation_hunter(self: Any) -> dict[str, Any]:
    """
    Agent 032 — Auto-detect mandate confirmations from live signals.
    Runs daily (06:30 UTC).

    Scrapes recent signal_records from:
      - canlii_live (court decisions)
      - law_firm_* scrapers (deal announcements)
      - SEDAR legal_contingency disclosures

    Fuzzy-matches entity names via EntityResolver (rapidfuzz, threshold 82.0).
    Creates mandate_confirmations with is_auto_detected=True.
    Partner review required before confirmations count in accuracy metrics.
    """
    import asyncio

    from app.database import get_db
    from app.services.confirmation_hunter import run as hunter_run

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                return await hunter_run(db)

        result = asyncio.run(_run())
        log.info("agent_032_confirmation_hunter", **result)
        return result

    except Exception as exc:
        log.exception("agent_032_confirmation_hunter_failed", error=str(exc))
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except ImportError:
            pass
        raise self.retry(exc=exc) from exc
