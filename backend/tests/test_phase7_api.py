"""
tests/test_phase7_api.py — Phase 7 Scoring API tests.

Tests:
  1.  GET /api/v1/scores/{id}            — 200 + correct schema
  2.  GET /api/v1/scores/{id}            — 404 for unknown company
  3.  GET /api/v1/scores/{id}            — 401 without token
  4.  GET /api/v1/scores/{id}/explain    — 200 + explanation schema
  5.  POST /api/v1/scores/batch          — 200 with list results
  6.  POST /api/v1/scores/batch          — 422 for >50 company_ids
  7.  GET /api/v1/companies/search?q=    — returns list (may be empty)
  8.  GET /api/v1/companies/{id}         — 404 for unknown company
  9.  GET /api/v1/signals/{id}           — 200 with list
  10. GET /api/v1/trends/practice_areas  — 200 with list
  11. GET /api/health                    — includes ml_ready field
  12. score_company_batch task           — bulk path: single SELECT, single INSERT
  13. score_company_batch task           — missing features increments failed count
  14. invalidate_score_cache             — deletes the correct Redis key
  15. GET /api/v1/companies/search       — 401 without token
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_no_auth(path: str) -> int:
    """Return status code for an unauthenticated request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code


# ── 1. GET /api/v1/scores/{id} — 200 + schema ────────────────────────────────


@pytest.mark.asyncio
async def test_get_score_returns_200_with_schema() -> None:
    """Endpoint returns 200 and correct schema when a score exists."""
    mock_score = {
        "company_id": 1,
        "company_name": "Shopify Inc.",
        "scored_at": "2026-03-23T10:00:00+00:00",
        "scores": {"ma": {"30d": 0.71, "60d": 0.84, "90d": 0.89}},
        "velocity_score": 0.34,
        "anomaly_score": 0.08,
        "confidence": {"low": 0.67, "high": 0.91},
        "top_signals": [],
        "model_versions": {"ma": "bayesian_v1"},
    }

    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock) as mock_get,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_get.return_value = mock_score
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/1",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == 1
    assert "scores" in data
    assert "velocity_score" in data
    assert "anomaly_score" in data
    assert "confidence" in data
    assert "model_versions" in data


# ── 2. GET /api/v1/scores/{id} — 404 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_score_returns_404_when_no_score() -> None:
    """Endpoint returns 404 when no score exists for the company."""
    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock) as mock_get,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_get.return_value = None
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/99999",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 404
    assert "99999" in response.json().get("detail", "")


# ── 3. GET /api/v1/scores/{id} — 401 without token ───────────────────────────


@pytest.mark.asyncio
async def test_get_score_requires_auth() -> None:
    """Score endpoint returns 401/403 without a token."""
    status = await _get_no_auth("/api/v1/scores/1")
    assert status in (401, 403)


