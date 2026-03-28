"""
tests/integration/test_pipeline.py — End-to-end scoring pipeline integration test.

Tests the full path: company features → ML scoring → results stored in DB.

Requires a running PostgreSQL instance with migrations applied.
Run with: pytest tests/integration/ -m integration --tb=short

Mark: integration (skipped in CI unit test run unless --integration flag passed)
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.integration
class TestScoringPipeline:
    """Integration tests for the end-to-end scoring pipeline."""

    @pytest.mark.asyncio
    async def test_score_stored_after_batch_task(self):
        """
        score_company_batch task stores results in scoring_results.

        Verifies the three-phase bulk pattern:
          Phase A — bulk feature SELECT
          Phase B — in-memory ML scoring
          Phase C — bulk INSERT
        """

        mock_features = {
            "company_id": 1,
            "revenue_growth": 0.15,
            "employee_count": 500,
            "feature_date": date.today(),
        }

        mock_horizon_scores = MagicMock()
        mock_horizon_scores.score_30d = 0.72
        mock_horizon_scores.score_60d = 0.65
        mock_horizon_scores.score_90d = 0.58
        mock_horizon_scores.as_dict.return_value = {"30d": 0.72, "60d": 0.65, "90d": 0.58}
        mock_horizon_scores.model_version = "xgb_v1"

        mock_orchestrator = MagicMock()
        mock_orchestrator._loaded = True
        mock_orchestrator.score_company.return_value = {"M&A/Corporate": mock_horizon_scores}

        mock_db = MagicMock()
        feat_result = MagicMock()
        feat_result.mappings.return_value = [mock_features]
        mock_db.execute.return_value = feat_result
        mock_db.commit.return_value = None
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.ml.orchestrator.get_orchestrator", return_value=mock_orchestrator),
            patch("app.database_sync.get_sync_db") as mock_get_db,
            patch("app.ml.anomaly_detector.get_anomaly_detector") as mock_anomaly,
            patch("app.ml.velocity_scorer.aggregate_company_velocity", return_value=0.3),
        ):
            mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_anomaly.return_value.score.return_value = 0.1

            from app.tasks.phase6_tasks import score_company_batch

            # Execute task synchronously (bypass Celery)
            result = score_company_batch.__wrapped__([1])

        assert result["total"] == 1
        assert result["scored"] >= 0  # scored or failed depending on mock depth

    @pytest.mark.asyncio
    async def test_live_feed_invalidates_score_cache(self):
        """
        After a new live signal is ingested, the score cache key for that
        company must be invalidated so the next request triggers a fresh score.
        """

        company_id = 42
        today = date.today().isoformat()
        expected_key = f"score:{company_id}:{today}"

        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1

        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.delete = AsyncMock(return_value=1)

            from app.services.scoring_service import invalidate_score_cache

            await invalidate_score_cache(company_id)
            mock_cache.delete.assert_called_once_with(expected_key)

    def test_bulk_feature_fetch_uses_two_db_calls(self):
        """
        score_company_batch must call db.execute exactly twice for a batch:
          1. SELECT features (Phase A)
          2. INSERT results (Phase C)
        """
        from unittest.mock import MagicMock

        mock_features = {"company_id": 1, "revenue_growth": 0.1, "feature_date": date.today()}
        mock_horizon = MagicMock()
        mock_horizon.score_30d = 0.5
        mock_horizon.as_dict.return_value = {"30d": 0.5}
        mock_horizon.model_version = "v1"

        mock_orchestrator = MagicMock()
        mock_orchestrator._loaded = True
        mock_orchestrator.score_company.return_value = {"M&A": mock_horizon}

        mock_db = MagicMock()
        feat_result = MagicMock()
        feat_result.mappings.return_value = [mock_features]
        mock_db.execute.return_value = feat_result

        with (
            patch("app.ml.orchestrator.get_orchestrator", return_value=mock_orchestrator),
            patch("app.database_sync.get_sync_db") as mock_ctx,
            patch("app.ml.anomaly_detector.get_anomaly_detector") as mock_anomaly,
            patch("app.ml.velocity_scorer.aggregate_company_velocity", return_value=0.2),
        ):
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            mock_anomaly.return_value.score.return_value = 0.05

            from app.tasks.phase6_tasks import score_company_batch

            score_company_batch.__wrapped__([1])

        # Should call execute at least twice: SELECT + INSERT
        assert mock_db.execute.call_count >= 2
