"""
app/models/signal.py — Signal ORM model.

A Signal is a single scraped data point that may indicate legal mandate need.

Every scraper writes Signal records. The feature engineering pipeline (Phase 2)
reads signals and transforms them into numeric features per company per day.

Design:
  - content_hash (SHA256) prevents duplicate signals from the same source
  - practice_area_flags: 34-bit integer, one bit per practice area (bitmask)
  - signal_strength: raw signal weight before ML calibration (0.0–1.0)
  - source_reliability: trust score for the source (configured in BaseScraper)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ── Practice Area Bitmask Constants ───────────────────────────────────────────
# Each practice area has a fixed bit position.
# Signal.practice_area_flags is an integer bitmask.
# Example: a signal relevant to M&A (bit 0) and Insolvency (bit 4) = 0b10001 = 17

PRACTICE_AREA_BITS = {
    "ma_corporate": 0,
    "litigation": 1,
    "regulatory_compliance": 2,
    "employment_labour": 3,
    "insolvency_restructuring": 4,
    "securities_capital_markets": 5,
    "competition_antitrust": 6,
    "privacy_cybersecurity": 7,
    "environmental_indigenous_energy": 8,
    "tax": 9,
    "real_estate_construction": 10,
    "banking_finance": 11,
    "intellectual_property": 12,
    "immigration_corporate": 13,
    "infrastructure_project_finance": 14,
    "wills_estates": 15,
    "administrative_public_law": 16,
    "arbitration": 17,
    "class_actions": 18,
    "construction_disputes": 19,
    "defamation_media": 20,
    "financial_regulatory": 21,
    "franchise_distribution": 22,
    "health_life_sciences": 23,
    "insurance_reinsurance": 24,
    "international_trade_customs": 25,
    "mining_natural_resources": 26,
    "municipal_land_use": 27,
    "nfp_charity": 28,
    "pension_benefits": 29,
    "product_liability": 30,
    "sports_entertainment": 31,
    "technology_fintech_regulatory": 32,
    "data_privacy_technology": 33,
}


class Signal(Base):
    """
    A single scraped data point relevant to legal mandate prediction.

    Written by scrapers, read by the feature engineering pipeline.
    Stored in PostgreSQL (not MongoDB — signals are structured with FK to Company).
    """

    __tablename__ = "signals"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # ── Company FK ────────────────────────────────────────────────────────────
    company_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Null until entity resolution links signal to a company",
    )

    # ── Source Identification ─────────────────────────────────────────────────
    scraper_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Scraper that produced this signal (e.g., 'osc_enforcement')",
    )
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Signal Classification ─────────────────────────────────────────────────
    signal_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="e.g., enforcement_action, corporate_filing, job_posting, news_mention",
    )
    practice_area_flags: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="34-bit bitmask — one bit per practice area"
    )
    primary_practice_area: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Highest-confidence practice area for this signal",
    )

    # ── Signal Content ────────────────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_entity_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
        comment="Company name as it appeared in the source (before entity resolution)",
    )

    # ── Deduplication ─────────────────────────────────────────────────────────
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="SHA256 of (scraper_name + source_url + published_at.date) — prevents duplicates",
    )

    # ── Signal Quality ────────────────────────────────────────────────────────
    signal_strength: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, comment="Raw pre-ML signal weight 0.0–1.0"
    )
    source_reliability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.8,
        comment="Trust score for the source 0.0–1.0 (configured per scraper)",
    )

    # ── Entity Resolution ─────────────────────────────────────────────────────
    entity_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="True after entity resolution has linked signal to a Company",
    )
    entity_resolution_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Confidence of entity match 0.0–1.0"
    )

    # ── Extra Metadata ────────────────────────────────────────────────────────
    metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Source-specific fields (fine amount, case number, etc.)"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the original event occurred / was published",
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    company: Mapped[Company | None] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Company", back_populates="signals", lazy="noload"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_signals_company_type_date", "company_id", "signal_type", "published_at"),
        Index("ix_signals_practice_area", "primary_practice_area", "published_at"),
        Index("ix_signals_unresolved", "entity_resolved", "scraped_at"),
        Index("ix_signals_scraper_date", "scraper_name", "scraped_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Signal id={self.id} scraper={self.scraper_name!r} "
            f"type={self.signal_type!r} company_id={self.company_id}>"
        )

    def has_practice_area(self, practice_area: str) -> bool:
        """Check if this signal is relevant to a given practice area."""
        bit = PRACTICE_AREA_BITS.get(practice_area)
        if bit is None:
            return False
        return bool(self.practice_area_flags & (1 << bit))

    def set_practice_area(self, practice_area: str) -> None:
        """Set the bitmask bit for a given practice area."""
        bit = PRACTICE_AREA_BITS.get(practice_area)
        if bit is not None:
            self.practice_area_flags |= 1 << bit

    @property
    def practice_areas(self) -> list[str]:
        """Return list of practice area names from bitmask."""
        return [
            name
            for name, bit in PRACTICE_AREA_BITS.items()
            if self.practice_area_flags & (1 << bit)
        ]
