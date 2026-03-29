"""0009 — Class action cases table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_action_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("case_name", sa.String(500), nullable=False),
        sa.Column("case_number", sa.String(100), nullable=True),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("court", sa.String(200), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("case_type", sa.String(100), nullable=True),
        sa.Column("plaintiff_firm", sa.String(300), nullable=True),
        sa.Column("filing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certification_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_amount_cad", sa.Float, nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_scraper", sa.String(100), nullable=True),
        sa.Column("practice_areas", JSONB, nullable=True),
        sa.Column("raw_payload", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_class_action_cases_jurisdiction",
        "class_action_cases",
        ["jurisdiction"],
    )
    op.create_index(
        "ix_class_action_cases_status",
        "class_action_cases",
        ["status"],
    )
    op.create_index(
        "ix_class_action_cases_filing_date",
        "class_action_cases",
        ["filing_date"],
    )
    op.create_index(
        "ix_class_action_cases_case_type",
        "class_action_cases",
        ["case_type"],
    )


def downgrade() -> None:
    op.drop_table("class_action_cases")
