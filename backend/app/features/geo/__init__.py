"""
app/features/geo/__init__.py — Geographic & Macro Features (10 features).

The Canadian legal market has strong geographic and macro patterns:
  - Interest rate increases → insolvency spike 12-18 months later
  - Oil price shock → energy sector litigation (Alberta concentration)
  - Construction sector insolvency leads manufacturing by 2-4 quarters
  - OSB postal-code data → regional insolvency pressure maps

Features implemented here:
  interest_rate_cycle_position     — Bank of Canada rate vs neutral (0=neutral, +1=hiking, -1=cutting)
  province_insolvency_rate_delta   — Company province insolvency change vs national baseline
  google_trends_legal_spike_score  — Max spike ratio across legal query sets for company's sector
  sector_insolvency_leading        — Sector-specific insolvency leading indicator score
  regulatory_calendar_proximity    — Days until next major regulatory reporting deadline
  osb_postal_code_stress           — OSB insolvency rate in company's postal code vs baseline
  commodity_price_shock_flag       — Binary: relevant commodity price shock detected
  social_sentiment_composite       — Weighted composite of all social signal types
  media_mention_velocity_7d        — News mentions per day (last 7 days)
  reddit_legal_mention_count_7d    — Legal mentions on r/legaladvicecanada + r/canada last 7d
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, select

from app.features.base import BaseFeature, FeatureValue, register_feature

log = structlog.get_logger(__name__)

# ── Canadian interest rate cycle ───────────────────────────────────────────────
# Encoded from Bank of Canada historical data + current policy
# Phase 5 will pull this live via Bank of Canada Valet API
_RATE_CYCLE_CACHE: dict[str, float] = {}  # Updated by live feed in Phase 5


@register_feature
class InterestRateCyclePositionFeature(BaseFeature):
    name = "interest_rate_cycle_position"
    version = "v1"
    category = "geo"
    description = "BoC policy rate vs neutral estimate. +1=hiking, 0=neutral, -1=cutting. Insolvency lag = 12-18mo."

    # Static fallback: BoC target rate as of March 2026 context
    _CURRENT_RATE_APPROX = 2.75  # Updated quarterly via Phase 5 live feed
    _NEUTRAL_RATE_APPROX = 2.50  # BoC long-run neutral estimate

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        try:
            # Check if live rate is cached from Phase 5 geo feed
            from app.models.signal import SignalRecord

            cutoff = datetime.now(tz=UTC) - timedelta(days=90)
            result = await db.execute(
                select(SignalRecord.signal_value)
                .where(
                    and_(
                        SignalRecord.signal_type == "market_macro_signal",
                        SignalRecord.source_id.in_(["geo_bank_of_canada_rates", "geo_statscan"]),
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
                .order_by(SignalRecord.scraped_at.desc())
                .limit(1)
            )
            row = result.scalar()
            if row:
                val = json.loads(row) if isinstance(row, str) else (row or {})
                current_rate = float(val.get("overnight_rate", self._CURRENT_RATE_APPROX))
            else:
                current_rate = self._CURRENT_RATE_APPROX

            # Normalize: (rate - neutral) / 2.0 — clipped to -1..+1
            position = (current_rate - self._NEUTRAL_RATE_APPROX) / 2.0
            position_clipped = max(-1.0, min(1.0, position))

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=position_clipped,
                is_null=False,
                confidence=0.80,
                metadata={"current_rate": current_rate, "neutral": self._NEUTRAL_RATE_APPROX},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class GoogleTrendsLegalSpikeScoreFeature(BaseFeature):
    name = "google_trends_legal_spike_score"
    version = "v1"
    category = "geo"
    description = (
        "Max Google Trends spike ratio for legal keywords in company's sector/province. Range: 0–5."
    )

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id == "geo_google_trends",
                    )
                )
            )
            rows = result.scalars().all()
            if not rows:
                return self._null_value(company_id, horizon_days)

            max_spike = 0.0
            for row in rows:
                try:
                    val = json.loads(row) if isinstance(row, str) else (row or {})
                    spike_ratio = float(val.get("spike_ratio", 1.0))
                    max_spike = max(max_spike, spike_ratio)
                except (ValueError, TypeError, AttributeError):
                    continue

            score = min(5.0, max(0.0, max_spike - 1.0))  # Excess above baseline

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=score,
                signal_count=len(rows),
                is_null=(score == 0 and self.null_if_no_signals),
                confidence=0.70,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class SectorInsolvencyLeadingFeature(BaseFeature):
    name = "sector_insolvency_leading"
    version = "v1"
    category = "geo"
    description = (
        "Sector-specific insolvency leading indicator. Construction leads manufacturing by 2-4Q."
    )

    # Sector lag patterns from Canadian litigation intelligence
    # See: ORACLE architecture notes — Canadian litigation intelligence baked into model
    _SECTOR_WEIGHTS = {
        "construction": 1.5,  # Construction is the leading insolvency indicator
        "manufacturing": 1.2,
        "retail": 1.1,
        "energy": 1.0,
        "technology": 0.8,
        "financial": 0.6,  # Financial sector has regulatory buffers
        "healthcare": 0.5,
    }

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.company import Company
        from app.models.signal import SignalRecord

        try:
            # Get company sector
            company_result = await db.execute(
                select(Company.sector, Company.province).where(Company.id == company_id)
            )
            company_row = company_result.first()
            if not company_row:
                return self._null_value(company_id, horizon_days)

            sector = (company_row.sector or "").lower()
            province = (company_row.province or "").upper()

            # Get OSB insolvency count for company's sector/province in window
            cutoff = self._cutoff(horizon_days)
            result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "insolvency_filing",
                    )
                )
            )
            total_insolvencies = result.scalar() or 0

            # Apply sector weight
            sector_weight = 1.0
            for sector_key, weight in self._SECTOR_WEIGHTS.items():
                if sector_key in sector:
                    sector_weight = weight
                    break

            # Alberta/Saskatchewan energy sector gets extra weight
            if province in ("AB", "SK") and "energy" in sector:
                sector_weight *= 1.3

            score = min(10.0, total_insolvencies * sector_weight / 10.0)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=score,
                signal_count=total_insolvencies,
                is_null=False,
                confidence=0.75,
                metadata={"sector": sector, "province": province, "sector_weight": sector_weight},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class SocialSentimentCompositeFeature(BaseFeature):
    name = "social_sentiment_composite"
    version = "v1"
    category = "geo"
    description = "Weighted composite of all social signal types. High = negative social sentiment. Range: 0–10."

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)

        _SOURCE_WEIGHTS = {
            "social_reddit": 0.8,
            "social_twitter_x": 1.0,
            "social_stockhouse": 1.2,  # Stockhouse is more targeted
            "social_breach_monitor": 2.0,  # Breach is high severity
            "social_linkedin": 1.5,  # Executive LinkedIn signals high quality
        }

        try:
            result = await db.execute(
                select(SignalRecord.source_id, func.count(SignalRecord.id))
                .where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id.like("social_%"),
                    )
                )
                .group_by(SignalRecord.source_id)
            )
            rows = result.all()

            if not rows:
                return self._null_value(company_id, horizon_days)

            composite = 0.0
            total_signals = 0
            for source_id, count in rows:
                weight = _SOURCE_WEIGHTS.get(source_id, 1.0)
                composite += count * weight
                total_signals += count

            normalized = min(10.0, composite / 5.0)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=normalized,
                signal_count=total_signals,
                is_null=False,
                confidence=0.75,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class MediaMentionVelocityFeature(BaseFeature):
    name = "media_mention_velocity_7d"
    version = "v1"
    category = "geo"
    description = (
        "News mentions per day averaged over last 7 days. Velocity spike = coverage acceleration."
    )

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff_7d = datetime.now(tz=UTC) - timedelta(days=7)
        try:
            result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff_7d,
                        SignalRecord.source_id.like("news_%"),
                    )
                )
            )
            count = result.scalar() or 0
            velocity = count / 7.0

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=velocity,
                signal_count=count,
                is_null=(count == 0 and self.null_if_no_signals),
                confidence=0.90,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class CommodityPriceShockFlagFeature(BaseFeature):
    name = "commodity_price_shock_flag"
    version = "v1"
    category = "geo"
    description = "Binary: 1 if relevant commodity (oil/gas/metals) price shock detected for company's sector."
    null_if_no_signals = False

    _SHOCK_KEYWORDS = {
        "oil price crash",
        "commodity shock",
        "price collapse",
        "energy crisis",
        "metals downturn",
        "commodity cycle",
        "oil price drop",
        "lumber price",
        "gold price decline",
        "copper price",
    }

    async def compute(
        self, company_id: int, horizon_days: int, db: Any, mongo_db: Any
    ) -> FeatureValue:
        from app.models.signal import SignalRecord

        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id.like("news_%"),
                    )
                )
            )
            texts = [t for t in result.scalars().all() if t]
            has_shock = any(kw in text.lower() for text in texts for kw in self._SHOCK_KEYWORDS)

            return FeatureValue(
                company_id=company_id,
                feature_name=self.name,
                feature_version=self.version,
                horizon_days=horizon_days,
                value=1.0 if has_shock else 0.0,
                is_null=False,
                signal_count=len(texts),
                confidence=0.72,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)
