"""
app/ml/velocity_scorer.py — Enhancement 2: Mandate velocity scoring.

Computes rate of change in mandate probability over 7 days.
Score: (today_prob - 7d_ago_prob) / max(7d_ago_prob, 0.01)
Clamped to [-1.0, +1.0] to prevent division blow-up.

High velocity (> 0.3) = mandate probability rising fast → flag for BD.
Negative velocity = probability declining → signal cooling off.

Stored in scoring_results.velocity_score column.
Also maintained in Redis hash for real-time access by Agent 021.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

log = logging.getLogger(__name__)

VELOCITY_WINDOW_DAYS: int = 7
VELOCITY_HIGH_THRESHOLD: float = 0.3   # triggers BD alert
VELOCITY_MIN_DENOMINATOR: float = 0.01  # prevents division by near-zero


def compute_velocity(
    current_scores: dict[str, dict[int, float]],
    prior_scores: dict[str, dict[int, float]],
) -> dict[str, float]:
    """
    Compute velocity per practice area (using 30d horizon as primary signal).

    Args:
        current_scores: {practice_area: {30: prob, 60: prob, 90: prob}} — today
        prior_scores:   Same structure — 7 days ago

    Returns:
        dict: {practice_area: velocity_score} — clamped to [-1, 1]
    """
    velocities: dict[str, float] = {}

    for pa, current in current_scores.items():
        current_30 = current.get(30, 0.0)
        prior_30 = prior_scores.get(pa, {}).get(30, 0.0)

        denominator = max(prior_30, VELOCITY_MIN_DENOMINATOR)
        raw_velocity = (current_30 - prior_30) / denominator

        # Clamp to [-1, 1]
        velocities[pa] = float(max(-1.0, min(1.0, raw_velocity)))

    return velocities


def aggregate_company_velocity(
    per_pa_velocities: dict[str, float],
    top_n: int = 5,
) -> float:
    """
    Aggregate per-practice-area velocities into a single company velocity score.

    Uses the mean of the top N absolute velocities (focus on most-moving areas).
    Preserves sign: positive if top movers are mostly increasing.

    Args:
        per_pa_velocities: {practice_area: velocity}
        top_n: How many top-magnitude areas to include

    Returns:
        Aggregate velocity in [-1, 1]
    """
    if not per_pa_velocities:
        return 0.0

    sorted_by_abs = sorted(per_pa_velocities.items(), key=lambda x: abs(x[1]), reverse=True)
    top = sorted_by_abs[:top_n]

    if not top:
        return 0.0

    return float(sum(v for _, v in top) / len(top))


def flag_high_velocity_companies(
    company_velocities: dict[int, float],
    threshold: float = VELOCITY_HIGH_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Return companies with velocity above threshold, sorted descending.

    Args:
        company_velocities: {company_id: aggregate_velocity}
        threshold: Minimum velocity to include

    Returns:
        List of {company_id, velocity} dicts, sorted by velocity desc.
    """
    flagged = [
        {"company_id": cid, "velocity": v}
        for cid, v in company_velocities.items()
        if v >= threshold
    ]
    return sorted(flagged, key=lambda x: x["velocity"], reverse=True)


def compute_velocity_from_history(
    score_history: list[dict[str, Any]],
) -> Optional[float]:
    """
    Compute velocity from a list of historical score records.

    Args:
        score_history: List of dicts with keys: scored_at (ISO str), score_30d (float).
                       Must contain at least 2 entries spanning 7+ days.
    Returns:
        Velocity score, or None if insufficient history.
    """
    if len(score_history) < 2:
        return None

    # Sort by date ascending
    try:
        history = sorted(
            score_history,
            key=lambda r: datetime.fromisoformat(r["scored_at"].replace("Z", "+00:00")),
        )
    except (KeyError, ValueError) as exc:
        log.warning("velocity_scorer: could not parse score history: %s", exc)
        return None

    latest = history[-1]
    cutoff = datetime.fromisoformat(
        latest["scored_at"].replace("Z", "+00:00")
    ) - timedelta(days=VELOCITY_WINDOW_DAYS)

    # Find the score closest to 7 days ago
    prior = None
    for record in history[:-1]:
        try:
            ts = datetime.fromisoformat(record["scored_at"].replace("Z", "+00:00"))
            if ts <= cutoff:
                prior = record
        except ValueError:
            continue

    if prior is None:
        return None

    current_30 = float(latest.get("score_30d", 0.0))
    prior_30 = float(prior.get("score_30d", 0.0))
    denominator = max(prior_30, VELOCITY_MIN_DENOMINATOR)
    return float(max(-1.0, min(1.0, (current_30 - prior_30) / denominator)))
