"""0008_phase9_feedback

Phase 9: Feedback Loop

New tables:
    - mandate_confirmations:    Records of confirmed mandates (manual + auto-detected)
    - prediction_accuracy_log:  Per-confirmation accuracy metrics vs prior predictions
    - model_drift_alerts:       Practice areas flagged for accuracy degradation

Revision ID: 0008_phase9_feedback
Revises: 0007_phase7_api
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_phase9_feedback"
down_revision = "0007_phase7_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── mandate_confirmations ──────────────────────────────────────────────────
    op.create_table(
        "mandate_confirmations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("practice_area", sa.String(100), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmation_source", sa.String(200), nullable=False),
        sa.Column("evidence_url", sa.Text, nullable=True),
        sa.Column("is_auto_detected", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "reviewed_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_mandate_confirmations_company_pa",
        "mandate_confirmations",
        ["company_id", "practice_area", "confirmed_at"],
    )
    op.create_index(
        "ix_mandate_confirmations_source",
        "mandate_confirmations",
        ["confirmation_source"],
    )

    # ── prediction_accuracy_log ───────────────────────────────────────────────
    op.create_table(
        "prediction_accuracy_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("practice_area", sa.String(100), nullable=False),
        sa.Column("horizon", sa.Integer, nullable=False),  # 30, 60, or 90
        sa.Column("predicted_score", sa.Float, nullable=False),
        sa.Column("threshold_used", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("was_correct", sa.Boolean, nullable=False),
        sa.Column("lead_days", sa.Integer, nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_prediction_accuracy_pa_date",
        "prediction_accuracy_log",
        ["practice_area", "confirmed_at"],
    )
    op.create_index(
        "ix_prediction_accuracy_company",
        "prediction_accuracy_log",
        ["company_id"],
    )
    op.create_index(
        "ix_prediction_accuracy_correct",
        "prediction_accuracy_log",
        ["was_correct", "horizon"],
    )

    # ── model_drift_alerts ────────────────────────────────────────────────────
    op.create_table(
        "model_drift_alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("practice_area", sa.String(100), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accuracy_before", sa.Float, nullable=False),
        sa.Column("accuracy_after", sa.Float, nullable=False),
        sa.Column("delta", sa.Float, nullable=False),  # accuracy_after - accuracy_before
        sa.Column("ks_statistic", sa.Float, nullable=True),
        sa.Column("ks_pvalue", sa.Float, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="open",
        ),  # open / acknowledged / resolved
    )
    op.create_index(
        "ix_model_drift_pa_date",
        "model_drift_alerts",
        ["practice_area", "detected_at"],
    )
    op.create_index(
        "ix_model_drift_status",
        "model_drift_alerts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("model_drift_alerts")
    op.drop_table("prediction_accuracy_log")
    op.drop_table("mandate_confirmations")
