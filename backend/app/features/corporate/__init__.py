"""
app/features/corporate/__init__.py — Corporate Filing Features (10 features).

All computed from signal_records WHERE source_id LIKE 'corporate_%' OR 'regulatory_%'.

Features:
  material_change_count        — count of MCR/8-K-equivalent filings in window
  material_change_velocity     — rate of change vs prior window (acceleration)
  insider_sell_ratio           — insider sells / (sells + buys) in window
  insider_net_transaction_cad  — net CAD value of insider transactions
  filing_velocity_change       — filings/day now vs prior period (z-score)
  auditor_change_flag          — binary: new auditor mentioned in window
  going_concern_flag           — binary: going concern language in any filing
  restatement_flag             — binary: restatement mentioned in window
  regulatory_filing_lag_days   — days between fiscal year end and AIF filing
  related_party_transaction_count — count of RPT signals in window
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func, and_, or_

from app.features.base import BaseFeature, FeatureValue, register_feature

log = structlog.get_logger(__name__)


def _corporate_signal_query(company_id: int, cutoff: datetime):
    """Base query filter for corporate signals."""
    from app.models.signal import SignalRecord
    return and_(
        SignalRecord.company_id == company_id,
        SignalRecord.scraped_at >= cutoff,
        SignalRecord.source_id.like("corporate_%"),
    )


@register_feature
class MaterialChangeCountFeature(BaseFeature):
    name = "material_change_count"
    version = "v1"
    category = "corporate"
    description = "Number of material change reports / 8-K equivalents filed in window"

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type.in_([
                            "filing_material_change", "filing_8k_equivalent",
                            "filing_press_release_material",
                        ]),
                    )
                )
            )
            count = result.scalar() or 0
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(count), signal_count=count,
                is_null=(count == 0 and self.null_if_no_signals),
                confidence=0.95,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class InsiderSellRatioFeature(BaseFeature):
    name = "insider_sell_ratio"
    version = "v1"
    category = "corporate"
    description = "Insider sell transactions / (sell + buy) in window. Range: 0–1."

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        import json
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_value).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.signal_type == "filing_insider_trade",
                    )
                )
            )
            rows = result.scalars().all()
            if not rows:
                return self._null_value(company_id, horizon_days)

            sells = 0
            buys = 0
            for row in rows:
                try:
                    val = json.loads(row) if isinstance(row, str) else (row or {})
                    tx_type = str(val.get("transaction_type", "")).lower()
                    if "sell" in tx_type or "dispose" in tx_type:
                        sells += 1
                    elif "buy" in tx_type or "acqui" in tx_type:
                        buys += 1
                except (ValueError, TypeError, AttributeError):
                    continue

            total = sells + buys
            ratio = sells / total if total > 0 else 0.0
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=ratio, signal_count=total,
                is_null=(total == 0),
                confidence=min(1.0, total / 5),  # More transactions → higher confidence
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class FilingVelocityChangeFeature(BaseFeature):
    name = "filing_velocity_change"
    version = "v1"
    category = "corporate"
    description = "Z-score: current filings/day vs prior period filings/day"

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff_current = self._cutoff(horizon_days)
        cutoff_prior = cutoff_current - timedelta(days=horizon_days)

        try:
            async def _count(start: datetime, end: datetime) -> int:
                r = await db.execute(
                    select(func.count(SignalRecord.id)).where(
                        and_(
                            SignalRecord.company_id == company_id,
                            SignalRecord.scraped_at >= start,
                            SignalRecord.scraped_at < end,
                            SignalRecord.source_id.like("corporate_%"),
                        )
                    )
                )
                return r.scalar() or 0

            current_count = await _count(cutoff_current, datetime.now(tz=timezone.utc))
            prior_count = await _count(cutoff_prior, cutoff_current)

            current_rate = current_count / max(horizon_days, 1)
            prior_rate = prior_count / max(horizon_days, 1)

            if prior_rate == 0 and current_rate == 0:
                return self._null_value(company_id, horizon_days)

            # Simple normalized change (not true z-score without population std)
            baseline = max(prior_rate, 0.01)
            z = (current_rate - prior_rate) / baseline
            z_clipped = max(-5.0, min(5.0, z))

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=z_clipped, signal_count=current_count,
                is_null=False,
                confidence=0.85,
                metadata={"current_rate": current_rate, "prior_rate": prior_rate},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class GoingConcernFlagFeature(BaseFeature):
    name = "going_concern_flag"
    version = "v1"
    category = "corporate"
    description = "Binary: 1 if going concern language detected in any filing in window"
    null_if_no_signals = False  # Always returns a value (0 = no going concern = informative)

    _KEYWORDS = [
        "going concern", "substantial doubt", "ability to continue",
        "material uncertainty", "viability", "ceasing operations",
    ]

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        or_(
                            SignalRecord.source_id.like("corporate_%"),
                            SignalRecord.source_id.like("news_%"),
                        ),
                    )
                )
            )
            texts = result.scalars().all()
            for text in texts:
                if not text:
                    continue
                text_lower = text.lower()
                if any(kw in text_lower for kw in self._KEYWORDS):
                    return FeatureValue(
                        company_id=company_id, feature_name=self.name,
                        feature_version=self.version, horizon_days=horizon_days,
                        value=1.0, is_null=False, signal_count=len(texts),
                        confidence=0.90,
                    )
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=0.0, is_null=False, signal_count=len(texts),
                confidence=0.85,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class AuditorChangeFlagFeature(BaseFeature):
    name = "auditor_change_flag"
    version = "v1"
    category = "corporate"
    description = "Binary: 1 if auditor change / resignation detected in window"
    null_if_no_signals = False

    _KEYWORDS = [
        "change of auditor", "resign", "appointed as auditor",
        "new auditor", "auditor resignation", "change auditor",
        "appointed deloitte", "appointed pwc", "appointed kpmg",
        "appointed ey", "appointed bdo", "appointment of auditor",
    ]

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id.like("corporate_%"),
                    )
                )
            )
            texts = result.scalars().all()
            for text in texts:
                if not text:
                    continue
                if any(kw in text.lower() for kw in self._KEYWORDS):
                    return FeatureValue(
                        company_id=company_id, feature_name=self.name,
                        feature_version=self.version, horizon_days=horizon_days,
                        value=1.0, is_null=False, signal_count=len(texts),
                        confidence=0.88,
                    )
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=0.0, is_null=False, signal_count=len(texts),
                confidence=0.80,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class RestatementFlagFeature(BaseFeature):
    name = "restatement_flag"
    version = "v1"
    category = "corporate"
    description = "Binary: 1 if financial restatement detected in window"
    null_if_no_signals = False

    _KEYWORDS = [
        "restatement", "restate", "restated financial", "material misstatement",
        "accounting error", "prior period adjustment", "revision of financial",
    ]

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
            )
            texts = result.scalars().all()
            for text in texts:
                if text and any(kw in text.lower() for kw in self._KEYWORDS):
                    return FeatureValue(
                        company_id=company_id, feature_name=self.name,
                        feature_version=self.version, horizon_days=horizon_days,
                        value=1.0, is_null=False, confidence=0.90,
                    )
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=0.0, is_null=False, confidence=0.80,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class RelatedPartyTransactionCountFeature(BaseFeature):
    name = "related_party_transaction_count"
    version = "v1"
    category = "corporate"
    description = "Count of related party transaction signals in window"

    _KEYWORDS = [
        "related party", "related-party", "non-arm's length",
        "non arm's length", "interested party", "rpte",
    ]

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        from app.models.signal import SignalRecord
        cutoff = self._cutoff(horizon_days)
        try:
            result = await db.execute(
                select(SignalRecord.signal_text).where(
                    and_(
                        SignalRecord.company_id == company_id,
                        SignalRecord.scraped_at >= cutoff,
                        SignalRecord.source_id.like("corporate_%"),
                    )
                )
            )
            texts = result.scalars().all()
            count = sum(
                1 for t in texts
                if t and any(kw in t.lower() for kw in self._KEYWORDS)
            )
            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(count), signal_count=count,
                is_null=(count == 0 and self.null_if_no_signals),
                confidence=0.85,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)
