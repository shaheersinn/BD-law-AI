"""
app/models/class_action_score.py — Class action risk scoring convergence output.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ClassActionScore(Base):
    __tablename__ = "class_action_scores"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True)
    probability = Column(Float, nullable=False)  # 0.0–1.0
    predicted_type = Column(
        String(100)
    )  # securities|product_liability|privacy|employment|environmental|competition
    time_horizon_days = Column(Integer)  # 30, 60, or 90
    contributing_signals = Column(JSONB)  # [{signal_type, weight, source_id, date}]
    confidence = Column(Float)  # 0.0–1.0
    scored_at = Column(DateTime, server_default=func.now())
