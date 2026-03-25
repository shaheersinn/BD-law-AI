"""
backend/app/routes/scores_8b_addition.py

Phase 8B adds ONE new endpoint to the existing scores router:

    GET /api/v1/scores/top-velocity?limit=20

Returns the top N companies by aggregate velocity score from the
most recent scoring_results row per company.

Drop this into scores.py — add the route to the existing router.
The route MUST be registered BEFORE /{company_id} to avoid path
collision (FastAPI matches in order: /top-velocity must come first).

SQL query:
    SELECT DISTINCT ON (company_id)
        sr.company_id, sr.velocity_score, sr.scores, sr.scored_at,
        c.name AS company_name, c.sector
    FROM scoring_results sr
    JOIN companies c ON c.id = sr.company_id
    WHERE sr.scored_at >= NOW() - INTERVAL '48 hours'
    ORDER BY company_id, scored_at DESC   -- DISTINCT ON selects latest per company
    -- then wrap as subquery sorted by velocity_score DESC

Paste this into backend/app/routes/scores.py:
"""

# ── Add this import at the top of scores.py ───────────────────────────────────
# from typing import Optional  # already imported
# from sqlalchemy import text   # already imported

# ── Add this route to the scores router in scores.py ─────────────────────────
# IMPORTANT: Register BEFORE the /{company_id} route

TOP_VELOCITY_SQL = """
WITH latest AS (
    SELECT DISTINCT ON (company_id)
        company_id, velocity_score, scores, scored_at, anomaly_score
    FROM scoring_results
    WHERE scored_at >= NOW() - INTERVAL '48 hours'
      AND velocity_score IS NOT NULL
    ORDER BY company_id, scored_at DESC
)
SELECT
    l.company_id,
    l.velocity_score,
    l.scores,
    l.scored_at,
    l.anomaly_score,
    c.name AS company_name,
    c.sector
FROM latest l
JOIN companies c ON c.id = l.company_id
ORDER BY l.velocity_score DESC
LIMIT :limit
"""


# ── Paste this function into scores.py ────────────────────────────────────────

"""
@router.get("/top-velocity")
async def get_top_velocity_companies(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_partner),
) -> list[dict]:
    '''
    Top N companies by 7-day mandate probability velocity.
    Returns company_id, velocity_score, top_practice_area, top_score_30d.
    Reads from most recent scoring_results per company (last 48h).
    Cached 15 minutes.
    '''
    import json
    from app.cache.client import get_cache

    cache = await get_cache()
    cache_key = f"top_velocity:{limit}"

    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # Cache miss — proceed to DB

    result = await db.execute(text(TOP_VELOCITY_SQL), {"limit": limit})
    rows = result.fetchall()

    output = []
    for row in rows:
        company_id, velocity, scores_json, scored_at, anomaly, name, sector = row

        # Find the highest-scoring practice area at 30d
        top_pa = None
        top_score_30d = 0.0
        if scores_json:
            scores = scores_json if isinstance(scores_json, dict) else json.loads(scores_json)
            for pa, horizons in scores.items():
                s30 = horizons.get("30d", 0.0) or 0.0
                if s30 > top_score_30d:
                    top_score_30d = s30
                    top_pa = pa

        output.append({
            "company_id": company_id,
            "company_name": name,
            "sector": sector,
            "velocity_score": round(float(velocity), 4),
            "top_practice_area": top_pa,
            "top_score_30d": round(top_score_30d, 4),
            "anomaly_score": round(float(anomaly), 4) if anomaly else None,
            "scored_at": scored_at.isoformat() if scored_at else None,
        })

    if cache:
        try:
            await cache.setex(cache_key, 900, json.dumps(output))  # 15 min TTL
        except Exception:
            pass

    return output
"""


# ── Summary ────────────────────────────────────────────────────────────────────
# Files to modify in existing codebase:
#   backend/app/routes/scores.py
#     - Add TOP_VELOCITY_SQL string
#     - Add get_top_velocity_companies() route BEFORE /{company_id}
#     - Route: GET /top-velocity
#     - Auth: require_partner (partners + admins)
#     - Cache: 15 min TTL under key top_velocity:{limit}
#
# No new migration needed — reads from existing scoring_results table.
# No new env vars needed.
