"""0009_phase12_optimization

Phase 12: Post-Launch Optimization

New tables:
    - usage_reports:            Weekly usage analytics snapshots
    - score_quality_reports:    Per-practice-area ML accuracy summaries
    - signal_weight_overrides:  Human BD team multipliers (override ML-calibrated weights)
    - retrain_submissions:      Targeted Azure ML retraining job records

Revision ID: 0009_phase12_optimization
Revises: 0007_phase7_api
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0009_phase12_optimization"
down_revision = "0007_phase7_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── usage_reports ──────────────────────────────────────────────────────────
    # Weekly snapshots of API usage: top companies, practice areas, response times
    op.create_table(
        "usage_reports",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("top_companies", JSONB, nullable=True),       # [{company_id, name, request_count}]
        sa.Column("top_practice_areas", JSONB, nullable=True),  # [{practice_area, view_count}]
        sa.Column("p50_ms", sa.Float, nullable=True),
        sa.Column("p95_ms", sa.Float, nullable=True),
        sa.Column("cache_hit_rate", sa.Float, nullable=True),
        sa.Column("endpoint_breakdown", JSONB, nullable=True),  # [{endpoint, p50, p95, count}]
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_usage_reports_week_start", "usage_reports", ["week_start"])

    # ── score_quality_reports ──────────────────────────────────────────────────
    # Per-practice-area precision/recall summaries from prediction_accuracy_log
    op.create_table(
        "score_quality_reports",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("summary", JSONB, nullable=True),    # [{practice_area, precision, recall, avg_lead_days, sample_count, low_data_flag}]
        sa.Column("worst_five", JSONB, nullable=True), # [practice_area strings]
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_score_quality_reports_date", "score_quality_reports", ["report_date"]
    )

    # ── signal_weight_overrides ────────────────────────────────────────────────
    # Human BD team multipliers: applied after ML-calibrated weights. Human wins.
    op.create_table(
        "signal_weight_overrides",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("signal_type", sa.String(100), nullable=False),
        sa.Column("practice_area", sa.String(100), nullable=False),
        sa.Column("multiplier", sa.Float, nullable=False),  # 0.01–5.0 enforced in app layer
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "set_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_signal_weight_overrides_active",
        "signal_weight_overrides",
        ["signal_type", "practice_area"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # ── retrain_submissions ────────────────────────────────────────────────────
    # Records of targeted Azure ML retraining jobs submitted by Agent 035
    op.create_table(
        "retrain_submissions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("practice_areas", JSONB, nullable=False),    # list of practice area strings
        sa.Column("drift_alert_ids", JSONB, nullable=True),    # which model_drift_alerts triggered this
        sa.Column("azure_job_id", sa.String(200), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'submitted'")),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_retrain_submissions_submitted_at", "retrain_submissions", ["submitted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_retrain_submissions_submitted_at", "retrain_submissions")
    op.drop_table("retrain_submissions")
    op.drop_index("ix_signal_weight_overrides_active", "signal_weight_overrides")
    op.drop_table("signal_weight_overrides")
    op.drop_index("ix_score_quality_reports_date", "score_quality_reports")
    op.drop_table("score_quality_reports")
    op.drop_index("ix_usage_reports_week_start", "usage_reports")
    op.drop_table("usage_reports")
