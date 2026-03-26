"""Phase 5 — Live feed event tracking table.

Revision ID: 0005_phase5_live_feeds
Revises: 0004_phase4_llm_training
Create Date: 2026-03-26

Creates:
    - live_feed_events: Tracks events published to Redis Streams
      Used by Phase 5 live feed pipeline for deduplication and auditing.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_phase5_live_feeds"
down_revision = "0004_phase4_llm_training"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "live_feed_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Redis stream name this event was published to
        sa.Column("stream_name", sa.String(100), nullable=False),
        # Event type: signal_ingested | company_updated | scraper_completed | score_triggered
        sa.Column("event_type", sa.String(50), nullable=False),
        # Company this event relates to (nullable — some events are system-level)
        sa.Column("company_id", sa.Integer(), nullable=True),
        # Raw event payload
        sa.Column("payload", JSONB, nullable=True),
        # When the event was consumed and processed by a worker
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        # Deduplication key — prevents reprocessing the same event
        sa.Column("dedup_key", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_live_feed_events_stream_name",
        "live_feed_events",
        ["stream_name"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_events_company_id",
        "live_feed_events",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_events_event_type",
        "live_feed_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_events_dedup_key",
        "live_feed_events",
        ["dedup_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_live_feed_events_dedup_key", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_event_type", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_company_id", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_stream_name", table_name="live_feed_events")
    op.drop_table("live_feed_events")
