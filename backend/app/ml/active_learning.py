"""
app/ml/active_learning.py — Enhancement 4: Active learning loop.

Identifies companies where model prediction confidence is in the
uncertainty zone [0.4, 0.6]. These are flagged for priority signal
collection — more aggressive scraping, not human review.

Stored in active_learning_queue table.
Celery task: agents.run_active_learning — weekly.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

UNCERTAINTY_LOW: float = 0.4
UNCERTAINTY_HIGH: float = 0.6


def identify_uncertain_companies(
    company_scores: dict[int, dict[str, dict[int, float]]],
    min_uncertain_areas: int = 1,
) -> list[dict[str, Any]]:
    """
    Find companies with uncertain mandate probabilities.

    Args:
        company_scores: {company_id: {practice_area: {30: prob, 60: prob, 90: prob}}}
        min_uncertain_areas: Min number of practice areas in uncertainty zone.

    Returns:
        List of {company_id, uncertain_areas, max_uncertainty_score}
        sorted by number of uncertain areas descending.
    """
    uncertain: list[dict[str, Any]] = []

    for company_id, area_scores in company_scores.items():
        uncertain_areas: list[str] = []
        uncertainty_scores: list[float] = []

        for pa, horizon_scores in area_scores.items():
            prob_30 = horizon_scores.get(30, 0.0)
            if UNCERTAINTY_LOW <= prob_30 <= UNCERTAINTY_HIGH:
                uncertain_areas.append(pa)
                # Distance from 0.5 — closer to 0.5 = more uncertain
                uncertainty_scores.append(1.0 - 2.0 * abs(prob_30 - 0.5))

        if len(uncertain_areas) >= min_uncertain_areas:
            uncertain.append(
                {
                    "company_id": company_id,
                    "uncertain_areas": uncertain_areas,
                    "n_uncertain": len(uncertain_areas),
                    "max_uncertainty": max(uncertainty_scores) if uncertainty_scores else 0.0,
                    "queued_at": datetime.now(tz=UTC).isoformat(),
                }
            )

    return sorted(uncertain, key=lambda x: x["n_uncertain"], reverse=True)


def build_active_learning_queue_rows(
    uncertain_companies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert uncertain companies to active_learning_queue table rows.
    One row per company per uncertain practice area.
    """
    rows: list[dict[str, Any]] = []
    for item in uncertain_companies:
        company_id = item["company_id"]
        for pa in item.get("uncertain_areas", []):
            rows.append(
                {
                    "company_id": company_id,
                    "practice_area": pa,
                    "priority_score": item["max_uncertainty"],
                    "queued_at": item["queued_at"],
                    "status": "pending",  # pending → scraping → resolved
                }
            )
    return rows
