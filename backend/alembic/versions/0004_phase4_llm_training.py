"""Phase 4 — LLM Training: training_datasets table.

Revision ID: 0004_phase4_llm_training
Revises: 0003_phase3_ground_truth
Create Date: 2026-03-24

Creates:
  - training_datasets: tracks each Agent 019 (Training Data Curator) export run
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers
revision = "0004_phase4_llm_training"
down_revision = "0003_phase3_ground_truth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("label_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("positive_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("negative_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uncertain_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("practice_areas", ARRAY(sa.Text()), nullable=True),
        sa.Column("horizons", ARRAY(sa.Integer()), nullable=True),
        sa.Column("min_confidence", sa.Float(), nullable=False, server_default="0.70"),
        sa.Column("export_path", sa.Text(), nullable=True),
        sa.Column("export_format", sa.String(length=10), nullable=False, server_default="parquet"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_td_status", "training_datasets", ["status"])
    op.create_index("ix_td_created_at", "training_datasets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_td_created_at", table_name="training_datasets")
    op.drop_index("ix_td_status", table_name="training_datasets")
    op.drop_table("training_datasets")
