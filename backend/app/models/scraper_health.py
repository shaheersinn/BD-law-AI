"""
app/models/scraper_health.py — Scraper health and performance tracking.

Every scraper writes a health record after each run.
Agent 007 (Data Quality Sentinel) and Agent 008 (Canary) read this table.
The Phase 1B scraper audit dashboard queries this table.

Status values:
  healthy   — last run succeeded, failure rate < 5%
  degraded  — last run succeeded but performance declining
  failing   — last 3+ runs failed consecutively
  disabled  — manually disabled (e.g., source ToS changed)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScraperHealth(Base):
    """
    Tracks health and performance of every scraper over time.
    One row per scraper — updated in-place on each run.
    """

    __tablename__ = "scraper_health"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scraper_name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    scraper_category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="filings, legal, regulatory, jobs, market, news, social, geo, lawfirms"
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="healthy", index=True,
        comment="healthy | degraded | failing | disabled"
    )

    # ── Run Timing ────────────────────────────────────────────────────────────
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_run_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Failure Tracking ──────────────────────────────────────────────────────
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Volume Tracking ───────────────────────────────────────────────────────
    records_last_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_today_reset_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Performance Metrics ───────────────────────────────────────────────────
    avg_run_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_run_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate_7d: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Success rate over last 7 days (0.0–1.0)"
    )

    # ── Source Metadata ───────────────────────────────────────────────────────
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    source_reliability_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.8
    )
    requires_api_key: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=0
    )
    api_key_env_var: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Extra Diagnostics ─────────────────────────────────────────────────────
    diagnostics: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Last-run diagnostic payload (response codes, parse errors, etc.)"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_scraper_health_status_category", "status", "scraper_category"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScraperHealth scraper={self.scraper_name!r} "
            f"status={self.status!r} failures={self.consecutive_failures}>"
        )

    @property
    def failure_rate(self) -> float:
        """Overall failure rate across all runs."""
        if self.total_runs == 0:
            return 0.0
        return self.total_failures / self.total_runs

    def record_success(self, records: int, duration_ms: int) -> None:
        """Update health after a successful run."""
        from datetime import timezone

        now = datetime.now(tz=timezone.utc)
        self.last_run_at = now
        self.last_success_at = now
        self.last_run_duration_ms = duration_ms
        self.consecutive_failures = 0
        self.total_runs += 1
        self.records_last_run = records
        self.records_total += records
        self._update_daily_count(records, now)
        self._update_avg_duration(duration_ms)

        if self.success_rate_7d is not None and self.success_rate_7d > 0.95:
            self.status = "healthy"
        elif self.status == "failing":
            self.status = "degraded"

    def record_failure(self, error: str) -> None:
        """Update health after a failed run."""
        from datetime import timezone

        now = datetime.now(tz=timezone.utc)
        self.last_run_at = now
        self.last_error_at = now
        self.last_error_message = str(error)[:2000]
        self.consecutive_failures += 1
        self.total_runs += 1
        self.total_failures += 1
        self.records_last_run = 0

        if self.consecutive_failures >= 3:
            self.status = "failing"
        elif self.consecutive_failures >= 1:
            self.status = "degraded"

    def _update_daily_count(self, records: int, now: datetime) -> None:
        """Reset daily counter if it's a new day."""
        if (
            self.records_today_reset_date is None
            or self.records_today_reset_date.date() < now.date()
        ):
            self.records_today = records
            self.records_today_reset_date = now
        else:
            self.records_today += records

    def _update_avg_duration(self, duration_ms: int) -> None:
        """Rolling average duration."""
        if self.avg_run_duration_ms is None:
            self.avg_run_duration_ms = float(duration_ms)
        else:
            # Exponential moving average (alpha=0.1)
            self.avg_run_duration_ms = 0.9 * self.avg_run_duration_ms + 0.1 * duration_ms
