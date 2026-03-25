"""
app/services/accuracy_tracker.py — Phase 9: Prediction accuracy measurement.

For each confirmed mandate, finds the scoring_results row from 30/60/90 days
prior and records whether ORACLE's prediction was correct.

Logic:
  - "Correct" at horizon H = score at scored_at ≥ threshold, where
    scored_at is the closest row to (confirmed_at - H days).
  - Idempotent: upsert-style — won't duplicate rows for the same
    (company_id, practice_area, confirmed_at, horizon) tuple.

Weekly Celery task: agents.compute_prediction_accuracy (Agent 030)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

HORIZONS = (30, 60, 90)
DEFAULT_THRESHOLD = 0.5


async def compute_accuracy_for_confirmation(
    db: AsyncSession,
    confirmation_id: int,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """
    Compute and persist accuracy metrics for one mandate confirmation.

    For each horizon (30/60/90), finds the scoring_results row closest to
    (confirmed_at - horizon_days) and determines correctness.

    Returns:
        {confirmation_id, practice_area, horizons_processed, errors}
    """
    # ── Fetch the confirmation ─────────────────────────────────────────────────
    try:
        result = await db.execute(
            text("""
                SELECT company_id, practice_area, confirmed_at
                FROM mandate_confirmations
                WHERE id = :confirmation_id
            """),
            {"confirmation_id": confirmation_id},
        )
        row = result.fetchone()
    except Exception:
        log.exception("fetch confirmation failed", confirmation_id=confirmation_id)
        return {"confirmation_id": confirmation_id, "errors": 1, "horizons_processed": 0}

    if not row:
        log.warning("confirmation not found", confirmation_id=confirmation_id)
        return {"confirmation_id": confirmation_id, "errors": 1, "horizons_processed": 0}

    company_id, practice_area, confirmed_at = row
    if confirmed_at.tzinfo is None:
        confirmed_at = confirmed_at.replace(tzinfo=UTC)

    horizons_processed = 0
    errors = 0

    for horizon in HORIZONS:
        target_date = confirmed_at - timedelta(days=horizon)

        try:
            # Find the scoring_results row closest to target_date
            score_result = await db.execute(
                text("""
                    SELECT scored_at, scores
                    FROM scoring_results
                    WHERE company_id = :company_id
                      AND scored_at <= :confirmed_at
                    ORDER BY ABS(EXTRACT(EPOCH FROM (scored_at - :target_date)))
                    LIMIT 1
                """),
                {
                    "company_id": company_id,
                    "confirmed_at": confirmed_at,
                    "target_date": target_date,
                },
            )
            score_row = score_result.fetchone()
        except Exception:
            log.exception(
                "score lookup failed",
                company_id=company_id,
                horizon=horizon,
            )
            errors += 1
            continue

        if not score_row:
            # No score exists for this company — skip this horizon
            continue

        scored_at, scores_json = score_row
        if not isinstance(scores_json, dict):
            continue

        pa_scores = scores_json.get(practice_area, {})
        horizon_key = f"{horizon}d"
        score_key_alt = f"score_{horizon}d"
        predicted_score = (
            pa_scores.get(horizon_key)
            or pa_scores.get(score_key_alt)
            or 0.0
        )
        was_correct = float(predicted_score) >= threshold

        if scored_at.tzinfo is None:
            scored_at = scored_at.replace(tzinfo=UTC)
        lead_days = max(0, (confirmed_at - scored_at).days)

        # Idempotent upsert
        try:
            await db.execute(
                text("""
                    INSERT INTO prediction_accuracy_log
                        (company_id, practice_area, horizon, predicted_score,
                         threshold_used, was_correct, lead_days, confirmed_at)
                    VALUES
                        (:company_id, :practice_area, :horizon, :predicted_score,
                         :threshold_used, :was_correct, :lead_days, :confirmed_at)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "company_id": company_id,
                    "practice_area": practice_area,
                    "horizon": horizon,
                    "predicted_score": float(predicted_score),
                    "threshold_used": threshold,
                    "was_correct": was_correct,
                    "lead_days": lead_days,
                    "confirmed_at": confirmed_at,
                },
            )
            await db.commit()
            horizons_processed += 1
        except Exception:
            log.exception(
                "accuracy insert failed",
                company_id=company_id,
                horizon=horizon,
            )
            await db.rollback()
            errors += 1

    return {
        "confirmation_id": confirmation_id,
        "practice_area": practice_area,
        "horizons_processed": horizons_processed,
        "errors": errors,
    }


async def compute_all_pending(
    db: AsyncSession,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, int]:
    """
    Find mandate_confirmations not yet logged in prediction_accuracy_log
    and compute accuracy for each.

    Called by the weekly Agent 030 Celery task.

    Returns:
        {processed, errors}
    """
    try:
        result = await db.execute(
            text("""
                SELECT mc.id
                FROM mandate_confirmations mc
                WHERE NOT EXISTS (
                    SELECT 1 FROM prediction_accuracy_log pal
                    WHERE pal.company_id = mc.company_id
                      AND pal.practice_area = mc.practice_area
                      AND pal.confirmed_at = mc.confirmed_at
                )
                ORDER BY mc.confirmed_at DESC
                LIMIT 500
            """)
        )
        pending_ids = [r[0] for r in result.fetchall()]
    except Exception:
        log.exception("pending confirmations query failed")
        return {"processed": 0, "errors": 1}

    processed = 0
    errors = 0

    for confirmation_id in pending_ids:
        outcome = await compute_accuracy_for_confirmation(db, confirmation_id, threshold)
        if outcome.get("errors", 0):
            errors += 1
        else:
            processed += 1

    log.info(
        "accuracy compute complete",
        processed=processed,
        errors=errors,
        pending=len(pending_ids),
    )
    return {"processed": processed, "errors": errors}


async def get_accuracy_summary(
    db: AsyncSession,
    days: int = 90,
) -> list[dict[str, Any]]:
    """
    Per practice area summary: precision, recall, avg lead_days, n_confirmed.
    Only includes practice areas with at least 1 confirmed mandate.
    """
    since = datetime.now(UTC) - timedelta(days=days)

    try:
        result = await db.execute(
            text("""
                SELECT
                    practice_area,
                    horizon,
                    COUNT(*) AS n_total,
                    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) AS n_correct,
                    AVG(CASE WHEN lead_days IS NOT NULL THEN lead_days END) AS avg_lead_days
                FROM prediction_accuracy_log
                WHERE confirmed_at >= :since
                GROUP BY practice_area, horizon
                ORDER BY practice_area, horizon
            """),
            {"since": since},
        )
        rows = result.fetchall()
    except Exception:
        log.exception("accuracy summary query failed")
        return []

    return [
        {
            "practice_area": r[0],
            "horizon": r[1],
            "n_total": r[2],
            "n_correct": r[3],
            "precision": round(r[3] / r[2], 3) if r[2] > 0 else 0.0,
            "avg_lead_days": round(float(r[4]), 1) if r[4] is not None else None,
        }
        for r in rows
    ]
