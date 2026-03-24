"""
app/models/client.py — Client, Matter, BillingRecord ORM models.
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskLevel(enum.StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship partner
    partner_name: Mapped[str | None] = mapped_column(String(100))
    gc_name: Mapped[str | None] = mapped_column(String(200))
    gc_email: Mapped[str | None] = mapped_column(String(200))
    gc_linkedin: Mapped[str | None] = mapped_column(String(400))

    # Practice areas (stored as array)
    practice_groups: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # ML scores (updated nightly)
    churn_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    churn_score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.low)

    # Financial
    estimated_annual_spend: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    annual_revenue: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    wallet_share_pct: Mapped[int | None] = mapped_column(Integer)  # 0-100

    # Activity
    days_since_last_contact: Mapped[int] = mapped_column(Integer, default=0)
    days_since_last_matter: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    matters: Mapped[list["Matter"]] = relationship(
        "Matter", back_populates="client", lazy="selectin"
    )
    billing_records: Mapped[list["BillingRecord"]] = relationship(
        "BillingRecord", back_populates="client"
    )
    churn_signals: Mapped[list["ChurnSignal"]] = relationship(
        "ChurnSignal", back_populates="client", lazy="selectin"
    )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["practice_groups"] = self.practice_groups or []
        d["risk_level"] = self.risk_level.value if self.risk_level else "low"
        d["churn_signals"] = [s.to_dict() for s in (self.churn_signals or [])]
        return d


class Matter(Base):
    __tablename__ = "matters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    matter_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    practice_area: Mapped[str | None] = mapped_column(String(100))
    lead_partner: Mapped[str | None] = mapped_column(String(100))
    opened_at: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[date | None] = mapped_column(Date)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    total_billed: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    referral_source: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship("Client", back_populates="matters")


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    matter_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("matters.id"), index=True)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount_billed: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount_collected: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    write_off_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    has_dispute: Mapped[bool] = mapped_column(Boolean, default=False)

    client: Mapped["Client"] = relationship("Client", back_populates="billing_records")


class ChurnSignal(Base):
    """Individual signal contributing to a client's churn score."""

    __tablename__ = "churn_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    signal_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    client: Mapped["Client"] = relationship("Client", back_populates="churn_signals")
