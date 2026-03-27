"""
app/services/mandate_confirmation.py — Phase 9: Mandate confirmation recording.

When a mandate is confirmed (either by a partner manually or auto-detected by
Agent 032), this service:
  1. Writes a row to mandate_confirmations.
  2. Cross-references prior scoring_results to compute prediction_lead_days
     (how many days before confirmation ORACLE had a score > 0.5 for that PA).
  3. Returns a dict summarising the confirmation outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

SCORE_THRESHOLD = 0.5  # Score that constitutes a "positive" prediction


async def confirm_mandate(
    db: AsyncSession,
    company_id: int,
    practice_area: str,
    confirmed_at: datetime,
    source: str,
    evidence_url: str | None = None,
    reviewed_by_user_id: int | None = None,
    is_auto_detected: bool = False,
) -> dict[str, Any]:
    """
    Record a confirmed mandate and compute prediction lead time.

    Returns:
        dict with confirmation_id, lead_days (None if no prior prediction > 0.5)
    """
    # ── Write confirmation row ─────────────────────────────────────────────────
    result = await db.execute(
        text("""
            INSERT INTO mandate_confirmations
                (company_id, practice_area, confirmed_at, confirmation_source,
                 evidence_url, is_auto_detected, reviewed_by_user_id)
            VALUES
                (:company_id, :practice_area, :confirmed_at, :source,
                 :evidence_url, :is_auto_detected, :reviewed_by_user_id)
            RETURNING id
        """),
        {
            "company_id": company_id,
            "practice_area": practice_area,
            "confirmed_at": confirmed_at,
            "source": source,
            "evidence_url": evidence_url,
            "is_auto_detected": is_auto_detected,
            "reviewed_by_user_id": reviewed_by_user_id,
        },
    )
    row = result.fetchone()
    confirmation_id: int = row[0] if row else -1
    await db.commit()

    # ── Compute prediction lead days ───────────────────────────────────────────
    lead_days = await _compute_lead_days(db, company_id, practice_area, confirmed_at)

    log.info(
        "mandate confirmed",
        confirmation_id=confirmation_id,
        company_id=company_id,
        practice_area=practice_area,
        is_auto_detected=is_auto_detected,
        lead_days=lead_days,
    )

    return {
        "confirmation_id": confirmation_id,
        "company_id": company_id,
        "practice_area": practice_area,
        "confirmed_at": confirmed_at.isoformat(),
        "lead_days": lead_days,
        "source": source,
        "is_auto_detected": is_auto_detected,
    }


async def _compute_lead_days(
    db: AsyncSession,
    company_id: int,
    practice_area: str,
    confirmed_at: datetime,
) -> int | None:
    """
    Find the earliest scoring_results row where the 30d score for this
    practice area exceeded SCORE_THRESHOLD, from up to 90 days before
    confirmed_at.  Returns days between that row and confirmed_at.
    Returns None if no qualifying score found.
    """
    lookback_start = confirmed_at - timedelta(days=90)

    try:
        result = await db.execute(
            text("""
                SELECT scored_at, scores
                FROM scoring_results
                WHERE company_id = :company_id
                  AND scored_at >= :lookback_start
                  AND scored_at <= :confirmed_at
                ORDER BY scored_at ASC
            """),
            {
                "company_id": company_id,
                "lookback_start": lookback_start,
                "confirmed_at": confirmed_at,
            },
        )
        rows = result.fetchall()
    except Exception:
        log.exception("lead_days query failed", company_id=company_id)
        return None

    for scored_at, scores_json in rows:
        if not isinstance(scores_json, dict):
            continue
        pa_scores = scores_json.get(practice_area, {})
        score_30d = pa_scores.get("30d") or pa_scores.get("score_30d") or 0.0
        if score_30d >= SCORE_THRESHOLD:
            delta = confirmed_at - (
                scored_at if scored_at.tzinfo else scored_at.replace(tzinfo=UTC)
            )
            return max(0, delta.days)

    return None


_STATS_ALL = text("""
    SELECT
        practice_area,
        COUNT(*) AS total,
        SUM(CASE WHEN is_auto_detected THEN 1 ELSE 0 END) AS auto_detected,
        SUM(CASE WHEN NOT is_auto_detected THEN 1 ELSE 0 END) AS manual
    FROM mandate_confirmations
    WHERE confirmed_at >= :since
    GROUP BY practice_area
    ORDER BY total DESC
