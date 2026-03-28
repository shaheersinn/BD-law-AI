"""
app/features/base.py — Feature Engineering Base Classes & Registry.

Architecture:
  Every feature is a named, versioned, typed computation on a (company_id, window)
  pair. Features are computed from signal_records (PostgreSQL) and stored in
  company_features (PostgreSQL). MongoDB raw signals are READ for NLP features
  but never written to.

Feature categories (60+ features total):
  ── NLP Features (12)
     md&a_sentiment_delta, hedging_score, legal_language_density,
     regulatory_mention_count, litigation_keyword_count,
     blog_consensus_score, blog_practice_dominance,
     executive_departure_mentions, financial_distress_language_score,
     disclosure_tone_shift, forward_guidance_negativity, earnings_surprise_text_signal

  ── Corporate Filing Features (10)
     material_change_count_30d, material_change_count_90d,
     insider_sell_ratio, insider_net_transaction_cad,
     filing_velocity_change, auditor_change_flag,
     related_party_transaction_count, going_concern_flag,
     restatement_flag, regulatory_filing_lag_days

  ── Market Features (10)
     price_momentum_30d, price_momentum_90d,
     volume_anomaly_zscore, short_interest_pct,
     options_put_call_ratio, market_cap_change_pct_90d,
     bid_ask_spread_trend, analyst_downgrade_count_30d,
     credit_rating_change_flag, cross_listed_sec_flag

  ── Social & Sentiment Features (8)
     reddit_legal_mention_count_7d, reddit_distress_score_7d,
     twitter_legal_velocity_7d, stockhouse_bear_ratio_7d,
     breach_detected_flag, executive_linkedin_departure_flag,
     social_sentiment_composite, media_mention_velocity_7d

  ── Geographic & Macro Features (10)
     province_insolvency_rate_delta, regional_court_volume_delta,
     google_trends_legal_spike_score, interest_rate_cycle_position,
     sector_insolvency_leading_indicator, osb_postal_code_stress,
     commodity_price_shock_flag, gdp_growth_rate_sector,
     unemployment_rate_sector, regulatory_calendar_proximity_score

  ── Temporal & Velocity Features (8)
     signal_velocity_7d, signal_velocity_30d,
     signal_acceleration, signal_decay_adjusted_score,
     days_since_last_filing, days_since_last_regulatory_action,
     cross_signal_confirmation_count, signal_co_occurrence_score

  ── Corporate Graph Features (4)
     director_interlocks_score, board_distress_contagion,
     subsidiary_signal_count, related_entity_signal_propagation

Feature versioning:
  All features are versioned (v1, v2...). When a feature's computation
  changes, a new version is created. Old versions kept for model comparison.

Feature store:
  company_features table in PostgreSQL.
  One row per (company_id, feature_name, feature_version, computed_at, horizon).
  horizon: 30 | 60 | 90 (days) — same feature computed for each time window.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

log = structlog.get_logger(__name__)

VALID_HORIZONS = (30, 60, 90)


@dataclass
class FeatureValue:
    """Single computed feature value for one company × horizon."""
    company_id: int
    feature_name: str
    feature_version: str        # e.g. "v1"
    horizon_days: int           # 30 | 60 | 90
    value: float                # All features are float (0.0 for binary flags)
    is_null: bool = False       # True if insufficient data to compute
    confidence: float = 1.0     # 0–1 confidence in this value
    computed_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC)
    )
    signal_count: int = 0       # How many signals contributed to this value
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.horizon_days not in VALID_HORIZONS:
            raise ValueError(f"horizon_days must be one of {VALID_HORIZONS}")

    @property
    def feature_key(self) -> str:
        return f"{self.feature_name}:{self.feature_version}:{self.horizon_days}d"


class BaseFeature(ABC):
    """
    Abstract base class for all ORACLE feature computers.

    Subclasses implement compute() for one company × one horizon.
    The feature runner fans out across companies and horizons.
    """
    name: str           # e.g. "material_change_count"
    version: str = "v1"
    category: str       # "nlp" | "corporate" | "market" | "social" | "geo" | "temporal" | "graph"
    description: str = ""
    requires_mongo: bool = False    # True if this feature reads MongoDB
    requires_market: bool = False   # True if this feature needs market data
    null_if_no_signals: bool = True # Return is_null=True rather than 0 if no data

    @abstractmethod
    async def compute(
        self,
        company_id: int,
        horizon_days: int,
        db: Any,            # AsyncSession
        mongo_db: Any,      # MongoDB handle (may be None)
    ) -> FeatureValue:
        """
        Compute this feature for one company over one horizon window.
        Must return a FeatureValue — never raise, return is_null=True if no data.
        """
        ...

    async def compute_all_horizons(
        self,
        company_id: int,
        db: Any,
        mongo_db: Any,
    ) -> list[FeatureValue]:
        """Compute feature across all 3 horizons. Returns list of 3 FeatureValues."""
        results = []
        for horizon in VALID_HORIZONS:
            try:
                fv = await self.compute(company_id, horizon, db, mongo_db)
                results.append(fv)
            except Exception as exc:
                log.error("feature_compute_error",
                          feature=self.name, company_id=company_id,
                          horizon=horizon, error=str(exc))
                results.append(FeatureValue(
                    company_id=company_id,
                    feature_name=self.name,
                    feature_version=self.version,
                    horizon_days=horizon,
                    value=0.0,
                    is_null=True,
                    confidence=0.0,
                ))
        return results

    def _cutoff(self, horizon_days: int) -> datetime:
        return datetime.now(tz=UTC) - timedelta(days=horizon_days)

    def _null_value(self, company_id: int, horizon_days: int) -> FeatureValue:
        return FeatureValue(
            company_id=company_id,
            feature_name=self.name,
            feature_version=self.version,
            horizon_days=horizon_days,
            value=0.0,
            is_null=True,
            confidence=0.0,
        )


# ── Feature Registry ───────────────────────────────────────────────────────────
_FEATURE_REGISTRY: dict[str, type[BaseFeature]] = {}


def register_feature(cls: type[BaseFeature]) -> type[BaseFeature]:
    """Decorator: @register_feature registers a feature class."""
    key = f"{cls.name}:{cls.version}"
    if key in _FEATURE_REGISTRY:
        raise ValueError(f"Feature already registered: {key}")
    _FEATURE_REGISTRY[key] = cls
    return cls


class FeatureRegistry:
    @classmethod
    def all(cls) -> list[BaseFeature]:
        return [klass() for klass in _FEATURE_REGISTRY.values()]

    @classmethod
    def by_category(cls, category: str) -> list[BaseFeature]:
        return [klass() for klass in _FEATURE_REGISTRY.values()
                if klass.category == category]

    @classmethod
    def count(cls) -> int:
        return len(_FEATURE_REGISTRY)

    @classmethod
    def names(cls) -> list[str]:
        return sorted(f"{k.name}:{k.version}" for k in _FEATURE_REGISTRY.values())
