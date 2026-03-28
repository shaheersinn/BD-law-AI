"""
app/features/temporal/__init__.py — Temporal & Velocity Features (8 features).
app/features/market/__init__.py — Market Features (6 features).

Temporal: how signals change over time — the rate of change matters as much
as the count. A sudden spike in signals is more predictive than a steady level.

Market: price/options signals that precede legal mandates.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import and_, func, select

from app.features.base import BaseFeature, FeatureValue, register_feature

log = structlog.get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TEMPORAL FEATURES
# ══════════════════════════════════════════════════════════════════════════════

@register_feature
class SignalVelocity7dFeature(BaseFeature):
    name = "signal_velocity_7d"
    version = "v1"
    category = "temporal"
    description = "Signals received in last 7 days / 7. Rate per day. Absolute count."

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff_7d = datetime.now(tz=UTC) - timedelta(days=7)
        cutoff_horizon = self._cutoff(horizon_days)
        # Use 7d regardless of horizon — velocity is always the last 7 days
        try:
            result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff_7d,
                    )
                )
            )
            count_7d = result.scalar() or 0
            velocity = count_7d / 7.0

            # Also get horizon window count for context
            result2 = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff_horizon,
                    )
                )
            )
            count_horizon = result2.scalar() or 0

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=velocity, signal_count=count_7d,
                is_null=(count_7d == 0 and self.null_if_no_signals),
                confidence=0.95,
                metadata={"count_7d": count_7d, f"count_{horizon_days}d": count_horizon},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class SignalAccelerationFeature(BaseFeature):
    name = "signal_acceleration"
    version = "v1"
    category = "temporal"
    description = "Rate of change in signal velocity: (last 7d rate) - (prior 7d rate). Positive = accelerating."

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        now = datetime.now(tz=UTC)
        cutoff_recent = now - timedelta(days=7)
        cutoff_prior = now - timedelta(days=14)

        try:
            async def _count(start: datetime, end: datetime) -> int:
                r = await db.execute(
                    select(func.count(SignalRecord.id)).where(
                        and_(
                            SignalRecord.company_id == company_id,
                            SignalRecord.scraped_at >= start,
                            SignalRecord.scraped_at < end,
                        )
                    )
                )
                return r.scalar() or 0

            recent = await _count(cutoff_recent, now)
            prior = await _count(cutoff_prior, cutoff_recent)

            if recent == 0 and prior == 0:
                return self._null_value(company_id, horizon_days)

            acceleration = (recent - prior) / 7.0  # signals/day change

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=acceleration, signal_count=recent + prior,
                is_null=False, confidence=0.85,
                metadata={"recent_7d": recent, "prior_7d": prior},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class CrossSignalConfirmationCountFeature(BaseFeature):
    name = "cross_signal_confirmation_count"
    version = "v1"
    category = "temporal"
    description = "Number of distinct source categories with signals in window. Range: 0–9."
    null_if_no_signals = False

    _CATEGORIES = [
        "corporate_", "legal_", "regulatory_", "jobs_",
        "market_", "news_", "social_", "geo_", "lawblog_",
    ]

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.source_id).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
            )
            source_ids = result.scalars().all()

            confirmed_cats = set()
            for source_id in source_ids:
                for cat in self._CATEGORIES:
                    if source_id.startswith(cat):
                        confirmed_cats.add(cat)
                        break

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(len(confirmed_cats)), signal_count=len(source_ids),
                is_null=False, confidence=0.95,
                metadata={"categories": sorted(confirmed_cats)},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class DaysSinceLastFilingFeature(BaseFeature):
    name = "days_since_last_filing"
    version = "v1"
    category = "temporal"
    description = "Days since the company's most recent corporate filing. Lower = more active."
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        try:
            result = await db.execute(
                select(func.max(SignalRecord.scraped_at)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.source_id.like("corporate_%"),
                    )
                )
            )
            last_filing = result.scalar()
            if not last_filing:
                return self._null_value(company_id, horizon_days)

            if last_filing.tzinfo is None:
                last_filing = last_filing.replace(tzinfo=UTC)
            days = (datetime.now(tz=UTC) - last_filing).days

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(days), is_null=False, confidence=0.95,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class DaysSinceLastRegulatoryActionFeature(BaseFeature):
    name = "days_since_last_regulatory_action"
    version = "v1"
    category = "temporal"
    description = "Days since most recent regulatory enforcement signal. Lower = recent enforcement."
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        try:
            result = await db.execute(
                select(func.max(SignalRecord.scraped_at)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.source_id.like("regulatory_%"),
                    )
                )
            )
            last_action = result.scalar()
            if not last_action:
                return self._null_value(company_id, horizon_days)

            if last_action.tzinfo is None:
                last_action = last_action.replace(tzinfo=UTC)
            days = (datetime.now(tz=UTC) - last_action).days

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(days), is_null=False, confidence=0.95,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class SignalDecayAdjustedScoreFeature(BaseFeature):
    name = "signal_decay_adjusted_score"
    version = "v1"
    category = "temporal"
    description = "Exponentially decayed signal count: recent signals weight more. Range: 0–100."

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        import math

        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        now = datetime.now(tz=UTC)
        half_life_days = horizon_days / 2

        try:
            result = await db.execute(
                select(SignalRecord.scraped_at, SignalRecord.confidence_score).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
            )
            rows = result.all()
            if not rows:
                return self._null_value(company_id, horizon_days)

            decayed_score = 0.0
            for scraped_at, confidence in rows:
                if scraped_at is None:
                    continue
                if scraped_at.tzinfo is None:
                    scraped_at = scraped_at.replace(tzinfo=UTC)
                age_days = (now - scraped_at).total_seconds() / 86400
                decay = math.exp(-0.693 * age_days / half_life_days)  # 0.693 = ln(2)
                decayed_score += decay * (confidence or 1.0)

            normalized = min(100.0, decayed_score * 10)

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=normalized, signal_count=len(rows),
                is_null=False, confidence=0.88,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


# ══════════════════════════════════════════════════════════════════════════════
# MARKET FEATURES
# ══════════════════════════════════════════════════════════════════════════════

@register_feature
class PriceMomentumFeature(BaseFeature):
    name = "price_momentum"
    version = "v1"
    category = "market"
    description = "Price return over window vs TSX composite. Negative = underperformance."
    requires_market = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "market_price_signal",
                    )
                ).order_by(SignalRecord.scraped_at.asc())
            )
            rows = result.scalars().all()
            if len(rows) < 2:
                return self._null_value(company_id, horizon_days)

            prices = []
            for row in rows:
                try:
                    val = json.loads(row) if isinstance(row, str) else (row or {})
                    price = val.get("close") or val.get("price")
                    if price:
                        prices.append(float(price))
                except (ValueError, TypeError, AttributeError):
                    continue

            if len(prices) < 2:
                return self._null_value(company_id, horizon_days)

            momentum = (prices[-1] - prices[0]) / prices[0]  # Simple return

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=max(-1.0, min(1.0, momentum)),
                signal_count=len(prices), is_null=False, confidence=0.90,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class VolumeAnomalyZScoreFeature(BaseFeature):
    name = "volume_anomaly_zscore"
    version = "v1"
    category = "market"
    description = "Z-score of recent trading volume vs window average. High = unusual activity."
    requires_market = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        import statistics

        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "market_price_signal",
                    )
                )
            )
            rows = result.scalars().all()
            volumes = []
            for row in rows:
                try:
                    val = json.loads(row) if isinstance(row, str) else (row or {})
                    vol = val.get("volume")
                    if vol:
                        volumes.append(float(vol))
                except (ValueError, TypeError, AttributeError):
                    continue

            if len(volumes) < 5:
                return self._null_value(company_id, horizon_days)

            mean_vol = statistics.mean(volumes)
            std_vol = statistics.stdev(volumes) if len(volumes) > 1 else 1.0
            if std_vol == 0:
                return self._null_value(company_id, horizon_days)

            recent_vol = volumes[-1]
            z = (recent_vol - mean_vol) / std_vol
            z_clipped = max(-5.0, min(5.0, z))

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=z_clipped, signal_count=len(volumes),
                is_null=False, confidence=0.85,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class ShortInterestPctFeature(BaseFeature):
    name = "short_interest_pct"
    version = "v1"
    category = "market"
    description = "Short interest as percentage of float. High = bearish institutional view."
    requires_market = True
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "market_options_flow",
                    )
                ).order_by(SignalRecord.scraped_at.desc()).limit(1)
            )
            row = result.scalar()
            if not row:
                return self._null_value(company_id, horizon_days)

            val = json.loads(row) if isinstance(row, str) else (row or {})
            short_pct = val.get("short_interest_pct")
            if short_pct is None:
                return self._null_value(company_id, horizon_days)

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(short_pct), is_null=False, confidence=0.88,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)
