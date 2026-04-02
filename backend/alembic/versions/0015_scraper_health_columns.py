"""Add scraper_health columns for new ORM + companies.is_active.

Revision ID: 0015_scraper_health_columns
Revises: 0013_signals_table
"""

from __future__ import annotations

from alembic import op

revision = "0015_scraper_health_columns"
down_revision = "0013_signals_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE scraper_health
            ADD COLUMN IF NOT EXISTS scraper_name VARCHAR(100),
            ADD COLUMN IF NOT EXISTS scraper_category VARCHAR(50) NOT NULL DEFAULT 'unknown',
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'healthy',
            ADD COLUMN IF NOT EXISTS last_run_duration_ms INTEGER,
            ADD COLUMN IF NOT EXISTS records_last_run INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS records_today INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS records_total INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS records_today_reset_date TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS avg_run_duration_ms DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS p95_run_duration_ms DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS success_rate_7d DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS source_url VARCHAR(2000),
            ADD COLUMN IF NOT EXISTS source_reliability_score DOUBLE PRECISION NOT NULL DEFAULT 0.8,
            ADD COLUMN IF NOT EXISTS requires_api_key INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS api_key_env_var VARCHAR(100),
            ADD COLUMN IF NOT EXISTS diagnostics JSONB
    """)

    op.execute("""
        UPDATE scraper_health
        SET scraper_name = source_id
        WHERE scraper_name IS NULL AND source_id IS NOT NULL
    """)

    op.execute("""
        UPDATE scraper_health
        SET status = CASE
            WHEN COALESCE(is_healthy, true) THEN 'healthy'
            ELSE 'failing'
        END
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_scraper_health_scraper_name
        ON scraper_health (scraper_name)
    """)

    op.execute("""
        ALTER TABLE companies
            ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true
    """)

    op.execute("""
        UPDATE companies SET is_active = (status::text = 'active')
    """)


def downgrade() -> None:
    pass
