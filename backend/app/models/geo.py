"""
app/models/geo.py — Geospatial intelligence ORM models.

JetTrack, FootTrafficEvent, SatelliteSignal, PermitFiling.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JetTrack(Base):
    """Corporate jet track record."""

    __tablename__ = "jet_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tail_number: Mapped[str | None] = mapped_column(String(20))
    executive: Mapped[str | None] = mapped_column(String(200))
    origin_icao: Mapped[str | None] = mapped_column(String(10))
    origin_name: Mapped[str | None] = mapped_column(String(200))
    dest_icao: Mapped[str | None] = mapped_column(String(10))
    dest_name: Mapped[str | None] = mapped_column(String(200))
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    signal_text: Mapped[str | None] = mapped_column(Text)
    predicted_mandate: Mapped[str | None] = mapped_column(String(100))
    relationship_warmth: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "tail_number": self.tail_number,
            "executive": self.executive,
            "origin_icao": self.origin_icao,
            "origin_name": self.origin_name,
            "dest_icao": self.dest_icao,
            "dest_name": self.dest_name,
            "departed_at": self.departed_at.isoformat() if self.departed_at else None,
            "confidence": self.confidence,
            "is_flagged": self.is_flagged,
            "signal_text": self.signal_text,
            "predicted_mandate": self.predicted_mandate,
            "relationship_warmth": self.relationship_warmth,
        }


class FootTrafficEvent(Base):
    """Foot traffic detection event near competitor locations."""

    __tablename__ = "foot_traffic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    location_name: Mapped[str | None] = mapped_column(String(300))
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    threat_assessment: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_company": self.target_company,
            "location_name": self.location_name,
            "device_count": self.device_count,
            "avg_duration_minutes": self.avg_duration_minutes,
            "severity": self.severity,
            "threat_assessment": self.threat_assessment,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }


class SatelliteSignal(Base):
    """Satellite intelligence observation."""

    __tablename__ = "satellite_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(300))
    observation: Mapped[str | None] = mapped_column(Text)
    legal_inference: Mapped[str | None] = mapped_column(Text)
    signal_type: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "location": self.location,
            "observation": self.observation,
            "legal_inference": self.legal_inference,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "urgency": self.urgency,
        }


class PermitFiling(Base):
    """Permit filing record indicating potential legal work."""

    __tablename__ = "permit_filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    permit_type: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(300))
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    project_type: Mapped[str | None] = mapped_column(String(200))
    legal_work_triggered: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    estimated_fee: Mapped[str | None] = mapped_column(String(50))
    urgency: Mapped[str] = mapped_column(String(20), default="medium")
    lead_partner: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "permit_type": self.permit_type,
            "location": self.location,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "project_type": self.project_type,
            "legal_work_triggered": self.legal_work_triggered or [],
            "estimated_fee": self.estimated_fee,
            "urgency": self.urgency,
            "lead_partner": self.lead_partner,
        }