""")

_STATS_BY_PA = text("""
    SELECT
        practice_area,
        COUNT(*) AS total,
        SUM(CASE WHEN is_auto_detected THEN 1 ELSE 0 END) AS auto_detected,
        SUM(CASE WHEN NOT is_auto_detected THEN 1 ELSE 0 END) AS manual
    FROM mandate_confirmations
    WHERE confirmed_at >= :since
      AND practice_area = :practice_area
    GROUP BY practice_area
    ORDER BY total DESC
""")


async def get_confirmation_stats(
    db: AsyncSession,
    practice_area: str | None = None,
    days: int = 90,
) -> list[dict[str, Any]]:
    """
    Return confirmation counts per practice area over the last `days` days.
    Optionally filtered to a single practice area.
    """
    since = datetime.now(UTC) - timedelta(days=days)

    try:
        if practice_area:
            result = await db.execute(
                _STATS_BY_PA, {"since": since, "practice_area": practice_area}
            )
        else:
            result = await db.execute(_STATS_ALL, {"since": since})
        rows = result.fetchall()
    except Exception:
        log.exception("confirmation_stats query failed")
        return []

    return [
        {
            "practice_area": r[0],
            "total": r[1],
            "auto_detected": r[2],
            "manual": r[3],
        }
        for r in rows
    ]


_LIST_ALL = text("""
    SELECT id, company_id, practice_area, confirmed_at,
           confirmation_source, evidence_url, is_auto_detected,
           reviewed_by_user_id, created_at
    FROM mandate_confirmations
    ORDER BY confirmed_at DESC
    LIMIT :limit
""")

_LIST_BY_COMPANY = text("""
    SELECT id, company_id, practice_area, confirmed_at,
           confirmation_source, evidence_url, is_auto_detected,
           reviewed_by_user_id, created_at
    FROM mandate_confirmations
    WHERE company_id = :company_id
    ORDER BY confirmed_at DESC
    LIMIT :limit
""")

_LIST_BY_PA = text("""
    SELECT id, company_id, practice_area, confirmed_at,
           confirmation_source, evidence_url, is_auto_detected,
           reviewed_by_user_id, created_at
    FROM mandate_confirmations
    WHERE practice_area = :practice_area
    ORDER BY confirmed_at DESC
    LIMIT :limit
""")

_LIST_BY_COMPANY_AND_PA = text("""
    SELECT id, company_id, practice_area, confirmed_at,
           confirmation_source, evidence_url, is_auto_detected,
           reviewed_by_user_id, created_at
    FROM mandate_confirmations
    WHERE company_id = :company_id
      AND practice_area = :practice_area
    ORDER BY confirmed_at DESC
    LIMIT :limit
""")


async def list_confirmations(
    db: AsyncSession,
    company_id: int | None = None,
    practice_area: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent mandate confirmations, optionally filtered."""
    params: dict[str, Any] = {"limit": limit}

    if company_id is not None and practice_area is not None:
        params["company_id"] = company_id
        params["practice_area"] = practice_area
        query = _LIST_BY_COMPANY_AND_PA
    elif company_id is not None:
        params["company_id"] = company_id
        query = _LIST_BY_COMPANY
    elif practice_area is not None:
        params["practice_area"] = practice_area
        query = _LIST_BY_PA
    else:
        query = _LIST_ALL

    try:
        result = await db.execute(query, params)
        rows = result.fetchall()
    except Exception:
        log.exception("list_confirmations query failed")
        return []

    return [
        {
            "id": r[0],
            "company_id": r[1],
            "practice_area": r[2],
            "confirmed_at": r[3].isoformat() if r[3] else None,
            "confirmation_source": r[4],
            "evidence_url": r[5],
            "is_auto_detected": r[6],
            "reviewed_by_user_id": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]
