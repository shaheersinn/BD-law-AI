"""
app/routes/bd.py — BD (Business Development) intelligence endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/bd", tags=["bd"])


# ── Pydantic models ────────────────────────────────────────────────────────────


class InquiryRequest(BaseModel):
    company_name: str
    practice_area: str | None = None
    notes: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/partners")
async def list_partners(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Returns list of users with role='partner'."""
    try:
        result = await db.execute(
            text("""
                SELECT id, email, full_name, role
                FROM users
                WHERE role = 'partner'
                ORDER BY full_name
            """)
        )
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        log.exception("bd_partners_fetch_failed")
        return []


@router.get("/partner-coaching/{partner_id}")
async def get_partner_coaching(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Returns coaching insights for a partner."""
    try:
        result = await db.execute(
            text(
                "SELECT id, email, full_name, role FROM users WHERE id = :pid AND role = 'partner'"
            ),
            {"pid": partner_id},
        )
        row = result.mappings().first()
        if not row:
            return {
                "partner_id": partner_id,
                "metrics": {},
                "recommendations": [],
            }
        return {
            "partner_id": partner_id,
            "metrics": {
                "fast_close_rate": 0.0,
                "slow_close_rate": 0.0,
                "open_followups": 0,
                "last_content_days": 0,
                "top_referral_source": None,
            },
            "recommendations": [],
        }
    except Exception:
        log.exception("bd_partner_coaching_failed", partner_id=partner_id)
        return {
            "partner_id": partner_id,
            "metrics": {},
            "recommendations": [],
        }


@router.get("/pitch-history")
async def get_pitch_history(
    current_user: User = Depends(require_auth),
):
    """Pitch history. In future this will query a mandate_pitches table."""
    return []


@router.get("/associate-activity")
async def get_associate_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Returns list of associates with activity summary."""
    try:
        result = await db.execute(
            text("""
                SELECT id AS user_id, email, full_name
                FROM users
                WHERE role = 'associate'
                ORDER BY full_name
            """)
        )
        rows = result.mappings().all()
        return [
            {
                "user_id": r["user_id"],
                "email": r["email"],
                "full_name": r["full_name"],
                "activity_count": 0,
                "pitch_support_count": 0,
                "content_draft_count": 0,
                "engagement_score": 0.0,
            }
            for r in rows
        ]
    except Exception:
        log.exception("bd_associate_activity_failed")
        return []


@router.get("/writing-samples/{partner_id}")
async def get_writing_samples(
    partner_id: int,
    current_user: User = Depends(require_auth),
):
    """Writing samples. No writing_samples table yet."""
    return []


@router.get("/content")
async def get_bd_content(
    current_user: User = Depends(require_auth),
):
    """BD content library. No bd_content table yet."""
    return []


@router.post("/inquiries")
async def log_inquiry(
    req: InquiryRequest,
    current_user: User = Depends(require_auth),
):
    """Log a BD inquiry."""
    log.info(
        "bd_inquiry_logged",
        company_name=req.company_name,
        practice_area=req.practice_area,
        notes=req.notes,
        logged_by=current_user.id,
    )
    return {"status": "logged", "message": "BD inquiry recorded"}
