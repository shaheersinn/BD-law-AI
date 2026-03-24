"""Phase 1 — companies, company_aliases, signal_records, scraper_health tables.

Revision ID: 0002_phase1_scrapers
Revises: 0001_phase0_users
Create Date: 2026-03-23
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0002_phase1_scrapers"
down_revision = "0001_phase0_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── companies ──────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("name_normalized", sa.String(500), nullable=False),
        sa.Column("sedar_id", sa.String(50), nullable=True),
        sa.Column("cik", sa.String(20), nullable=True),
        sa.Column("lei", sa.String(20), nullable=True),
        sa.Column("business_number", sa.String(20), nullable=True),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("cusip", sa.String(9), nullable=True),
        sa.Column("isin", sa.String(12), nullable=True),
        sa.Column("sic_code", sa.String(10), nullable=True),
        sa.Column("naics_code", sa.String(10), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(200), nullable=True),
        sa.Column("province", sa.String(50), nullable=True),
        sa.Column("country", sa.String(10), nullable=False, server_default="CA"),
        sa.Column("hq_city", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(10), nullable=True),
        sa.Column("domain", sa.String(200), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("market_cap_cad", sa.Float(), nullable=True),
        sa.Column("revenue_cad", sa.Float(), nullable=True),
        sa.Column("fiscal_year_end", sa.String(10), nullable=True),
        sa.Column("status", sa.Enum(
            "active", "inactive", "acquired", "bankrupt", "merged", "private",
            name="companystatus"
        ), nullable=False, server_default="active"),
        sa.Column("is_publicly_listed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_crown_corporation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_foreign_private_issuer", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("priority_tier", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.Column("scrape_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_companies_name_normalized", "companies", ["name_normalized"])
    op.create_index("ix_companies_sedar_id", "companies", ["sedar_id"])
    op.create_index("ix_companies_cik", "companies", ["cik"])
    op.create_index("ix_companies_ticker", "companies", ["ticker"])
    op.create_index("ix_companies_domain", "companies", ["domain"])
    op.create_index("ix_companies_ticker_exchange", "companies", ["ticker", "exchange"])

    # ── company_aliases ────────────────────────────────────────────────────────
    op.create_table(
        "company_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("alias", sa.String(500), nullable=False),
        sa.Column("alias_normalized", sa.String(500), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=False, server_default="name"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_aliases_company_id", "company_aliases", ["company_id"])
    op.create_index("ix_company_aliases_normalized", "company_aliases", ["alias_normalized"])

    # ── signal_records ─────────────────────────────────────────────────────────
    op.create_table(
        "signal_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("signal_type", sa.String(100), nullable=False),
        sa.Column("raw_company_name", sa.String(500), nullable=True),
        sa.Column("raw_company_id", sa.String(100), nullable=True),
        sa.Column("signal_value", sa.Text(), nullable=True),
        sa.Column("signal_text", sa.Text(), nullable=True),
        sa.Column("mongo_doc_id", sa.String(50), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_negative_label", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("ttl_expires_at", sa.DateTime(), nullable=True),
        sa.Column("practice_area_hints", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signal_records_company_id", "signal_records", ["company_id"])
    op.create_index("ix_signal_records_source_id", "signal_records", ["source_id"])
    op.create_index("ix_signal_records_signal_type", "signal_records", ["signal_type"])
    op.create_index("ix_signal_records_is_resolved", "signal_records", ["is_resolved"])
    op.create_index("ix_signal_records_is_processed", "signal_records", ["is_processed"])
    op.create_index("ix_signal_records_published_at", "signal_records", ["published_at"])
    op.create_index("ix_signal_records_scraped_at", "signal_records", ["scraped_at"])
    op.create_index("ix_signal_source_scraped", "signal_records", ["source_id", "scraped_at"])
    op.create_index("ix_signal_company_type", "signal_records", ["company_id", "signal_type"])

    # ── scraper_health ─────────────────────────────────────────────────────────
    op.create_table(
        "scraper_health",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_records_scraped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_records_per_run", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p95_duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_healthy", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_rate_limited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("circuit_breaker_state", sa.String(20), nullable=False, server_default="closed"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_scraper_health_source", "scraper_health", ["source_id"])


def downgrade() -> None:
    op.drop_table("scraper_health")
    op.drop_table("signal_records")
    op.drop_table("company_aliases")
    op.drop_table("companies")
    op.execute("DROP TYPE IF EXISTS companystatus")
