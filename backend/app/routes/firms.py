"""
app/routes/firms.py — Competitive law firm intelligence.
Router prefix: /v1/firms
"""
from __future__ import annotations
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db

router = APIRouter(prefix="/v1/firms", tags=["firms"])


@router.get("/competitive")
async def competitive_intel(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Competitive firm data: name, practice_strengths, lawyer_count, threat_level.
    Queries law_firms table; returns [] if empty.
    """
    from sqlalchemy import select  # noqa: PLC0415
    try:
        from app.models.law_firm import LawFirm  # noqa: PLC0415
        result = await db.execute(select(LawFirm).limit(50))
        firms = result.scalars().all()
        return [
            {
                "id": str(f.id),
                "name": f.name,
                "tier": getattr(f, "tier", None),
                "practice_strengths": getattr(f, "practice_strengths", {}),
                "lawyer_count": getattr(f, "lawyer_count", None),
                "threat_level": "medium",
            }
            for f in firms
        ]
    except Exception:
        return []
