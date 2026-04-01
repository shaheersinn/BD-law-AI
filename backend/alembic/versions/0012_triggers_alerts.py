"""0012 — triggers + alerts tables (ORM models existed without migration).

Revision ID: 0012_triggers_alerts
Revises: 0011_phase12_optimization
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_triggers_alerts"
down_revision = "0011_phase12_optimization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "triggers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("trigger_type", sa.String(length=100), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("practice_area", sa.String(length=100), nullable=True),
        sa.Column("practice_confidence", sa.Integer(), nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("confirmed", sa.Boolean(), nullable=True),
        sa.Column("dismissed", sa.Boolean(), nullable=True),
        sa.Column("matter_opened", sa.Boolean(), nullable=True),
        sa.Column("actioned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("actioned_by", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_triggers_source", "triggers", ["source"])
    op.create_index("ix_triggers_company_name", "triggers", ["company_name"])
    op.create_index("ix_triggers_client_id", "triggers", ["client_id"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=True),
        sa.Column("dismissed", sa.Boolean(), nullable=True),
        sa.Column("matter_opened", sa.Boolean(), nullable=True),
        sa.Column("mandate_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_client_id", "alerts", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_client_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_triggers_client_id", table_name="triggers")
    op.drop_index("ix_triggers_company_name", table_name="triggers")
    op.drop_index("ix_triggers_source", table_name="triggers")
    op.drop_table("triggers")
