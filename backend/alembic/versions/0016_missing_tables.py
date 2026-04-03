"""0016 — Create 19 missing tables (clients, geo, BD, partners, features).

Revision ID: 0016_missing_tables
Revises: 0015_scraper_health_columns
Create Date: 2026-04-03
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op


revision = "0016_missing_tables"
down_revision = "0015_scraper_health_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # 1. partners (no FKs to missing tables)
    if "partners" not in existing:
        op.create_table(
            "partners",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("title", sa.String(200), nullable=True),
            sa.Column("email", sa.String(200), nullable=True),
            sa.Column("slack_id", sa.String(50), nullable=True),
            sa.Column("practice_areas", JSONB, nullable=False, server_default="[]"),
            sa.Column("target_industries", JSONB, nullable=False, server_default="[]"),
            sa.Column("firm_name", sa.String(200), nullable=False,
                      server_default="Halcyon Legal Partners LLP"),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 2. clients
    if "clients" not in existing:
        op.create_table(
            "clients",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("name", sa.String(200), nullable=False, index=True),
            sa.Column("industry", sa.String(100), nullable=False),
            sa.Column("region", sa.String(100), nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("partner_name", sa.String(100), nullable=True),
            sa.Column("gc_name", sa.String(200), nullable=True),
            sa.Column("gc_email", sa.String(200), nullable=True),
            sa.Column("gc_linkedin", sa.String(400), nullable=True),
            sa.Column("practice_groups", ARRAY(sa.String), nullable=True,
                      server_default="{}"),
            sa.Column("churn_score", sa.Integer, nullable=False, server_default="0"),
            sa.Column("churn_score_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
            sa.Column("estimated_annual_spend", sa.Numeric(15, 2), nullable=True),
            sa.Column("annual_revenue", sa.Numeric(15, 2), nullable=True),
            sa.Column("wallet_share_pct", sa.Integer, nullable=True),
            sa.Column("days_since_last_contact", sa.Integer, nullable=False,
                      server_default="0"),
            sa.Column("days_since_last_matter", sa.Integer, nullable=False,
                      server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 3. prospects
    if "prospects" not in existing:
        op.create_table(
            "prospects",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("name", sa.String(200), nullable=False, index=True),
            sa.Column("industry", sa.String(100), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("predicted_need", sa.String(200), nullable=True),
            sa.Column("legal_urgency_score", sa.Integer, nullable=False,
                      server_default="0"),
            sa.Column("company_id", sa.Integer, nullable=True, index=True),
            sa.Column("added_by", sa.Integer, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 4. matters (FK to clients)
    if "matters" not in existing:
        op.create_table(
            "matters",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("client_id", sa.Integer,
                      sa.ForeignKey("clients.id"), nullable=False, index=True),
            sa.Column("matter_number", sa.String(50), unique=True, nullable=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("practice_area", sa.String(100), nullable=True),
            sa.Column("lead_partner", sa.String(100), nullable=True),
            sa.Column("opened_at", sa.Date, nullable=True),
            sa.Column("closed_at", sa.Date, nullable=True),
            sa.Column("is_open", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("total_billed", sa.Numeric(15, 2), nullable=False,
                      server_default="0"),
            sa.Column("referral_source", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 5. billing_records (FK to clients, matters)
    if "billing_records" not in existing:
        op.create_table(
            "billing_records",
            sa.Column("id", sa.BigInteger, primary_key=True, index=True),
            sa.Column("client_id", sa.Integer,
                      sa.ForeignKey("clients.id"), nullable=False, index=True),
            sa.Column("matter_id", sa.Integer,
                      sa.ForeignKey("matters.id"), nullable=True, index=True),
            sa.Column("bill_date", sa.Date, nullable=False, index=True),
            sa.Column("amount_billed", sa.Numeric(15, 2), nullable=False),
            sa.Column("amount_collected", sa.Numeric(15, 2), nullable=False,
                      server_default="0"),
            sa.Column("write_off_amount", sa.Numeric(15, 2), nullable=False,
                      server_default="0"),
            sa.Column("has_dispute", sa.Boolean, nullable=False,
                      server_default="false"),
        )

    # 6. churn_signals (FK to clients)
    if "churn_signals" not in existing:
        op.create_table(
            "churn_signals",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("client_id", sa.Integer,
                      sa.ForeignKey("clients.id"), nullable=False, index=True),
            sa.Column("signal_text", sa.Text, nullable=False),
            sa.Column("severity", sa.String(20), nullable=False,
                      server_default="medium"),
            sa.Column("detected_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 7. bd_activities (FK to partners, optional FK to matters)
    if "bd_activities" not in existing:
        op.create_table(
            "bd_activities",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("partner_id", sa.Integer,
                      sa.ForeignKey("partners.id"), nullable=False, index=True),
            sa.Column("activity_type", sa.String(50), nullable=False),
            sa.Column("contact_name", sa.String(200), nullable=True),
            sa.Column("company_name", sa.String(200), nullable=True),
            sa.Column("contact_type", sa.String(50), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("matter_id", sa.Integer,
                      sa.ForeignKey("matters.id"), nullable=True),
            sa.Column("had_followup_within_48h", sa.Boolean, nullable=True),
            sa.Column("led_to_matter", sa.Boolean, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
        )

    # 8. matter_sources (FK to matters)
    if "matter_sources" not in existing:
        op.create_table(
            "matter_sources",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("matter_id", sa.Integer,
                      sa.ForeignKey("matters.id"), nullable=False, unique=True),
            sa.Column("source_type", sa.String(50), nullable=False),
            sa.Column("source_name", sa.String(200), nullable=True),
            sa.Column("source_firm", sa.String(200), nullable=True),
            sa.Column("first_touch", sa.DateTime(timezone=True), nullable=True),
            sa.Column("days_to_close", sa.Integer, nullable=True),
        )

    # 9. referral_contacts (FK to partners)
    if "referral_contacts" not in existing:
        op.create_table(
            "referral_contacts",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("partner_id", sa.Integer,
                      sa.ForeignKey("partners.id"), nullable=False, index=True),
            sa.Column("contact_name", sa.String(200), nullable=False),
            sa.Column("firm_name", sa.String(200), nullable=True),
            sa.Column("contact_type", sa.String(50), nullable=False,
                      server_default="accountant"),
            sa.Column("last_contact", sa.DateTime(timezone=True), nullable=True),
            sa.Column("matters_sent", sa.Integer, nullable=False, server_default="0"),
            sa.Column("revenue_sent", sa.Numeric(15, 2), nullable=False,
                      server_default="0"),
        )

    # 10. content_pieces (FK to partners)
    if "content_pieces" not in existing:
        op.create_table(
            "content_pieces",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("partner_id", sa.Integer,
                      sa.ForeignKey("partners.id"), nullable=False, index=True),
            sa.Column("title", sa.Text, nullable=False),
            sa.Column("content_type", sa.String(50), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("topic", sa.String(300), nullable=True),
            sa.Column("views", sa.Integer, nullable=False, server_default="0"),
            sa.Column("engagements", sa.Integer, nullable=False, server_default="0"),
            sa.Column("inquiries_attributed", sa.Integer, nullable=False,
                      server_default="0"),
            sa.Column("body_text", sa.Text, nullable=True),
        )

    # 11. writing_samples (FK to partners)
    if "writing_samples" not in existing:
        op.create_table(
            "writing_samples",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("partner_id", sa.Integer,
                      sa.ForeignKey("partners.id"), nullable=False, index=True),
            sa.Column("text", sa.Text, nullable=False),
            sa.Column("content_type", sa.String(50), nullable=False,
                      server_default="linkedin_post"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 12. client_inquiries (FK to partners)
    if "client_inquiries" not in existing:
        op.create_table(
            "client_inquiries",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("partner_id", sa.Integer,
                      sa.ForeignKey("partners.id"), nullable=False, index=True),
            sa.Column("inquiry_date", sa.Date, nullable=False),
            sa.Column("company_name", sa.String(200), nullable=False),
            sa.Column("industry", sa.String(100), nullable=True),
            sa.Column("source", sa.String(50), nullable=False, server_default="cold"),
            sa.Column("attributed_content_ids", JSONB, nullable=False,
                      server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 13. alumni (no FKs to missing tables)
    if "alumni" not in existing:
        op.create_table(
            "alumni",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("current_role", sa.String(200), nullable=False),
            sa.Column("current_company", sa.String(200), nullable=False, index=True),
            sa.Column("departure_year", sa.Integer, nullable=True),
            sa.Column("mentor_partner", sa.String(100), nullable=True),
            sa.Column("warmth_score", sa.Integer, nullable=False, server_default="50"),
            sa.Column("linkedin_url", sa.String(400), nullable=True),
            sa.Column("has_active_trigger", sa.Boolean, nullable=False,
                      server_default="false"),
            sa.Column("trigger_description", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 14. jet_tracks (String company field — no FK)
    if "jet_tracks" not in existing:
        op.create_table(
            "jet_tracks",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("company", sa.String(200), nullable=False, index=True),
            sa.Column("tail_number", sa.String(20), nullable=True),
            sa.Column("executive", sa.String(200), nullable=True),
            sa.Column("origin_icao", sa.String(10), nullable=True),
            sa.Column("origin_name", sa.String(200), nullable=True),
            sa.Column("dest_icao", sa.String(10), nullable=True),
            sa.Column("dest_name", sa.String(200), nullable=True),
            sa.Column("departed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("confidence", sa.Integer, nullable=False, server_default="0"),
            sa.Column("is_flagged", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("signal_text", sa.Text, nullable=True),
            sa.Column("predicted_mandate", sa.String(100), nullable=True),
            sa.Column("relationship_warmth", sa.Integer, nullable=False,
                      server_default="50"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 15. foot_traffic_events
    if "foot_traffic_events" not in existing:
        op.create_table(
            "foot_traffic_events",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("target_company", sa.String(200), nullable=False, index=True),
            sa.Column("location_name", sa.String(300), nullable=True),
            sa.Column("device_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("avg_duration_minutes", sa.Integer, nullable=True),
            sa.Column("severity", sa.String(20), nullable=False,
                      server_default="medium"),
            sa.Column("threat_assessment", sa.Text, nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 16. satellite_signals
    if "satellite_signals" not in existing:
        op.create_table(
            "satellite_signals",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("company", sa.String(200), nullable=False, index=True),
            sa.Column("location", sa.String(300), nullable=True),
            sa.Column("observation", sa.Text, nullable=True),
            sa.Column("legal_inference", sa.Text, nullable=True),
            sa.Column("signal_type", sa.String(100), nullable=True),
            sa.Column("confidence", sa.Integer, nullable=False, server_default="0"),
            sa.Column("urgency", sa.String(20), nullable=False,
                      server_default="medium"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 17. permit_filings
    if "permit_filings" not in existing:
        op.create_table(
            "permit_filings",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("company", sa.String(200), nullable=False, index=True),
            sa.Column("permit_type", sa.String(100), nullable=True),
            sa.Column("location", sa.String(300), nullable=True),
            sa.Column("filed_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
            sa.Column("project_type", sa.String(200), nullable=True),
            sa.Column("legal_work_triggered", ARRAY(sa.String), nullable=True),
            sa.Column("estimated_fee", sa.String(50), nullable=True),
            sa.Column("urgency", sa.String(20), nullable=False,
                      server_default="medium"),
            sa.Column("lead_partner", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now()),
        )

    # 18. class_action_scores (FK to companies — already exists)
    if "class_action_scores" not in existing:
        op.create_table(
            "class_action_scores",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("company_id", sa.Integer,
                      sa.ForeignKey("companies.id"), unique=True),
            sa.Column("probability", sa.Float, nullable=False),
            sa.Column("predicted_type", sa.String(100), nullable=True),
            sa.Column("time_horizon_days", sa.Integer, nullable=True),
            sa.Column("contributing_signals", JSONB, nullable=True),
            sa.Column("confidence", sa.Float, nullable=True),
            sa.Column("scored_at", sa.DateTime, server_default=sa.func.now()),
        )

    # 19. company_features (FK to companies — already exists)
    if "company_features" not in existing:
        op.create_table(
            "company_features",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("company_id", sa.Integer,
                      sa.ForeignKey("companies.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("feature_name", sa.String(100), nullable=False),
            sa.Column("feature_version", sa.String(20), nullable=False,
                      server_default="v1"),
            sa.Column("horizon_days", sa.Integer, nullable=False),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("value", sa.Float, nullable=True),
            sa.Column("is_null", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("confidence", sa.Float, nullable=True),
            sa.Column("signal_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column("metadata", sa.Text, nullable=True),
            sa.UniqueConstraint(
                "company_id", "feature_name", "feature_version", "horizon_days",
                name="uq_company_feature_version_horizon",
            ),
            sa.Index(
                "ix_company_feature_lookup",
                "company_id", "horizon_days", "feature_version",
            ),
        )


def downgrade() -> None:
    for table in [
        "company_features", "class_action_scores", "permit_filings",
        "satellite_signals", "foot_traffic_events", "jet_tracks", "alumni",
        "client_inquiries", "writing_samples", "content_pieces",
        "referral_contacts", "matter_sources", "bd_activities", "churn_signals",
        "billing_records", "matters", "prospects", "clients", "partners",
    ]:
        op.drop_table(table, if_exists=True)
