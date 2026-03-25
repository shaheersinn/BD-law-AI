"""0007_phase7_api

Phase 7: Scoring API

New tables:
    - api_request_log:  Per-request logging for scoring API endpoints

Revision ID: 0007_phase7_api
Revises: 0006_phase6_ml
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_phase7_api"
down_revision = "0006_phase6_ml"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── api_request_log ────────────────────────────────────────────────────────
    op.create_table(
        "api_request_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("response_time_ms", sa.Float, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_api_request_log_endpoint", "api_request_log", ["endpoint"])
    op.create_index("ix_api_request_log_created_at", "api_request_log", ["created_at"])
    op.create_index("ix_api_request_log_company_id", "api_request_log", ["company_id"])


def downgrade() -> None:
    op.drop_table("api_request_log")
