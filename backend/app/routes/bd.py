"""
app/routes/bd.py — Business Development intelligence endpoints.
Router prefix: /v1/bd
"""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db

router = APIRouter(prefix="/v1/bd", tags=["bd"])


@router.get("/partners")
async def list_partners(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """BD partner profiles. Returns [] until data is seeded."""
    return []


@router.get("/partner-coaching/{partner_id}")
async def partner_coaching(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> dict[str, Any]:
    """BD coaching data for one partner."""
    return {
        "partner_id": partner_id,
        "recent_wins": [],
        "pipeline": [],
        "trends": [],
        "last_updated": datetime.now(tz=UTC).isoformat(),
    }


@router.get("/pitch-history")
async def pitch_history(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Past pitches with outcome, competitor, deal_size. Returns []."""
    return []


@router.get("/associate-activity")
async def associate_activity(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Associate BD metrics: utilization, specialization, alumni_potential. Returns []."""
    return []


@router.get("/content")
async def bd_content(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """BD content library items. Returns []."""
    return []


@router.post("/inquiries", status_code=201)
async def submit_inquiry(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> dict[str, Any]:
    """Persist a BD inquiry. Returns created record stub."""
    return {
        "id": "pending",
        "created_at": datetime.now(tz=UTC).isoformat(),
        "status": "received",
    }
