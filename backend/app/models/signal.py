"""
app/models/signal.py — all intelligence signal ORM models.
Covers: Prospect, Trigger, Alert, JetTrack, FootTrafficEvent,
        SatelliteSignal, PermitFiling, RegulatoryAlert, CompetitorThreat.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class AlertThreshold(str, enum.Enum):
    critical = "CRITICAL"
    high = "HIGH"
    moderate = "MODERATE"
    watch = "WATCH"


class TriggerSource(str, enum.Enum):
    sedar = "SEDAR"
    edgar = "EDGAR"
    canlii = "CANLII"
    jobs = "JOBS"
    osc = "OSC"
    osfi = "OSFI"
    fintrac = "FINTRAC"
    comp_bureau = "COMP_BUREAU"
    news = "NEWS"
    linkedin = "LINKEDIN"


# ── Prospect ───────────────────────────────────────────────────────────────────

class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))

    # Scoring
    legal_urgency_score: Mapped[int] = mapped_column(Integer, default=0)   # 0-100
    predicted_need: Mapped[str | None] = mapped_column(String(200))
    estimated_value: Mapped[str | None] = mapped_column(String(50))
    outreach_window: Mapped[str | None] = mapped_column(String(50))
    warmth: Mapped[str] = mapped_column(String(20), default="cold")         # cold/lukewarm/warm

    # Raw signals (JSON list of strings)
    signals: Mapped[list] = mapped_column(JSONB, default=list)

    score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Live trigger feed ──────────────────────────────────────────────────────────

class Trigger(Base):
    """
    Real-time legal trigger — one row per detected event from any scraper.
    Powers the Live Triggers page.
    """

    __tablename__ = "triggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[TriggerSource] = mapped_column(
        Enum(TriggerSource), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clients.id"), index=True
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(800))

    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    urgency: Mapped[int] = mapped_column(Integer, default=50)         # 0-100
    practice_area: Mapped[str | None] = mapped_column(String(100))
    practice_confidence: Mapped[int] = mapped_column(Integer, default=50)

    # Partner feedback loop
    confirmed: Mapped[bool | None] = mapped_column(Boolean)
    dismissed: Mapped[bool | None] = mapped_column(Boolean)
    matter_opened: Mapped[bool | None] = mapped_column(Boolean)
    actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    actioned_by: Mapped[str | None] = mapped_column(String(100))

    # Training features (computed nightly)
    features: Mapped[dict | None] = mapped_column(JSONB)


# ── Mandate alert (scored convergence) ─────────────────────────────────────────

class Alert(Base):
    """
    Fired when a company's convergence score crosses a threshold.
    One alert per threshold crossing per company.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clients.id"), index=True
    )
    is_existing_client: Mapped[bool] = mapped_column(Boolean, default=False)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    prev_score: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[AlertThreshold] = mapped_column(Enum(AlertThreshold), nullable=False)

    practice_area: Mapped[str | None] = mapped_column(String(100))
    pa_confidence: Mapped[float | None] = mapped_column(Float)
    top_signals: Mapped[list] = mapped_column(JSONB, default=list)
    routed_to: Mapped[list] = mapped_column(JSONB, default=list)   # list of partner IDs

    # Feedback
    confirmed: Mapped[bool | None] = mapped_column(Boolean)
    dismissed: Mapped[bool | None] = mapped_column(Boolean)
    matter_opened: Mapped[bool | None] = mapped_column(Boolean)
    matter_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("matters.id"))
    mandate_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# ── Geospatial signals ─────────────────────────────────────────────────────────

class JetTrack(Base):
    __tablename__ = "jet_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tail_number: Mapped[str] = mapped_column(String(20), nullable=False)
    executive: Mapped[str | None] = mapped_column(String(200))
    origin_icao: Mapped[str] = mapped_column(String(10), nullable=False)
    origin_name: Mapped[str | None] = mapped_column(String(200))
    dest_icao: Mapped[str] = mapped_column(String(10), nullable=False)
    dest_name: Mapped[str | None] = mapped_column(String(200))
    departed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_text: Mapped[str | None] = mapped_column(Text)
    predicted_mandate: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    relationship_warmth: Mapped[int] = mapped_column(Integer, default=0)
    bay_street_trip_count: Mapped[int] = mapped_column(Integer, default=1)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FootTrafficEvent(Base):
    __tablename__ = "foot_traffic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clients.id"))
    location_name: Mapped[str] = mapped_column(String(300), nullable=False)
    location_address: Mapped[str | None] = mapped_column(String(300))
    location_type: Mapped[str] = mapped_column(String(50))  # competitor/regulator/bank
    device_count: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    threat_assessment: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    recommended_action: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SatelliteSignal(Base):
    __tablename__ = "satellite_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clients.id"))
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    signal_type: Mapped[str] = mapped_column(String(50))  # Workforce/Construction/Environmental
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    legal_inference: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")
    lead_partner: Mapped[str | None] = mapped_column(String(100))
    imagery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PermitFiling(Base):
    __tablename__ = "permit_filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clients.id"))
    permit_type: Mapped[str] = mapped_column(String(200), nullable=False)
    project_type: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    legal_work_triggered: Mapped[list] = mapped_column(JSONB, default=list)
    urgency: Mapped[str] = mapped_column(String(20), default="medium")
    estimated_fee: Mapped[str | None] = mapped_column(String(30))
    lead_partner: Mapped[str | None] = mapped_column(String(100))
    source_portal: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(800))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Regulatory alerts ──────────────────────────────────────────────────────────

class RegulatoryAlert(Base):
    __tablename__ = "regulatory_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(800))
    practice_area: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    affected_client_ids: Mapped[list] = mapped_column(JSONB, default=list)


# ── Competitor intelligence ────────────────────────────────────────────────────

class CompetitorThreat(Base):
    __tablename__ = "competitor_threats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    firm_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signal: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50))  # Lateral Hire/Practice Expansion/etc.
    level: Mapped[str] = mapped_column(String(20), default="medium")
    affected_clients: Mapped[list] = mapped_column(JSONB, default=list)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
