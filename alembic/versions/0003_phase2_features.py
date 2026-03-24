"""Phase 2 — company_features table.

Revision ID: 0003_phase2_features
Revises: 0002_phase1_scrapers
Create Date: 2026-03-24
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0003_phase2_features"
down_revision = "0002_phase1_scrapers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_features",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("feature_name", sa.String(100), nullable=False),
        sa.Column("feature_version", sa.String(10), nullable=False,
                  server_default="v1"),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("is_null", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "feature_name", "feature_version", "horizon_days",
            name="uq_company_feature_version_horizon",
        ),
    )
    op.create_index("ix_cf_company_horizon", "company_features",
                    ["company_id", "horizon_days"])
    op.create_index("ix_cf_feature_name", "company_features", ["feature_name"])
    op.create_index("ix_cf_computed_at", "company_features", ["computed_at"])
    op.create_index("ix_cf_is_null", "company_features", ["is_null"])
    op.create_index("ix_cf_category", "company_features", ["category"])

    # Partial index: non-null features only (used by ML training query)
    op.execute(
        "CREATE INDEX ix_cf_nonnull_company_horizon ON company_features "
        "(company_id, horizon_days) WHERE is_null = false"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cf_nonnull_company_horizon")
    op.drop_table("company_features")
