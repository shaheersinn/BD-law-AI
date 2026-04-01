"""0013 — Create signals table (ORM model app.models.signal.Signal).

Revision ID: 0013_signals_table
Revises: 0012_triggers_alerts
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013_signals_table"
down_revision = "0012_triggers_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("scraper_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("signal_type", sa.String(length=100), nullable=False),
        sa.Column("practice_area_flags", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("primary_practice_area", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=1000), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_entity_name", sa.String(length=500), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("signal_strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source_reliability", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("entity_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("entity_resolution_confidence", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_company_id", "signals", ["company_id"], unique=False)
    op.create_index("ix_signals_scraper_name", "signals", ["scraper_name"], unique=False)
    op.create_index("ix_signals_signal_type", "signals", ["signal_type"], unique=False)
    op.create_index(
        "ix_signals_primary_practice_area", "signals", ["primary_practice_area"], unique=False
    )
    op.create_index("ix_signals_raw_entity_name", "signals", ["raw_entity_name"], unique=False)
    op.create_index("ix_signals_content_hash", "signals", ["content_hash"], unique=True)
    op.create_index("ix_signals_published_at", "signals", ["published_at"], unique=False)
    op.create_index("ix_signals_scraped_at", "signals", ["scraped_at"], unique=False)
    op.create_index("ix_signals_entity_resolved", "signals", ["entity_resolved"], unique=False)
    op.create_index(
        "ix_signals_company_type_date",
        "signals",
        ["company_id", "signal_type", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_signals_practice_area",
        "signals",
        ["primary_practice_area", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_signals_unresolved",
        "signals",
        ["entity_resolved", "scraped_at"],
        unique=False,
    )
    op.create_index(
        "ix_signals_scraper_date",
        "signals",
        ["scraper_name", "scraped_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_signals_scraper_date", table_name="signals")
    op.drop_index("ix_signals_unresolved", table_name="signals")
    op.drop_index("ix_signals_practice_area", table_name="signals")
    op.drop_index("ix_signals_company_type_date", table_name="signals")
    op.drop_index("ix_signals_entity_resolved", table_name="signals")
    op.drop_index("ix_signals_scraped_at", table_name="signals")
    op.drop_index("ix_signals_published_at", table_name="signals")
    op.drop_index("ix_signals_content_hash", table_name="signals")
    op.drop_index("ix_signals_raw_entity_name", table_name="signals")
    op.drop_index("ix_signals_primary_practice_area", table_name="signals")
    op.drop_index("ix_signals_signal_type", table_name="signals")
    op.drop_index("ix_signals_scraper_name", table_name="signals")
    op.drop_index("ix_signals_company_id", table_name="signals")
    op.drop_table("signals")
