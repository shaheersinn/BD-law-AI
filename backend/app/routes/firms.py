"""
app/routes/firms.py — Law firm competitive intelligence endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/firms", tags=["firms"])


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/competitive")
async def get_competitive_firms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """
    Returns law firms from the companies table.

    Matches companies where sector ILIKE '%law%', name ILIKE '%llp%',
    or name ILIKE '%legal%'.
    """
    try:
        result = await db.execute(
            text("""
                SELECT
                    id,
                    name,
                    COALESCE(headcount, 0)               AS headcount,
                    COALESCE(practice_area_hints, '{}')  AS practice_areas
                FROM companies
                WHERE
                    sector ILIKE '%law%'
                    OR name ILIKE '%llp%'
                    OR name ILIKE '%legal%'
                ORDER BY name
                LIMIT 200
            """)
        )
        rows = result.mappings().all()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "headcount": r["headcount"] or 0,
                "practice_areas": list(r["practice_areas"]) if r["practice_areas"] else [],
                "recent_laterals": 0,
                "market_position": "unknown",
                "threat_level": "low",
            }
            for r in rows
        ]
    except Exception:
        log.exception("firms_competitive_fetch_failed")
        return []
