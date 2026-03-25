"""
app/models/training.py — Training dataset tracking ORM models for Phase 4.

TrainingDataset: records each curator export run with statistics and file path.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import ARRAY, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DatasetStatus(StrEnum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class TrainingDataset(Base):
    """
    Records a single training dataset export produced by Agent 019 (Training Data Curator).

    Each record captures what labels were included, quality filters applied,
    and where the exported file lives (local path or DigitalOcean Spaces key).
    """

    __tablename__ = "training_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DatasetStatus.pending.value
    )
    # Label counts in this dataset
    label_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uncertain_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Scope
    practice_areas: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    horizons: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    # Quality filter applied during curation
    min_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    # Export details
    export_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, default="parquet")
    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_td_status", "status"),
        Index("ix_td_created_at", "created_at"),
    )

    @property
    def duration_seconds(self) -> float | None:
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None
