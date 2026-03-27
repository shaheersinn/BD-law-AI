"""
app/features/runner.py — Feature Computation Runner.

Orchestrates feature computation across all companies × all features × all horizons.

Called by:
  - Celery task `features.run_all_features` (daily, 2am Toronto time)
  - Celery task `features.run_company_features` (on-demand, per company)
  - Phase 6 ML training (reads from company_features table)

Architecture:
  - Batch companies in groups of 50 (memory management)
  - Compute all features in parallel per company using asyncio.gather
  - Persist to company_features table
  - Skip companies with no signals in the window (no-op, not an error)
  - Log feature coverage metrics for monitoring

Performance targets:
  - 10,000 companies × 60 features × 3 horizons = 1.8M feature computations/day
  - Target: < 4 hours wall time on 4-worker Celery pool
  - Achieved by: async DB queries, batch inserts, sparse storage (skip is_null=True)
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, delete, and_

from app.features.base import FeatureRegistry, FeatureValue, BaseFeature

log = structlog.get_logger(__name__)

_BATCH_SIZE = 50         # Companies per batch
_MAX_CONCURRENT = 10    # Concurrent feature computations per company


class FeatureRunner:
    """
    Batch feature computation engine.
    """

    def __init__(
        self,
        db: Any,            # AsyncSession
        mongo_db: Any,      # MongoDB handle
        skip_null: bool = True,  # Don't persist is_null=True features
    ) -> None:
        self._db = db
        self._mongo_db = mongo_db
        self._skip_null = skip_null

    async def run_all(self, limit_companies: int | None = None) -> dict[str, Any]:
        """
        Run all features for all active companies.
        Returns summary dict with counts.
        """
        from app.models.company import Company

        start = time.monotonic()

        # Get all active companies
        result = await self._db.execute(
            select(Company.id).where(Company.status == "active")
            .order_by(Company.priority_tier.asc(), Company.signal_count.desc())
            .limit(limit_companies)
        )
        company_ids = list(result.scalars().all())

        log.info("feature_runner_start",
                 total_companies=len(company_ids),
                 total_features=FeatureRegistry.count())

        total_computed = 0
        total_persisted = 0
        total_null = 0
        errors = 0

        # Process in batches
        for batch_start in range(0, len(company_ids), _BATCH_SIZE):
            batch = company_ids[batch_start:batch_start + _BATCH_SIZE]
            batch_results = await asyncio.gather(
                *[self._compute_company(cid) for cid in batch],
                return_exceptions=True,
            )
            for result in batch_results:
                if isinstance(result, Exception):
                    errors += 1
                    log.error("feature_runner_company_error", error=str(result))
                    continue
                computed, persisted, null = result
                total_computed += computed
                total_persisted += persisted
                total_null += null

        elapsed = time.monotonic() - start
        summary = {
            "companies_processed": len(company_ids),
            "features_computed": total_computed,
            "features_persisted": total_persisted,
            "features_null_skipped": total_null,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
            "computed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        log.info("feature_runner_complete", **summary)
        return summary

    async def run_company(self, company_id: int) -> dict[str, Any]:
        """Run all features for a single company (on-demand)."""
        computed, persisted, null = await self._compute_company(company_id)
        return {"company_id": company_id, "computed": computed,
                "persisted": persisted, "null_skipped": null}

    async def _compute_company(self, company_id: int) -> tuple[int, int, int]:
        """Compute all features for one company. Returns (computed, persisted, null)."""
        features = FeatureRegistry.all()
        computed = 0
        persisted = 0
        null = 0

        # Fan out: compute all features concurrently (capped by semaphore)
        sem = asyncio.Semaphore(_MAX_CONCURRENT)

        async def _compute_one(feature: BaseFeature) -> list[FeatureValue]:
            async with sem:
                return await feature.compute_all_horizons(
                    company_id, self._db, self._mongo_db
                )

        all_results = await asyncio.gather(
            *[_compute_one(f) for f in features],
            return_exceptions=True,
        )

        feature_values: list[FeatureValue] = []
        for result in all_results:
            if isinstance(result, Exception):
                log.warning("feature_compute_exception",
                            company_id=company_id, error=str(result))
                continue
            feature_values.extend(result)
            computed += len(result)

        # Persist to DB
        for fv in feature_values:
            if fv.is_null and self._skip_null:
                null += 1
                continue
            try:
                await self._persist_feature_value(fv)
                persisted += 1
            except Exception as exc:
                log.error("feature_persist_error",
                          company_id=company_id,
                          feature=fv.feature_name,
                          error=str(exc))

        return computed, persisted, null

    async def _persist_feature_value(self, fv: FeatureValue) -> None:
        """Upsert a single FeatureValue into company_features."""
        from app.models.features import CompanyFeature
        import json

        existing = await self._db.execute(
            select(CompanyFeature).where(
                and_(
                    CompanyFeature.company_id == fv.company_id,
                    CompanyFeature.feature_name == fv.feature_name,
                    CompanyFeature.feature_version == fv.feature_version,
                    CompanyFeature.horizon_days == fv.horizon_days,
                )
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            row.value = fv.value
            row.is_null = fv.is_null
            row.confidence = fv.confidence
            row.signal_count = fv.signal_count
            row.computed_at = fv.computed_at
            row.metadata = json.dumps(fv.metadata) if fv.metadata else None
        else:
            self._db.add(CompanyFeature(
                company_id=fv.company_id,
                feature_name=fv.feature_name,
                feature_version=fv.feature_version,
                horizon_days=fv.horizon_days,
                category=fv.metadata.get("category", ""),
                value=fv.value,
                is_null=fv.is_null,
                confidence=fv.confidence,
                signal_count=fv.signal_count,
                computed_at=fv.computed_at,
                metadata=json.dumps(fv.metadata) if fv.metadata else None,
            ))

        await self._db.commit()

    async def get_feature_vector(
        self,
        company_id: int,
        horizon_days: int,
        feature_version: str = "v1",
    ) -> dict[str, float | None]:
        """
        Return the full feature vector for a company × horizon as a dict.
        Used by Phase 6 ML training and Phase 7 scoring API.
        """
        from app.models.features import CompanyFeature

        result = await self._db.execute(
            select(CompanyFeature).where(
                and_(
                    CompanyFeature.company_id == company_id,
                    CompanyFeature.horizon_days == horizon_days,
                    CompanyFeature.feature_version == feature_version,
                )
            )
        )
        rows = result.scalars().all()

        vector: dict[str, float | None] = {}
        for row in rows:
            vector[row.feature_name] = None if row.is_null else row.value

        return vector
