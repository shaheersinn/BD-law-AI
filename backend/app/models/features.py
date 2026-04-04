"""app/models/features.py — CompanyFeature: pre-computed ML feature vectors."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanyFeature(Base):
    __tablename__ = "company_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_null: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(tz=UTC),
    )
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "feature_name",
            "feature_version",
            "horizon_days",
            name="uq_company_feature_version_horizon",
        ),
        Index(
            "ix_company_feature_lookup",
            "company_id",
            "horizon_days",
            "feature_version",
        ),
    )
