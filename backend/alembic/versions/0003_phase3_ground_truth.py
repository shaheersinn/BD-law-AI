"""Phase 3 — ground_truth_labels and labeling_runs tables.

Revision ID: 0003_phase3_ground_truth
Revises: 0002_phase1_scrapers
Create Date: 2026-03-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_phase3_ground_truth"
down_revision = "0002_phase1_scrapers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── labeling_runs ───────────────────────────────────────────────────────────
    op.create_table(
        "labeling_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="running",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("companies_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "positive_labels_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "negative_labels_created",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labeling_runs_status", "labeling_runs", ["status"])
    op.create_index("ix_labeling_runs_run_type", "labeling_runs", ["run_type"])

    # ── ground_truth_labels ─────────────────────────────────────────────────────
    op.create_table(
        "ground_truth_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("labeling_run_id", sa.Integer(), nullable=True),
        sa.Column("label_type", sa.String(20), nullable=False),
        sa.Column("practice_area", sa.String(100), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("signal_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_signal_ids", sa.ARRAY(sa.Integer()), nullable=True),
        sa.Column("evidence_mongo_ids", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("label_source", sa.String(50), nullable=False, server_default="retrospective"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("is_validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validated_by", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["labeling_run_id"], ["labeling_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["validated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "practice_area",
            "horizon_days",
            "signal_window_start",
            name="uq_label_company_pa_horizon_window",
        ),
    )
    op.create_index(
        "ix_gtl_company_id", "ground_truth_labels", ["company_id"]
    )
    op.create_index(
        "ix_gtl_label_type", "ground_truth_labels", ["label_type"]
    )
    op.create_index(
        "ix_gtl_practice_area", "ground_truth_labels", ["practice_area"]
    )
    op.create_index(
        "ix_gtl_horizon_days", "ground_truth_labels", ["horizon_days"]
    )
    op.create_index(
        "ix_gtl_labeling_run_id", "ground_truth_labels", ["labeling_run_id"]
    )
    op.create_index(
        "ix_gtl_company_label",
        "ground_truth_labels",
        ["company_id", "label_type"],
    )


def downgrade() -> None:
    op.drop_table("ground_truth_labels")
    op.drop_table("labeling_runs")
