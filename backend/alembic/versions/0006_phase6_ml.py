"""0006_phase6_ml

Phase 6: ML Training + 10 Enhancements

New tables:
    - model_registry:           Which model is active per practice area
    - scoring_results:          34×3 mandate probability matrix per company per day
    - signal_rules:             Co-occurrence Apriori rules
    - sector_signal_weights:    Per-sector signal multipliers
    - scoring_explanations:     SHAP counterfactuals per high-scoring company
    - signal_decay_config:      Temporal decay lambda per signal type
    - active_learning_queue:    Companies flagged for priority signal collection

Revision ID: 0006_phase6_ml
Revises: 0005_phase3_ground_truth (or latest completed migration)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0006_phase6_ml"
down_revision = "0005_phase5_live_feeds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── model_registry ─────────────────────────────────────────────────────────
    op.create_table(
        "model_registry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("practice_area", sa.String(64), nullable=False, unique=True),
        sa.Column("active_model", sa.String(32), nullable=False),       # "bayesian" | "transformer"
        sa.Column("bayesian_f1", sa.Float, nullable=False, default=0.0),
        sa.Column("transformer_f1", sa.Float, nullable=False, default=0.0),
        sa.Column("bayesian_version", sa.String(256), nullable=True),
        sa.Column("transformer_version", sa.String(256), nullable=True),
        sa.Column("n_train", sa.Integer, nullable=True),
        sa.Column("n_holdout", sa.Integer, nullable=True),
        sa.Column("scale_pos_weight", sa.Float, nullable=True),
        sa.Column("top_features", sa.JSON, nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    op.create_index("ix_model_registry_practice_area", "model_registry", ["practice_area"])

    # ── scoring_results ────────────────────────────────────────────────────────
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("scores", sa.JSON, nullable=False),        # {pa: {30d: f, 60d: f, 90d: f}}
        sa.Column("velocity_score", sa.Float, nullable=True),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("confidence_low", sa.Float, nullable=True),
        sa.Column("confidence_high", sa.Float, nullable=True),
        sa.Column("model_versions", sa.JSON, nullable=True),  # {pa: "bayesian_v3"}
        sa.Column("top_signals", sa.JSON, nullable=True),
        sa.Column("feature_snapshot", sa.JSON, nullable=True),  # snapshot for debugging
    )
    op.create_index("ix_scoring_results_company_id", "scoring_results", ["company_id"])
    op.create_index("ix_scoring_results_scored_at", "scoring_results", ["scored_at"])
    op.create_index(
        "ix_scoring_results_company_date",
        "scoring_results",
        ["company_id", "scored_at"],
        unique=False,
    )

    # ── signal_rules (Apriori co-occurrence) ──────────────────────────────────
    op.create_table(
        "signal_rules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("practice_area", sa.String(64), nullable=False),
        sa.Column("antecedent_signals", sa.JSON, nullable=False),   # [signal_type, ...]
        sa.Column("consequent_signals", sa.JSON, nullable=True),
        sa.Column("support", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("lift", sa.Float, nullable=False),
        sa.Column("n_transactions", sa.Integer, nullable=True),
        sa.Column("mined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
    )
    op.create_index("ix_signal_rules_practice_area", "signal_rules", ["practice_area"])
    op.create_index("ix_signal_rules_lift", "signal_rules", ["lift"])

    # ── sector_signal_weights ─────────────────────────────────────────────────
    op.create_table(
        "sector_signal_weights",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sector", sa.String(64), nullable=False),
        sa.Column("signal_type", sa.String(128), nullable=False),
        sa.Column("weight_multiplier", sa.Float, nullable=False, default=1.0),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("n_samples", sa.Integer, nullable=True),
        sa.UniqueConstraint("sector", "signal_type", name="uq_sector_signal"),
    )
    op.create_index("ix_sector_signal_weights_sector", "sector_signal_weights", ["sector"])

    # ── scoring_explanations (SHAP counterfactuals) ────────────────────────────
    op.create_table(
        "scoring_explanations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("scoring_result_id", sa.BigInteger,
                  sa.ForeignKey("scoring_results.id", ondelete="CASCADE"), nullable=True),
        sa.Column("practice_area", sa.String(64), nullable=False),
        sa.Column("horizon", sa.Integer, nullable=False),          # 30, 60, or 90
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("top_shap_features", sa.JSON, nullable=False),   # [{feature, shap_value, feature_value}]
        sa.Column("counterfactuals", sa.JSON, nullable=False),     # [{feature, direction, reduction}]
        sa.Column("base_value", sa.Float, nullable=True),
        sa.Column("explained_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scoring_explanations_company", "scoring_explanations", ["company_id"])

    # ── signal_decay_config ───────────────────────────────────────────────────
    op.create_table(
        "signal_decay_config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("signal_type", sa.String(128), nullable=False),
        sa.Column("practice_area", sa.String(64), nullable=False, default="global"),
        sa.Column("lambda_value", sa.Float, nullable=False),
        sa.Column("half_life_days", sa.Float, nullable=False),
        sa.Column("calibrated", sa.Boolean, nullable=False, default=False),
        sa.Column("source", sa.String(64), nullable=True),         # "default_prior" | "calibrated"
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("signal_type", "practice_area", name="uq_decay_signal_pa"),
    )
    op.create_index("ix_signal_decay_signal_type", "signal_decay_config", ["signal_type"])

    # ── active_learning_queue ─────────────────────────────────────────────────
    op.create_table(
        "active_learning_queue",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("practice_area", sa.String(64), nullable=False),
        sa.Column("priority_score", sa.Float, nullable=False),      # uncertainty ∈ [0, 1]
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        # pending → scraping → resolved
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_active_learning_queue_company", "active_learning_queue", ["company_id"])
    op.create_index("ix_active_learning_queue_status", "active_learning_queue", ["status"])
    op.create_index(
        "ix_active_learning_queue_priority",
        "active_learning_queue",
        ["status", "priority_score"],
    )


def downgrade() -> None:
    op.drop_table("active_learning_queue")
    op.drop_table("signal_decay_config")
    op.drop_table("scoring_explanations")
    op.drop_table("sector_signal_weights")
    op.drop_table("signal_rules")
    op.drop_table("scoring_results")
    op.drop_table("model_registry")
