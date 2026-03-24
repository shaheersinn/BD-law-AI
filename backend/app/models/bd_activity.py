"""
app/models/bd_activity.py — BD coaching, content attribution, and ghost studio models.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    slack_id: Mapped[str | None] = mapped_column(String(50))
    practice_areas: Mapped[list] = mapped_column(JSONB, default=list)
    target_industries: Mapped[list] = mapped_column(JSONB, default=list)
    firm_name: Mapped[str] = mapped_column(String(200), default="Halcyon Legal Partners LLP")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    activities: Mapped[list["BDActivity"]] = relationship(
        "BDActivity", back_populates="partner", lazy="dynamic"
    )
    content_pieces: Mapped[list["ContentPiece"]] = relationship(
        "ContentPiece", back_populates="partner"
    )
    writing_samples: Mapped[list["WritingSample"]] = relationship(
        "WritingSample", back_populates="partner"
    )
    referral_contacts: Mapped[list["ReferralContact"]] = relationship(
        "ReferralContact", back_populates="partner"
    )


class BDActivity(Base):
    """One logged BD touchpoint by a partner."""

    __tablename__ = "bd_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partners.id"), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # meeting/call/event/proposal/follow_up/cle_talk/linkedin_post
    contact_name: Mapped[str | None] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(200))
    contact_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # client/prospect/referral_accountant/referral_banker
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    matter_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("matters.id"))
    had_followup_within_48h: Mapped[bool | None] = mapped_column(Boolean)
    led_to_matter: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)

    partner: Mapped["Partner"] = relationship("Partner", back_populates="activities")


class MatterSource(Base):
    """Attribution record: where did each new matter come from?"""

    __tablename__ = "matter_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    matter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matters.id"), nullable=False, unique=True
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # referral_accountant/referral_banker/event/linkedin/cold_outreach/existing_client
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_firm: Mapped[str | None] = mapped_column(String(200))
    first_touch: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    days_to_close: Mapped[int | None] = mapped_column(Integer)


class ReferralContact(Base):
    """Accountants, bankers, and other referral sources per partner."""

    __tablename__ = "referral_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partners.id"), nullable=False, index=True
    )
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    firm_name: Mapped[str | None] = mapped_column(String(200))
    contact_type: Mapped[str] = mapped_column(
        String(50), default="accountant"
    )  # accountant/banker/consultant/lawyer_other_firm
    last_contact: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matters_sent: Mapped[int] = mapped_column(Integer, default=0)
    revenue_sent: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    partner: Mapped["Partner"] = relationship("Partner", back_populates="referral_contacts")


class ContentPiece(Base):
    """Thought-leadership content piece published by a partner."""

    __tablename__ = "content_pieces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partners.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # linkedin_post/article/cle_talk/client_alert/podcast
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    topic: Mapped[str | None] = mapped_column(String(300))
    views: Mapped[int] = mapped_column(Integer, default=0)
    engagements: Mapped[int] = mapped_column(Integer, default=0)
    inquiries_attributed: Mapped[int] = mapped_column(Integer, default=0)
    body_text: Mapped[str | None] = mapped_column(Text)

    partner: Mapped["Partner"] = relationship("Partner", back_populates="content_pieces")


class WritingSample(Base):
    """Past writing by a partner used as few-shot examples for ghost studio."""

    __tablename__ = "writing_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partners.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="linkedin_post")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["Partner"] = relationship("Partner", back_populates="writing_samples")


class ClientInquiry(Base):
    """Logged client inquiry for content attribution."""

    __tablename__ = "client_inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partners.id"), nullable=False, index=True
    )
    inquiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(
        String(50), default="cold"
    )  # linkedin/article/referral/cold/event
    attributed_content_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Alumni(Base):
    """Former firm members tracked at in-house positions."""

    __tablename__ = "alumni"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    current_role: Mapped[str] = mapped_column(String(200), nullable=False)
    current_company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    departure_year: Mapped[int | None] = mapped_column(Integer)
    mentor_partner: Mapped[str | None] = mapped_column(String(100))
    warmth_score: Mapped[int] = mapped_column(Integer, default=50)
    linkedin_url: Mapped[str | None] = mapped_column(String(400))
    has_active_trigger: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
