"""
app/models/trigger.py — Trigger and Alert ORM models.

Triggers are live signal events detected by scrapers.
Alerts are high-confidence triggers that fire notifications to partners.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trigger(Base):
    """A live signal event detected by a scraper."""

    __tablename__ = "triggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2000))
    urgency: Mapped[int] = mapped_column(Integer, default=50)
    practice_area: Mapped[str | None] = mapped_column(String(100))
    practice_confidence: Mapped[int] = mapped_column(Integer, default=0)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmed: Mapped[bool | None] = mapped_column(Boolean)
    dismissed: Mapped[bool | None] = mapped_column(Boolean)
    matter_opened: Mapped[bool | None] = mapped_column(Boolean)
    actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    actioned_by: Mapped[str | None] = mapped_column(String(200))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "trigger_type": self.trigger_type,
            "company_name": self.company_name,
            "client_id": self.client_id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "urgency": self.urgency,
            "practice_area": self.practice_area,
            "practice_confidence": self.practice_confidence,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "confirmed": self.confirmed,
            "dismissed": self.dismissed,
            "matter_opened": self.matter_opened,
            "actioned": self.actioned,
            "actioned_by": self.actioned_by,
        }


class Alert(Base):
    """A high-confidence trigger that fires a notification to a partner."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer, index=True)
    company_name: Mapped[str | None] = mapped_column(String(200))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed: Mapped[bool | None] = mapped_column(Boolean)
    dismissed: Mapped[bool | None] = mapped_column(Boolean)
    matter_opened: Mapped[bool | None] = mapped_column(Boolean)
    mandate_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
