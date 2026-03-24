"""
app/models/ground_truth.py — Ground truth label ORM models for Phase 3.

Two tables:
  - LabelingRun: tracks each labeling pipeline execution
  - GroundTruthLabel: one label per (company, practice_area, horizon, window)
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LabelType(StrEnum):
    positive = "positive"
    negative = "negative"
    uncertain = "uncertain"


class RunType(StrEnum):
    retrospective = "retrospective"
    negative_sampling = "negative_sampling"
    full = "full"
    pseudo_label = "pseudo_label"


class RunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"


class LabelSource(StrEnum):
    retrospective = "retrospective"
    manual = "manual"
    active_learning = "active_learning"
    pseudo_label = "pseudo_label"


class LabelingRun(Base):
    """Records a single execution of the ground truth labeling pipeline."""

    __tablename__ = "labeling_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    companies_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_labels_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_labels_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    labels: Mapped[list[GroundTruthLabel]] = relationship(
        "GroundTruthLabel", back_populates="run", lazy="select"
    )

    @property
    def total_labels(self) -> int:
        return self.positive_labels_created + self.negative_labels_created

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class GroundTruthLabel(Base):
    """
    A ground truth label for a (company, practice_area, horizon_days, window) tuple.

    Positive label: company exhibited signals in [window_start, window_end] AND
    subsequently had a legal engagement event in the follow-up period.

    Negative label: company exhibited signals but had NO subsequent legal engagement.

    Unique constraint ensures one label per (company, practice_area, horizon, window_start).
    """

    __tablename__ = "ground_truth_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    labeling_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("labeling_runs.id", ondelete="SET NULL"), nullable=True
    )
    label_type: Mapped[str] = mapped_column(String(20), nullable=False)
    practice_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # IDs of signal_records rows that provided evidence for this label
    evidence_signal_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    # MongoDB document IDs (unstructured evidence)
    evidence_mongo_ids: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    label_source: Mapped[str] = mapped_column(String(50), nullable=False, default="retrospective")
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    run: Mapped[LabelingRun | None] = relationship("LabelingRun", back_populates="labels")

    __table_args__ = (
        Index("ix_gtl_company_id", "company_id"),
        Index("ix_gtl_label_type", "label_type"),
        Index("ix_gtl_practice_area", "practice_area"),
        Index("ix_gtl_horizon_days", "horizon_days"),
        Index("ix_gtl_labeling_run_id", "labeling_run_id"),
        Index("ix_gtl_company_label", "company_id", "label_type"),
    )
