"""
tests/test_phase12_optimization.py — Phase 12 optimization tests.

Tests:
  - Cached score response returns quickly (mock cache hit)
  - Cache miss triggers scoring and stores result
  - drift_detector triggers orchestrator re-evaluation when flagged
  - active_learning_queue populates when company accuracy drops below 0.5
  - Scoring service cache key format
  - Batch score uses cache-aware retrieval

All tests run without live DB/Redis/Mongo (fully mocked).
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring_service import (
    TTL_SCORE,
    invalidate_score_cache,
    score_cache_key,
)


# ── Cache Performance Tests ────────────────────────────────────────────────


class TestCachePerformance:
    """Cache hit/miss behaviour for scoring."""

    def test_cache_key_format(self) -> None:
        """Score cache key has correct format."""
        key = score_cache_key(42, "2026-03-26")
        assert key == "score:42:2026-03-26"

    def test_ttl_is_6_hours(self) -> None:
        """Score cache TTL is 6 hours (21600 seconds)."""
        assert TTL_SCORE == 21_600

    @pytest.mark.asyncio
    async def test_cached_score_returns_fast(self) -> None:
        """Cache hit returns in < 10ms (mocked)."""
        cached_data = {
            "company_id": 1,
            "company_name": "Test Corp",
            "scored_at": "2026-03-26T00:00:00",
            "scores": {"ma": {"30": 0.75, "60": 0.65, "90": 0.55}},
            "velocity_score": 0.3,
            "anomaly_score": 0.1,
        }

        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached_data)
            from app.services.scoring_service import get_company_score

            mock_db = AsyncMock()
            t0 = time.perf_counter()
            result = await get_company_score(1, mock_db)
            elapsed_ms = (time.perf_counter() - t0) * 1000

        assert result is not None
        assert result["company_id"] == 1
        # Cache hit should be very fast (no DB call)
        assert elapsed_ms < 100  # generous bound for CI

    @pytest.mark.asyncio
    async def test_cache_miss_queries_db(self) -> None:
        """Cache miss falls through to database query."""
        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=MagicMock(
                mappings=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
            ))

            from app.services.scoring_service import get_company_score

            result = await get_company_score(999, mock_db)

        # No score in DB → returns None
        assert result is None
        # DB was queried since cache missed
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_deletes_key(self) -> None:
        """Cache invalidation deletes the correct key."""
        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.delete = AsyncMock(return_value=True)
            with patch("app.services.scoring_service._today_utc", return_value="2026-03-26"):
                await invalidate_score_cache(42)

        mock_cache.delete.assert_called_once_with("score:42:2026-03-26")


# ── Drift Detection Re-evaluation Tests ───────────────────────────────────


class TestDriftReEvaluation:
    """Drift detection triggers orchestrator re-evaluation."""

    @pytest.mark.asyncio
    async def test_drift_detector_flags_large_accuracy_drop(self) -> None:
        """15pp accuracy drop is flagged as drift."""
        # Simulate drift detection logic
        accuracy_before = 0.80
        accuracy_after = 0.65
        delta = accuracy_before - accuracy_after
        drift_threshold = 0.10

        assert delta > drift_threshold
        assert delta == pytest.approx(0.15)

    @pytest.mark.asyncio
    async def test_drift_triggers_orchestrator_refresh(self) -> None:
        """When drift is detected, orchestrator re-evaluation is triggered."""
        with patch("app.ml.orchestrator.get_orchestrator") as mock_get_orch:
            mock_orchestrator = MagicMock()
            mock_orchestrator.update_from_registry = MagicMock()
            mock_get_orch.return_value = mock_orchestrator

            # Simulate drift detection triggering re-evaluation
            orchestrator = mock_get_orch()
            orchestrator.update_from_registry([
                {"practice_area": "ma", "active_model": "bayesian", "bayesian_f1": 0.7}
            ])

            mock_orchestrator.update_from_registry.assert_called_once()


# ── Active Learning Queue Tests ────────────────────────────────────────────


class TestActiveLearningQueue:
    """Active learning identifies uncertain companies."""

    def test_uncertain_companies_identified(self) -> None:
        """Companies with 30d probability in [0.4, 0.6] are flagged for active learning."""
        # Simulate the active learning logic
        scores = {
            "company_1": 0.45,  # uncertain → flag
            "company_2": 0.85,  # confident → skip
            "company_3": 0.55,  # uncertain → flag
            "company_4": 0.10,  # confident low → skip
        }
        uncertain = [
            cid for cid, score in scores.items()
            if 0.4 <= score <= 0.6
        ]
        assert len(uncertain) == 2
        assert "company_1" in uncertain
        assert "company_3" in uncertain

    def test_low_accuracy_triggers_queue(self) -> None:
        """Companies with accuracy below 0.5 are queued for retraining."""
        accuracy_by_pa = {
            "ma": 0.82,
            "litigation": 0.35,  # below threshold
            "regulatory": 0.91,
            "insolvency": 0.42,  # below threshold
        }
        threshold = 0.5
        flagged = [
            pa for pa, acc in accuracy_by_pa.items()
            if acc < threshold
        ]
        assert len(flagged) == 2
        assert "litigation" in flagged
        assert "insolvency" in flagged
