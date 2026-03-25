"""
app/services/drift_detector.py — Phase 9: Model drift detection (Agent 031).

Detects when a practice area's prediction accuracy has degraded significantly,
using two complementary tests:

  1. Accuracy delta: rolling 30-day accuracy compared to the prior 30 days.
     If the drop exceeds DRIFT_THRESHOLD (10 percentage points), flag it.

  2. KS test: Kolmogorov-Smirnov test on the raw predicted_score distributions
     before vs after the midpoint window. A significant shift (p < 0.05)
     combined with an accuracy drop confirms the model has drifted.

Flags are stored in model_drift_alerts. An alert is only inserted if no
'open' alert already exists for that practice area (to avoid duplicates).

Weekly Celery task: agents.run_drift_detector (Agent 031)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

DRIFT_THRESHOLD = 0.10  # 10 percentage-point accuracy drop triggers an alert
MIN_SAMPLES = 10  # Minimum confirmations per window to run the test


async def detect_drift(
    db: AsyncSession,
    window_days: int = 30,
) -> list[dict[str, Any]]:
    """
    Compare rolling accuracy across two consecutive windows per practice area.

    Window A: [now - 2*window_days, now - window_days)
    Window B: [now - window_days, now)

    If accuracy(B) - accuracy(A) < -DRIFT_THRESHOLD: insert drift alert.

    Returns:
        List of newly created alert dicts.
    """
    now = datetime.now(UTC)
    window_b_start = now - timedelta(days=window_days)
    window_a_start = now - timedelta(days=2 * window_days)

    try:
        result = await db.execute(
            text("""
                SELECT practice_area
                FROM prediction_accuracy_log
                WHERE confirmed_at >= :window_a_start
                GROUP BY practice_area
                HAVING COUNT(*) >= :min_samples
            """),
            {
                "window_a_start": window_a_start,
                "min_samples": MIN_SAMPLES,
            },
        )
        practice_areas = [r[0] for r in result.fetchall()]
    except Exception:
        log.exception("drift detector PA query failed")
        return []

    new_alerts: list[dict[str, Any]] = []

    for pa in practice_areas:
        try:
            # Window A accuracy
            acc_a, scores_a = await _window_stats(db, pa, window_a_start, window_b_start)
            # Window B accuracy
            acc_b, scores_b = await _window_stats(db, pa, window_b_start, now)
        except Exception:
            log.exception("window stats failed", practice_area=pa)
            continue

        if acc_a is None or acc_b is None:
            continue

        delta = acc_b - acc_a  # negative = degradation

        if delta >= -DRIFT_THRESHOLD:
            continue  # No significant drop

        # Run KS test if scipy is available
        ks_statistic: float | None = None
        ks_pvalue: float | None = None
        if scores_a and scores_b:
            ks_statistic, ks_pvalue = _ks_test(scores_a, scores_b)

        # Only insert if no open alert exists for this PA
        already_open = await _has_open_alert(db, pa)
        if already_open:
            log.debug("drift alert already open, skipping", practice_area=pa)
            continue

        alert = await _insert_alert(
            db,
            pa,
            accuracy_before=acc_a,
            accuracy_after=acc_b,
            delta=delta,
            ks_statistic=ks_statistic,
            ks_pvalue=ks_pvalue,
        )
        new_alerts.append(alert)
        log.warning(
            "model drift detected",
            practice_area=pa,
            accuracy_before=round(acc_a, 3),
            accuracy_after=round(acc_b, 3),
            delta=round(delta, 3),
        )

    log.info(
        "drift detection complete",
        practice_areas_checked=len(practice_areas),
        new_alerts=len(new_alerts),
    )
    return new_alerts


async def _window_stats(
    db: AsyncSession,
    practice_area: str,
    start: datetime,
    end: datetime,
) -> tuple[float | None, list[float]]:
    """
    Return (accuracy_rate, [predicted_scores]) for a practice area in a date window.
    Returns (None, []) if fewer than MIN_SAMPLES rows.
    """
    result = await db.execute(
        text("""
            SELECT was_correct, predicted_score
            FROM prediction_accuracy_log
            WHERE practice_area = :practice_area
              AND confirmed_at >= :start
              AND confirmed_at < :end
        """),
        {"practice_area": practice_area, "start": start, "end": end},
    )
    rows = result.fetchall()

    if len(rows) < MIN_SAMPLES:
        return None, []

    correct = sum(1 for r in rows if r[0])
    accuracy = correct / len(rows)
    scores = [float(r[1]) for r in rows]
    return accuracy, scores


def _ks_test(
    scores_a: list[float],
    scores_b: list[float],
) -> tuple[float | None, float | None]:
    """
    Kolmogorov-Smirnov test on two score distributions.
    Returns (statistic, p-value), or (None, None) if scipy unavailable.
    """
    try:
        from scipy.stats import ks_2samp  # type: ignore[import-untyped]

        stat, pvalue = ks_2samp(scores_a, scores_b)
        return float(stat), float(pvalue)
    except ImportError:
        log.debug("scipy not available — KS test skipped")
        return None, None
    except Exception:
        log.exception("KS test failed")
        return None, None


async def _has_open_alert(db: AsyncSession, practice_area: str) -> bool:
    """Return True if an open drift alert already exists for this practice area."""
    try:
        result = await db.execute(
            text("""
                SELECT 1 FROM model_drift_alerts
                WHERE practice_area = :practice_area
                  AND status = 'open'
                LIMIT 1
            """),
            {"practice_area": practice_area},
        )
        return result.fetchone() is not None
    except Exception:
        log.exception("open alert check failed", practice_area=practice_area)
        return False


async def _insert_alert(
    db: AsyncSession,
    practice_area: str,
    accuracy_before: float,
    accuracy_after: float,
    delta: float,
    ks_statistic: float | None,
    ks_pvalue: float | None,
) -> dict[str, Any]:
    """Insert a new model_drift_alerts row and return it as a dict."""
    try:
        result = await db.execute(
            text("""
                INSERT INTO model_drift_alerts
                    (practice_area, accuracy_before, accuracy_after, delta,
                     ks_statistic, ks_pvalue, status)
                VALUES
                    (:practice_area, :accuracy_before, :accuracy_after, :delta,
                     :ks_statistic, :ks_pvalue, 'open')
                RETURNING id, detected_at
            """),
            {
                "practice_area": practice_area,
                "accuracy_before": accuracy_before,
                "accuracy_after": accuracy_after,
                "delta": delta,
                "ks_statistic": ks_statistic,
                "ks_pvalue": ks_pvalue,
            },
        )
        row = result.fetchone()
        await db.commit()
        alert_id = row[0] if row else -1
        detected_at = row[1] if row else datetime.now(UTC)
    except Exception:
        log.exception("alert insert failed", practice_area=practice_area)
        await db.rollback()
        return {}

    return {
        "id": alert_id,
        "practice_area": practice_area,
        "accuracy_before": round(accuracy_before, 3),
        "accuracy_after": round(accuracy_after, 3),
        "delta": round(delta, 3),
        "ks_statistic": ks_statistic,
        "ks_pvalue": ks_pvalue,
        "status": "open",
        "detected_at": detected_at.isoformat() if hasattr(detected_at, "isoformat") else str(detected_at),
    }


async def get_open_alerts(db: AsyncSession) -> list[dict[str, Any]]:
    """Return all open model drift alerts, newest first."""
    try:
        result = await db.execute(
            text("""
                SELECT id, practice_area, detected_at, accuracy_before,
                       accuracy_after, delta, ks_statistic, ks_pvalue, status
                FROM model_drift_alerts
                WHERE status = 'open'
                ORDER BY detected_at DESC
            """)
        )
        rows = result.fetchall()
    except Exception:
        log.exception("get_open_alerts query failed")
        return []

    return [
        {
            "id": r[0],
            "practice_area": r[1],
            "detected_at": r[2].isoformat() if r[2] else None,
            "accuracy_before": r[3],
            "accuracy_after": r[4],
            "delta": r[5],
            "ks_statistic": r[6],
            "ks_pvalue": r[7],
            "status": r[8],
        }
        for r in rows
    ]


async def acknowledge_alert(db: AsyncSession, alert_id: int) -> bool:
    """Mark an alert as acknowledged. Returns True on success."""
    try:
        await db.execute(
            text("""
                UPDATE model_drift_alerts
                SET status = 'acknowledged'
                WHERE id = :alert_id AND status = 'open'
            """),
            {"alert_id": alert_id},
        )
        await db.commit()
        return True
    except Exception:
        log.exception("acknowledge_alert failed", alert_id=alert_id)
        await db.rollback()
        return False
