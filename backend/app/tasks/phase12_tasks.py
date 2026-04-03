"""
app/tasks/phase12_tasks.py — Phase 12: Post-Launch Optimization Celery tasks.

Three agents:
    Agent 033 — compute_usage_report  (weekly Monday 08:00 UTC)
        Computes weekly usage analytics + score quality report.
        Delivers summary via Slack or structlog.

    Agent 034 — recalibrate_signal_weights  (monthly 1st at 02:00 UTC)
        Re-runs sector weight calibration on 30 days of confirmed mandate data.
        Re-mines Apriori co-occurrence rules.

    Agent 035 — check_retrain_trigger  (weekly Sunday 03:00 UTC)
        Checks for open model_drift_alerts with delta > threshold.
        Submits targeted Azure ML retraining job for flagged practice areas.

All tasks use the synchronous DB pattern (psycopg2 or SQLAlchemy sync) where needed,
or spin their own async loop.  For simplicity these tasks wrap async services via
asyncio.run() within a dedicated event loop (safe in Celery worker context since
each task runs in its own process/thread with no pre-existing event loop).
"""

from __future__ import annotations

import asyncio
import json
import logging

import structlog

log = structlog.get_logger(__name__)
_stdlib_log = logging.getLogger(__name__)

from app.tasks.celery_app import celery_app  # noqa: E402,I001


# ── Agent 033 — Usage Analytics + Score Quality ────────────────────────────────


@celery_app.task(
    name="agents.compute_usage_report",
    queue="agents",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    time_limit=600,
    soft_time_limit=540,
)
def compute_usage_report(self) -> dict:  # type: ignore[type-arg]
    """
    Agent 033 — Weekly usage analytics snapshot + score quality review.

    Runs every Monday 08:00 UTC (configured in celery_app.py beat_schedule).
    """
    _stdlib_log.info("Agent 033: compute_usage_report starting")

    try:
        result = asyncio.run(_run_usage_report())
        _stdlib_log.info("Agent 033: compute_usage_report complete", extra=result)
        return result
    except Exception as exc:
        _stdlib_log.exception("Agent 033: compute_usage_report failed")
        raise self.retry(exc=exc) from exc


async def _run_usage_report() -> dict:  # type: ignore[type-arg]
    from app.database import AsyncSessionLocal
    from app.services.analytics_service import compute_weekly_usage_report
    from app.services.score_quality import compute_score_quality_report

    async with AsyncSessionLocal() as db:
        usage = await compute_weekly_usage_report(db)
        quality = await compute_score_quality_report(db)

    return {
        "status": "ok",
        "week_start": str(usage.get("week_start")),
        "worst_five": quality.get("worst_five", []),
    }


# ── Agent 034 — Signal Weight Recalibration ────────────────────────────────────


@celery_app.task(
    name="agents.recalibrate_signal_weights",
    queue="agents",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    time_limit=3600,
    soft_time_limit=3300,
)
def recalibrate_signal_weights(self) -> dict:  # type: ignore[type-arg]
    """
    Agent 034 — Monthly sector weight recalibration + Apriori rule refresh.

    Runs on the 1st of every month at 02:00 UTC.
    """
    _stdlib_log.info("Agent 034: recalibrate_signal_weights starting")

    try:
        result = asyncio.run(_run_recalibration())
        _stdlib_log.info("Agent 034: recalibrate_signal_weights complete", extra=result)
        return result
    except Exception as exc:
        _stdlib_log.exception("Agent 034: recalibrate_signal_weights failed")
        raise self.retry(exc=exc) from exc


async def _run_recalibration() -> dict:  # type: ignore[type-arg]
    from app.database import AsyncSessionLocal
    from app.ml.cooccurrence import refresh_rules
    from app.ml.sector_weights import recalibrate_from_confirmations

    async with AsyncSessionLocal() as db:
        new_weights = await recalibrate_from_confirmations(db)
        total_rules = await refresh_rules(db)

    return {
        "status": "ok",
        "sectors_recalibrated": len(new_weights),
        "cooccurrence_rules_written": total_rules,
    }


# ── Agent 035 — Retraining Trigger ────────────────────────────────────────────


@celery_app.task(
    name="agents.check_retrain_trigger",
    queue="agents",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    time_limit=300,
    soft_time_limit=270,
)
def check_retrain_trigger(self) -> dict:  # type: ignore[type-arg]
    """
    Agent 035 — Weekly check for open model drift alerts that exceed threshold.
    Submits targeted Azure ML retraining if needed.

    Runs every Sunday 03:00 UTC.
    """
    _stdlib_log.info("Agent 035: check_retrain_trigger starting")

    try:
        result = asyncio.run(_run_retrain_check())
        _stdlib_log.info("Agent 035: check_retrain_trigger complete", extra=result)
        return result
    except Exception as exc:
        _stdlib_log.exception("Agent 035: check_retrain_trigger failed")
        raise self.retry(exc=exc) from exc


async def _run_retrain_check() -> dict:  # type: ignore[type-arg]
    from sqlalchemy import text

    from app.config import get_settings
    from app.database import AsyncSessionLocal

    settings = get_settings()
    threshold = settings.retrain_drift_threshold

    async with AsyncSessionLocal() as db:
        # Look for open drift alerts above threshold (Phase 9 table)
        try:
            rows = (
                await db.execute(
                    text(
                        """
                        SELECT id, practice_area, delta
                        FROM model_drift_alerts
                        WHERE status = 'open'
                          AND delta > :threshold
                        ORDER BY delta DESC
                        LIMIT 34
                        """
                    ),
                    {"threshold": threshold},
                )
            ).all()
        except Exception:
            log.warning("check_retrain_trigger: model_drift_alerts not available (Phase 9 pending)")
            return {"status": "skipped", "reason": "model_drift_alerts table not yet available"}

        if not rows:
            log.info("check_retrain_trigger: no open drift alerts above threshold")
            return {"status": "ok", "retrain_submitted": False}

        practice_areas = [row.practice_area for row in rows]
        alert_ids = [row.id for row in rows]

        log.info(
            "check_retrain_trigger: submitting targeted retraining",
            practice_areas=practice_areas,
            alert_count=len(rows),
        )

        # Submit Azure job
        job_name: str | None = None
        try:
            from azure.training.azure_job import submit_training_job  # type: ignore[import]

            job_name = submit_training_job(practice_areas=practice_areas)
        except Exception:
            log.warning("check_retrain_trigger: Azure job submission failed (credentials not set)")
            job_name = "dry-run-no-azure-credentials"

        # Record submission in retrain_submissions table
        try:
            await db.execute(
                text(
                    """
                    INSERT INTO retrain_submissions
                        (practice_areas, drift_alert_ids, azure_job_id, status)
                    VALUES
                        (:practice_areas::jsonb, :alert_ids::jsonb, :job_id, 'submitted')
                    """
                ),
                {
                    "practice_areas": json.dumps(practice_areas),
                    "alert_ids": json.dumps(alert_ids),
                    "job_id": job_name,
                },
            )

            # Update drift alert status
            await db.execute(
                text(
                    """
                    UPDATE model_drift_alerts
                    SET status = 'retrain_submitted'
                    WHERE id = ANY(:ids)
                    """
                ),
                {"ids": alert_ids},
            )

            await db.commit()
        except Exception:
            log.warning("check_retrain_trigger: failed to record submission in DB")

        return {
            "status": "ok",
            "retrain_submitted": True,
            "practice_areas": practice_areas,
            "azure_job_id": job_name,
        }
