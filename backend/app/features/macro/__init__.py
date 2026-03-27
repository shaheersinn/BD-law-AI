"""
app/features/macro/__init__.py — Corporate Graph Features (4 features).

These features use MongoDB corporate graph (populated by Phase 5 Agent 080).
The graph models director interlocks and subsidiary relationships.

If MongoDB is unavailable or graph not yet populated, all return is_null=True.
This is expected in Phase 2 — graph is populated incrementally from Phase 5 onward.

Features:
  director_interlocks_score     — # of shared directors with companies that have active signals
  board_distress_contagion      — distress score propagated from connected companies
  subsidiary_signal_count       — signals from known subsidiaries/related entities
  related_entity_signal_propagation — weighted signal from parent/child/sibling entities
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import structlog

from app.features.base import BaseFeature, FeatureValue, register_feature

log = structlog.get_logger(__name__)


@register_feature
class DirectorInterlocksScoreFeature(BaseFeature):
    name = "director_interlocks_score"
    version = "v1"
    category = "graph"
    description = "Count of shared directors with other companies that have active signals in window."
    requires_mongo = True
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        if not mongo_db:
            return self._null_value(company_id, horizon_days)
        try:
            cutoff = self._cutoff(horizon_days)
            # Query MongoDB corporate graph for director interlocks
            graph_col = mongo_db["corporate_graph"]
            doc = await graph_col.find_one({"company_id": company_id})
            if not doc:
                return self._null_value(company_id, horizon_days)

            connected_ids = [
                rel["target_company_id"]
                for rel in doc.get("relationships", [])
                if rel.get("relationship_type") == "director_interlocked"
            ]
            if not connected_ids:
                return self._null_value(company_id, horizon_days)

            # Count how many connected companies have active signals
            from app.models.signal import SignalRecord
            from sqlalchemy import select, func, and_
            result = await db.execute(
                select(func.count(SignalRecord.id.distinct())).where(
                    and_(
                        SignalRecord.company_id.in_(connected_ids),
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
            )
            active_count = result.scalar() or 0

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(min(active_count, 20)),
                signal_count=active_count, is_null=False,
                confidence=0.80,
                metadata={"connected_companies": len(connected_ids),
                          "active_connected": active_count},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class BoardDistressContagionFeature(BaseFeature):
    name = "board_distress_contagion"
    version = "v1"
    category = "graph"
    description = "Weighted distress score propagated from board-connected companies. Range: 0–10."
    requires_mongo = True
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        if not mongo_db:
            return self._null_value(company_id, horizon_days)
        try:
            cutoff = self._cutoff(horizon_days)
            graph_col = mongo_db["corporate_graph"]
            doc = await graph_col.find_one({"company_id": company_id})
            if not doc:
                return self._null_value(company_id, horizon_days)

            connected = [
                rel for rel in doc.get("relationships", [])
                if rel.get("relationship_type") in ("director_interlocked", "parent", "subsidiary")
            ]
            if not connected:
                return self._null_value(company_id, horizon_days)

            from app.models.signal import SignalRecord
            from sqlalchemy import select, func, and_

            total_contagion = 0.0
            for rel in connected[:20]:  # Cap at 20 connections
                target_id = rel.get("target_company_id")
                if not target_id:
                    continue
                weight = {"director_interlocked": 0.3, "parent": 0.7, "subsidiary": 0.5}.get(
                    rel.get("relationship_type", ""), 0.3
                )
                result = await db.execute(
                    select(func.count(SignalRecord.id)).where(
                        and_(
                            SignalRecord.company_id == target_id,
                            SignalRecord.scraped_at >= cutoff,
                            SignalRecord.signal_type.in_([
                                "insolvency_filing", "regulatory_osc_enforcement",
                                "filing_material_change", "social_breach_detected",
                            ]),
                        )
                    )
                )
                count = result.scalar() or 0
                total_contagion += count * weight

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=min(10.0, total_contagion),
                is_null=False, confidence=0.70,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class SubsidiarySignalCountFeature(BaseFeature):
    name = "subsidiary_signal_count"
    version = "v1"
    category = "graph"
    description = "Total signals from known subsidiaries/related entities in window."
    requires_mongo = True
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        if not mongo_db:
            return self._null_value(company_id, horizon_days)
        try:
            cutoff = self._cutoff(horizon_days)
            graph_col = mongo_db["corporate_graph"]
            doc = await graph_col.find_one({"company_id": company_id})
            if not doc:
                return self._null_value(company_id, horizon_days)

            subsidiary_ids = [
                rel["target_company_id"]
                for rel in doc.get("relationships", [])
                if rel.get("relationship_type") in ("subsidiary", "division")
            ]
            if not subsidiary_ids:
                return self._null_value(company_id, horizon_days)

            from app.models.signal import SignalRecord
            from sqlalchemy import select, func, and_
            result = await db.execute(
                select(func.count(SignalRecord.id)).where(
                    and_(
                        SignalRecord.company_id.in_(subsidiary_ids),
                        SignalRecord.scraped_at >= cutoff,
                    )
                )
            )
            count = result.scalar() or 0

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=float(count), signal_count=count,
                is_null=(count == 0),
                confidence=0.80,
                metadata={"subsidiaries_checked": len(subsidiary_ids)},
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)


@register_feature
class RelatedEntitySignalPropagationFeature(BaseFeature):
    name = "related_entity_signal_propagation"
    version = "v1"
    category = "graph"
    description = "Weighted signal count propagated from parent/peer entities. Range: 0–20."
    requires_mongo = True
    null_if_no_signals = True

    async def compute(self, company_id: int, horizon_days: int, db: Any, mongo_db: Any) -> FeatureValue:
        if not mongo_db:
            return self._null_value(company_id, horizon_days)
        try:
            cutoff = self._cutoff(horizon_days)
            graph_col = mongo_db["corporate_graph"]
            doc = await graph_col.find_one({"company_id": company_id})
            if not doc:
                return self._null_value(company_id, horizon_days)

            # Relationship type → propagation weight
            weights = {
                "parent": 0.8,
                "subsidiary": 0.5,
                "peer": 0.2,
                "joint_venture": 0.4,
                "director_interlocked": 0.2,
            }

            from app.models.signal import SignalRecord
            from sqlalchemy import select, func, and_

            propagated = 0.0
            total_signals = 0

            for rel in doc.get("relationships", [])[:30]:
                target_id = rel.get("target_company_id")
                rel_type = rel.get("relationship_type", "")
                weight = weights.get(rel_type, 0.1)
                if not target_id:
                    continue

                result = await db.execute(
                    select(func.count(SignalRecord.id)).where(
                        and_(
                            SignalRecord.company_id == target_id,
                            SignalRecord.scraped_at >= cutoff,
                        )
                    )
                )
                count = result.scalar() or 0
                propagated += count * weight
                total_signals += count

            return FeatureValue(
                company_id=company_id, feature_name=self.name,
                feature_version=self.version, horizon_days=horizon_days,
                value=min(20.0, propagated),
                signal_count=total_signals,
                is_null=(propagated == 0),
                confidence=0.70,
            )
        except Exception as exc:
            log.error("feature_error", feature=self.name, error=str(exc))
            return self._null_value(company_id, horizon_days)
