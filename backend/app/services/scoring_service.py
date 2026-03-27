"""
app/services/scoring_service.py — Phase 7 scoring business logic.

Provides cache-aware score retrieval used by API endpoints.
Keeps route handlers thin — all scoring retrieval logic lives here.

Cache strategy:
    key:  score:{company_id}:{YYYY-MM-DD}
    TTL:  6 hours (21 600 s)
    Invalidation: call invalidate_score_cache() on new signal ingestion.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.client import cache

log = logging.getLogger(__name__)

TTL_SCORE = 21_600  # 6 hours


def score_cache_key(company_id: int, date_str: str) -> str:
    return f"score:{company_id}:{date_str}"


def _today_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def get_company_score(
    company_id: int,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """
    Retrieve the latest score for a company.

    1. Check Redis cache.
    2. On miss: query scoring_results for the most recent row.
    3. On hit: hydrate and cache for 6 hours.
    4. Return None if no score exists (404 → caller's responsibility).
    """
    today = _today_utc()
    cache_key = score_cache_key(company_id, today)

    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        result = await db.execute(
            text("""
                SELECT
                    sr.id,
                    sr.company_id,
                    c.name        AS company_name,
                    sr.scored_at,
                    sr.scores,
                    sr.velocity_score,
                    sr.anomaly_score,
                    sr.confidence_low,
                    sr.confidence_high,
                    sr.top_signals,
                    sr.model_versions
                FROM scoring_results sr
                JOIN companies c ON c.id = sr.company_id
                WHERE sr.company_id = :company_id
                ORDER BY sr.scored_at DESC
                LIMIT 1
            """),
            {"company_id": company_id},
        )
        row = result.mappings().first()
    except Exception:
        log.exception("scoring_service: DB error fetching score for company %d", company_id)
        return None

    if row is None:
        return None

    data = _hydrate_score_row(row)
    await cache.set(cache_key, data, ttl=TTL_SCORE)
    return data


async def get_batch_scores(
    company_ids: list[int],
    practice_areas: list[str] | None,
    db: AsyncSession,
) -> list[dict[str, Any] | None]:
    """
    Retrieve scores for multiple companies.

    1. Check cache for each id.
    2. Bulk-query DB for misses in one SELECT.
    3. Merge results preserving input order.
    4. Filter to requested practice_areas if supplied.
    Returns list aligned with company_ids; None where no score exists.
    """
    today = _today_utc()

    # Check cache for all ids
    cached_map: dict[int, dict[str, Any]] = {}
    miss_ids: list[int] = []

    for cid in company_ids:
        hit = await cache.get(score_cache_key(cid, today))
        if hit is not None:
            cached_map[cid] = hit  # type: ignore[assignment]
        else:
            miss_ids.append(cid)

    # Bulk fetch misses
    db_map: dict[int, dict[str, Any]] = {}
    if miss_ids:
        try:
            result = await db.execute(
                text("""
                    SELECT DISTINCT ON (sr.company_id)
                        sr.id,
                        sr.company_id,
                        c.name        AS company_name,
                        sr.scored_at,
                        sr.scores,
                        sr.velocity_score,
                        sr.anomaly_score,
                        sr.confidence_low,
                        sr.confidence_high,
                        sr.top_signals,
                        sr.model_versions
                    FROM scoring_results sr
                    JOIN companies c ON c.id = sr.company_id
                    WHERE sr.company_id = ANY(:ids)
                    ORDER BY sr.company_id, sr.scored_at DESC
                """),
                {"ids": miss_ids},
            )
            for row in result.mappings():
                data = _hydrate_score_row(row)
                cid = int(row["company_id"])
                db_map[cid] = data
                await cache.set(score_cache_key(cid, today), data, ttl=TTL_SCORE)
        except Exception:
            log.exception("scoring_service: DB error in batch fetch")

    # Assemble output in input order
    output: list[dict[str, Any] | None] = []
    for cid in company_ids:
        data = cached_map.get(cid) or db_map.get(cid)
        if data is not None and practice_areas:
            # Filter scores to requested practice areas only
            data = dict(data)
            data["scores"] = {
                pa: v for pa, v in data.get("scores", {}).items() if pa in practice_areas
            }
        output.append(data)

    return output


async def get_company_explain(
    company_id: int,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """
    Return SHAP counterfactuals for the top 5 highest-scoring practice areas.
    Queries scoring_explanations joined to most recent scoring_result.
    """
    try:
        result = await db.execute(
            text("""
                SELECT
                    se.practice_area,
                    se.horizon,
                    se.score,
                    se.top_shap_features,
                    se.counterfactuals,
                    se.base_value,
                    se.explained_at
                FROM scoring_explanations se
                WHERE se.company_id = :company_id
                ORDER BY se.score DESC
                LIMIT 5
            """),
            {"company_id": company_id},
        )
        rows = result.mappings().all()
    except Exception:
        log.exception("scoring_service: DB error fetching explanations for company %d", company_id)
        return []

    explanations = []
    for row in rows:
        explanations.append(
            {
                "practice_area": row["practice_area"],
                "horizon": row["horizon"],
                "score": row["score"],
                "top_shap_features": _parse_json_field(row["top_shap_features"]),
                "counterfactuals": _parse_json_field(row["counterfactuals"]),
                "base_value": row["base_value"],
                "explained_at": row["explained_at"].isoformat() if row["explained_at"] else None,
            }
        )
    return explanations


async def invalidate_score_cache(company_id: int) -> None:
    """
    Invalidate cached score for a company.
    Called by live feed processor after new signal ingestion.
    """
    today = _today_utc()
    key = score_cache_key(company_id, today)
    deleted = await cache.delete(key)
    if deleted:
        log.debug("scoring_service: cache invalidated for company %d", company_id)


# ── Internal helpers ───────────────────────────────────────────────────────────


def _hydrate_score_row(row: Any) -> dict[str, Any]:
    """Convert a scoring_results DB row into the API response dict."""
    return {
        "company_id": row["company_id"],
        "company_name": row["company_name"],
        "scored_at": (
            row["scored_at"].isoformat()
            if hasattr(row["scored_at"], "isoformat")
            else str(row["scored_at"])
        ),
        "scores": _parse_json_field(row["scores"]),
        "velocity_score": row["velocity_score"],
        "anomaly_score": row["anomaly_score"],
        "confidence": {
            "low": row["confidence_low"],
            "high": row["confidence_high"],
        },
        "top_signals": _parse_json_field(row["top_signals"]) or [],
        "model_versions": _parse_json_field(row["model_versions"]) or {},
    }


def _parse_json_field(value: Any) -> Any:
    """Parse a JSON field that may already be a dict/list or a JSON string."""
    if value is None:
        return None
    if isinstance(value, dict | list):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
