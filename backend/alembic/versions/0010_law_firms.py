"""0010 — Law firms table for class action matching.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "law_firms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("name_normalized", sa.String(length=300), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("hq_province", sa.String(length=10), nullable=True),
        sa.Column("offices", JSONB, nullable=True),
        sa.Column("practice_strengths", JSONB, nullable=True),
        sa.Column("class_action_track_record", JSONB, nullable=True),
        sa.Column("jurisdictions", JSONB, nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("is_plaintiff_firm", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_defence_firm", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lawyer_count", sa.Integer(), nullable=True),
        sa.Column("class_action_lawyers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_law_firms_name_normalized", "law_firms", ["name_normalized"])
    op.create_unique_constraint("uq_law_firms_name_normalized", "law_firms", ["name_normalized"])
    op.create_index("ix_law_firms_tier", "law_firms", ["tier"])
    op.create_index("ix_law_firms_plaintiff", "law_firms", ["is_plaintiff_firm"])
    op.create_index("ix_law_firms_defence", "law_firms", ["is_defence_firm"])


def downgrade() -> None:
    op.drop_table("law_firms")
