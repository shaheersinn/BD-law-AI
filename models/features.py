"""app/models/features.py — CompanyFeature ORM model."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class CompanyFeature(Base):
    """
    Stores computed feature values for each company × feature × version × horizon.

    Sparse storage: is_null=True rows skipped by default (not stored).
    Feature vector retrieval: SELECT WHERE company_id=X AND horizon_days=30 AND version='v1'
    """
    __tablename__ = "company_features"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "feature_name", "feature_version", "horizon_days",
            name="uq_company_feature_version_horizon",
        ),
        Index("ix_cf_company_horizon", "company_id", "horizon_days"),
        Index("ix_cf_feature_name", "feature_name"),
        Index("ix_cf_computed_at", "computed_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False, index=True)
    feature_name = Column(String(100), nullable=False)
    feature_version = Column(String(10), nullable=False, default="v1")
    horizon_days = Column(Integer, nullable=False)       # 30 | 60 | 90
    category = Column(String(50), nullable=True)         # nlp | corporate | market | ...
    value = Column(Float, nullable=False)
    is_null = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float, nullable=False, default=1.0)
    signal_count = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(tz=timezone.utc))
    metadata = Column(Text, nullable=True)               # JSON string for extra debug info