# ── 4. GET /api/v1/scores/{id}/explain — 200 ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_explain_returns_200() -> None:
    """Explain endpoint returns 200 with explanation list."""
    mock_explain = [
        {
            "practice_area": "ma",
            "horizon": 30,
            "score": 0.71,
            "top_shap_features": [{"feature": "signal_count", "shap_value": 0.3}],
            "counterfactuals": [],
            "base_value": 0.5,
            "explained_at": "2026-03-23T10:00:00",
        }
    ]

    with (
        patch("app.routes.scores.get_company_explain", new_callable=AsyncMock) as mock_exp,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_exp.return_value = mock_explain
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/1/explain",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "practice_area" in data[0]
        assert "score" in data[0]


# ── 5. POST /api/v1/scores/batch — 200 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_scores_returns_200() -> None:
    """Batch endpoint returns a list for valid input."""
    with (
        patch("app.routes.scores.get_batch_scores", new_callable=AsyncMock) as mock_batch,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_batch.return_value = [None, None, None]
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scores/batch",
                json={"company_ids": [1, 2, 3]},
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 3


# ── 6. POST /api/v1/scores/batch — 422 for >50 ids ───────────────────────────


@pytest.mark.asyncio
async def test_batch_scores_rejects_over_50_ids() -> None:
    """Batch endpoint returns 422 when more than 50 company_ids are provided."""
    with (
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scores/batch",
                json={"company_ids": list(range(1, 52))},  # 51 ids
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 422


# ── 7. GET /api/v1/companies/search — returns list ───────────────────────────


@pytest.mark.asyncio
async def test_company_search_returns_list() -> None:
    """Company search returns a list (may be empty without real DB)."""
    with (
        patch("app.routes.companies.cache") as mock_cache,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        # Patch the DB execute to return empty
        with patch("app.routes.companies.get_db") as mock_db_dep:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.mappings.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db_dep.return_value = mock_session

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/v1/companies/search?q=shopify",
                    headers={"Authorization": "Bearer testtoken"},
                )

    assert response.status_code in (200, 503)  # 503 if rapidfuzz not installed
    if response.status_code == 200:
        assert isinstance(response.json(), list)


# ── 8. GET /api/v1/companies/{id} — 404 for unknown ──────────────────────────


@pytest.mark.asyncio
async def test_get_company_returns_404_for_unknown() -> None:
    """Company detail endpoint returns 404 for non-existent company."""
    with (
        patch("app.routes.companies.cache") as mock_cache,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
        patch("app.routes.companies.get_db") as mock_db_dep,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_user.return_value = MagicMock(is_active=True, role="partner")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_dep.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/companies/99999",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 404


# ── 9. GET /api/v1/signals/{id} — 200 + list ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_signals_returns_200() -> None:
    """Signals endpoint returns 200 with a list."""
    with (
        patch("app.routes.signals.get_db") as mock_db_dep,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_user.return_value = MagicMock(is_active=True, role="partner")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_dep.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/signals/1",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── 10. GET /api/v1/trends/practice_areas — 200 + list ───────────────────────


@pytest.mark.asyncio
async def test_trends_returns_200() -> None:
    """Trends endpoint returns 200 with a list."""
    with (
        patch("app.routes.trends.cache") as mock_cache,
        patch("app.routes.trends.get_db") as mock_db_dep,
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock) as mock_user,
    ):
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_user.return_value = MagicMock(is_active=True, role="partner")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db_dep.return_value = mock_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trends/practice_areas",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── 11. GET /api/health — includes ml_ready ──────────────────────────────────


@pytest.mark.asyncio
async def test_health_includes_ml_ready() -> None:
    """Health endpoint must include ml_ready field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert "ml_ready" in data
    assert isinstance(data["ml_ready"], bool)
    assert "ml" in data["components"]


# ── 12. score_company_batch — bulk path ──────────────────────────────────────


@pytest.mark.asyncio
async def test_score_company_batch_uses_bulk_select() -> None:
    """score_company_batch performs one bulk SELECT (not N per-company SELECTs)."""
    import asyncio

    from app.tasks.phase6_tasks import score_company_batch

    mock_feat_row_1 = {"company_id": 1, "feature_date": "2026-03-23", "signal_count": 5}
    mock_feat_row_2 = {"company_id": 2, "feature_date": "2026-03-23", "signal_count": 3}

    mock_horizon_scores = {
        "ma": MagicMock(
            as_dict=lambda: {"30d": 0.7, "60d": 0.8, "90d": 0.85},
            score_30d=0.7,
            model_version="bayesian_v1",
        ),
    }

    with (
        patch("app.tasks.phase6_tasks.get_orchestrator") as mock_orch_fn,
        patch("app.tasks.phase6_tasks.aggregate_company_velocity", return_value=0.3),
        patch("app.tasks.phase6_tasks.get_anomaly_detector") as mock_anom_fn,
        patch("app.tasks.phase6_tasks.get_db") as mock_db_fn,
    ):
        mock_orchestrator = MagicMock()
        mock_orchestrator._loaded = True
        mock_orchestrator.score_company.return_value = mock_horizon_scores
        mock_orch_fn.return_value = mock_orchestrator

        mock_anomaly = MagicMock()
        mock_anomaly.score.return_value = 0.05
        mock_anom_fn.return_value = mock_anomaly

        # Build mock DB session
        mock_session = AsyncMock()
        mock_feat_result = MagicMock()
        mock_feat_result.mappings.return_value = [mock_feat_row_1, mock_feat_row_2]
        mock_insert_result = MagicMock()
        mock_session.execute = AsyncMock(side_effect=[mock_feat_result, mock_insert_result])
        mock_session.commit = AsyncMock()

        # Make get_db() an async context manager
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_db_fn.return_value = mock_ctx

        # Run the task synchronously via asyncio
        task_fn = (
            score_company_batch.__wrapped__
            if hasattr(score_company_batch, "__wrapped__")
            else score_company_batch
        )
        result = asyncio.run(task_fn.__func__(MagicMock(), [1, 2]))  # type: ignore[attr-defined]

    # Should have called execute exactly twice: bulk SELECT + bulk INSERT
    assert mock_session.execute.call_count == 2
    assert result["total"] == 2


# ── 13. score_company_batch — missing features ───────────────────────────────


def test_score_company_batch_handles_missing_features() -> None:
    """score_company_batch increments failed count when features are missing."""
    import asyncio

    from app.tasks.phase6_tasks import score_company_batch

    with (
        patch("app.tasks.phase6_tasks.get_orchestrator") as mock_orch_fn,
        patch("app.tasks.phase6_tasks.get_db") as mock_db_fn,
    ):
        mock_orchestrator = MagicMock()
        mock_orchestrator._loaded = True
        mock_orch_fn.return_value = mock_orchestrator

        mock_session = AsyncMock()
        # Return empty feature map (no rows)
        mock_feat_result = MagicMock()
        mock_feat_result.mappings.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_feat_result)
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_db_fn.return_value = mock_ctx

        task_fn = (
            score_company_batch.__wrapped__
            if hasattr(score_company_batch, "__wrapped__")
            else score_company_batch
        )
        result = asyncio.run(task_fn.__func__(MagicMock(), [42, 43]))  # type: ignore[attr-defined]

    assert result["failed"] == 2
    assert result["scored"] == 0


# ── 14. invalidate_score_cache — deletes correct key ─────────────────────────


@pytest.mark.asyncio
async def test_invalidate_score_cache_deletes_correct_key() -> None:
    """invalidate_score_cache deletes the key for today's date."""
    from datetime import datetime

    from app.services.scoring_service import invalidate_score_cache

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    expected_key = f"score:7:{today}"

    with patch("app.services.scoring_service.cache") as mock_cache:
        mock_cache.delete = AsyncMock(return_value=True)
        await invalidate_score_cache(7)

    mock_cache.delete.assert_called_once_with(expected_key)


# ── 15. GET /api/v1/companies/search — 401 without token ─────────────────────


@pytest.mark.asyncio
async def test_company_search_requires_auth() -> None:
    """Company search endpoint returns 401/403 without a token."""
    status = await _get_no_auth("/api/v1/companies/search?q=shopify")
    assert status in (401, 403)
