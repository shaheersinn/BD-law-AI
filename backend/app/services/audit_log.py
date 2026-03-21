"""
app/services/audit_log.py — Immutable audit trail.

Logs all:
  - AI generation calls (prompt key, user, client context, token count)
  - Data exports and bulk operations
  - User logins and auth events
  - Alert label actions (partner feedback)
  - Admin operations (user creation, model retrain)

Every row is append-only. No updates, no deletes.
Required for Law Society data governance obligations.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import AsyncSessionLocal, Base

log = logging.getLogger(__name__)


# ── ORM Model ─────────────────────────────────────────────────────────────────

class AuditEventType(str, Enum):
    ai_generate    = "ai_generate"
    login_success  = "login_success"
    login_failure  = "login_failure"
    logout         = "logout"
    data_export    = "data_export"
    alert_label    = "alert_label"
    trigger_label  = "trigger_label"
    model_retrain  = "model_retrain"
    user_create    = "user_create"
    user_update    = "user_update"
    scrape_trigger = "scrape_trigger"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(200))
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))   # "client", "trigger", etc.
    resource_id: Mapped[Optional[int]] = mapped_column(Integer)
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)               # arbitrary event metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(300))
    request_id: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# ── Service ───────────────────────────────────────────────────────────────────

async def log_event(
    event_type: AuditEventType,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """
    Write a single audit log entry.
    Uses a fresh DB session so it doesn't interfere with the request session.
    Never raises — audit failures must not break the main request.
    """
    try:
        async with AsyncSessionLocal() as db:
            entry = AuditLog(
                event_type=event_type.value,
                user_id=user_id,
                user_email=user_email,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail or {},
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            db.add(entry)
            await db.commit()
    except Exception as e:
        log.error("Audit log write failed (non-fatal): %s", e)


# ── FastAPI helper ─────────────────────────────────────────────────────────────

def extract_request_meta(request) -> dict:
    """Extract IP and User-Agent from a FastAPI Request object."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:300],
        "request_id": getattr(request.state, "request_id", None),
    }
