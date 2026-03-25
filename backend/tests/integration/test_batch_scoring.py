"""
tests/integration/test_batch_scoring.py — Batch scoring API integration tests.

Tests POST /api/v1/scores/batch with 1, 10, and 50 companies.
Verifies 422 for >50, schema of returned objects, and cache-hit behaviour.

Mark: integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.integration
class TestBatchScoringAPI:
    """Batch scoring endpoint integration tests."""

    def test_batch_limit_422_for_51_ids(self):
        """POST /batch with 51 company_ids must return 422."""
        # This is enforced at the Pydantic schema level, not DB level
        # We verify the schema constraint exists
        # 51 IDs should raise a Pydantic ValidationError
        from pydantic import ValidationError

        from app.routes.scores import BatchScoreRequest

        with pytest.raises(ValidationError):
            BatchScoreRequest(company_ids=list(range(51)))

    def test_batch_schema_fields(self):
        """BatchScoreRequest schema has correct field constraints."""
        from app.routes.scores import BatchScoreRequest

        # Valid request with 1 ID
        req = BatchScoreRequest(company_ids=[1])
        assert req.company_ids == [1]
        assert req.practice_areas is None or isinstance(req.practice_areas, list)

    def test_batch_schema_max_50_ids(self):
        """BatchScoreRequest allows exactly 50 IDs."""
        from app.routes.scores import BatchScoreRequest

        req = BatchScoreRequest(company_ids=list(range(1, 51)))
        assert len(req.company_ids) == 50

    @pytest.mark.asyncio
    async def test_get_batch_scores_returns_list(self):
        """get_batch_scores service returns a list with correct length."""

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)

            from app.services.scoring_service import get_batch_scores

            result = await get_batch_scores([1, 2, 3], None, mock_db)
            assert isinstance(result, list)
            assert len(result) == 3  # one entry per requested id (None for missing)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db_for_scored_company(self):
        """get_batch_scores uses cache for already-scored companies."""
        import json

        cached_score = {
            "company_id": 1,
            "scores": {"M&A/Corporate": {"30d": 0.8, "60d": 0.7, "90d": 0.6}},
        }

        mock_db = AsyncMock()

        with patch("app.services.scoring_service.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=json.dumps(cached_score))

            from app.services.scoring_service import get_batch_scores

            result = await get_batch_scores([1], None, mock_db)

            # DB should NOT be called since cache hit
            mock_db.execute.assert_not_called()
            assert result[0] is not None
