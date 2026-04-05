"""0017 — Add CHECK constraint to clients.risk_level VARCHAR column.

Column was created as VARCHAR(20) in 0016. This migration adds a CHECK
constraint so PostgreSQL enforces valid values, matching the SQLAlchemy
Enum(native_enum=False) model definition.

Revision ID: 0017_risklevel_constraint
Revises: 0016_missing_tables
Create Date: 2026-04-05
"""
from __future__ import annotations

from alembic import op


revision = "0017_risklevel_constraint"
down_revision = "0016_missing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE clients
            ADD CONSTRAINT IF NOT EXISTS ck_clients_risk_level
            CHECK (risk_level IN ('critical', 'high', 'medium', 'low'))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE clients
            DROP CONSTRAINT IF EXISTS ck_clients_risk_level
    """)
