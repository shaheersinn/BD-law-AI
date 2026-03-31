"""Phase CA-1: Class action cases table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-31

Stores class action cases detected by the 12 class action scrapers.
Tracks lifecycle: investigation → filed → certified → settled/dismissed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_action_cases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("case_name", sa.String(500), nullable=False),
        sa.Column("case_number", sa.String(100), nullable=True),
        sa.Column(
            "jurisdiction",
            sa.String(50),
            nullable=False,
            comment="ON, BC, QC, AB, FED, US",
        ),
        sa.Column("court", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            comment="investigation|filed|certified|settled|dismissed|appealed",
        ),
        sa.Column(
            "case_type",
            sa.String(100),
            nullable=True,
            comment="securities|product_liability|privacy|employment|environmental|competition|consumer",
        ),
        sa.Column("plaintiff_firm", sa.String(300), nullable=True),
        sa.Column("filing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certification_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_amount_cad", sa.Float(), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_scraper", sa.String(100), nullable=True),
        sa.Column("practice_areas", JSONB(), nullable=True),
        sa.Column("raw_payload", JSONB(), nullable=True),
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
        "ix_class_action_cases_case_type",
        "class_action_cases",
        ["case_type"],
    )
    op.create_index(
        "ix_class_action_cases_filing_date",
        "class_action_cases",
        ["filing_date"],
    )
    op.create_index(
        "ix_class_action_cases_created_at",
        "class_action_cases",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_class_action_cases_created_at")
    op.drop_index("ix_class_action_cases_filing_date")
    op.drop_index("ix_class_action_cases_case_type")
    op.drop_index("ix_class_action_cases_status")
    op.drop_index("ix_class_action_cases_jurisdiction")
    op.drop_table("class_action_cases")
