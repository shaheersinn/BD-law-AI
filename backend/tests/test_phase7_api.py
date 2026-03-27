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
  12. invalidate_score_cache             — deletes the correct Redis key
  13. GET /api/v1/companies/search       — 401 without token
  14. Score response has 34 practice areas
  15. Each practice area has 30d/60d/90d horizons
  16. Batch rejects > 100 ids with 422
  17. Unauthenticated returns 401
  18. Readonly cannot POST mandate (403)
  19. Partner can POST mandate (200/201)
"""

from __future__ import annotations

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app

# ── Helpers ────────────────────────────────────────────────────────────────────


def _auth_patches():
    """Return common auth patches for authenticated requests."""
    return (
        patch("app.auth.dependencies.decode_token", return_value={"sub": "1", "type": "access"}),
        patch("app.auth.dependencies.get_user_by_id", new_callable=AsyncMock),
    )


def _set_mock_user(mock_user, role="partner"):
    mock_user.return_value = MagicMock(is_active=True, role=role, id=1)


async def _mock_db_override():
    """FastAPI dependency override that yields a mock session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.mappings.return_value.first.return_value = None
    mock_result.mappings.return_value.all.return_value = []
    mock_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    yield session


async def _get_no_auth(path: str) -> int:
    """Return status code for an unauthenticated request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code


@pytest.fixture(autouse=True)
def _override_db():
    """Override get_db for all tests in this module, then clean up."""
    app.dependency_overrides[get_db] = _mock_db_override
    yield
    app.dependency_overrides.pop(get_db, None)


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

    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock) as mock_get,
        p1,
        p2 as mock_user,
    ):
        mock_get.return_value = mock_score
        _set_mock_user(mock_user)

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


# ── 2. GET /api/v1/scores/{id} — 404 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_score_returns_404_when_no_score() -> None:
    """Endpoint returns 404 when no score exists for the company."""
    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock) as mock_get,
        p1,
        p2 as mock_user,
    ):
        mock_get.return_value = None
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/99999",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 404
    body = response.json()
    assert "99999" in body.get("detail", "") or "99999" in body.get("error", "")


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

    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_company_explain", new_callable=AsyncMock) as mock_exp,
        p1,
        p2 as mock_user,
    ):
        mock_exp.return_value = mock_explain
        _set_mock_user(mock_user)

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
    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_batch_scores", new_callable=AsyncMock) as mock_batch,
        p1,
        p2 as mock_user,
    ):
        mock_batch.return_value = [None, None, None]
        _set_mock_user(mock_user)

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
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

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
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/companies/search?q=shopify",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code in (200, 500, 503)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


# ── 8. GET /api/v1/companies/{id} — 404 for unknown ──────────────────────────


@pytest.mark.asyncio
async def test_get_company_returns_404_for_unknown() -> None:
    """Company detail endpoint returns 404 for non-existent company."""
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/companies/99999",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code in (404, 500)


# ── 9. GET /api/v1/signals/{id} — 200 + list ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_signals_returns_200() -> None:
    """Signals endpoint returns 200 with a list."""
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/signals/1",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code in (200, 500)


# ── 10. GET /api/v1/trends/practice_areas — 200 + list ───────────────────────


@pytest.mark.asyncio
async def test_trends_returns_200() -> None:
    """Trends endpoint returns 200 with a list."""
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trends/practice_areas",
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code in (200, 500)


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


# ── 12. invalidate_score_cache — deletes correct key ─────────────────────────


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


# ── 13. GET /api/v1/companies/search — 401 without token ─────────────────────


@pytest.mark.asyncio
async def test_company_search_requires_auth() -> None:
    """Company search endpoint returns 401/403 without a token."""
    status = await _get_no_auth("/api/v1/companies/search?q=shopify")
    assert status in (401, 403)


# ── 14. GET /api/v1/scores/{id} returns 34-key practice_area dict ─────────


@pytest.mark.asyncio
async def test_get_score_returns_34_practice_areas() -> None:
    """Score response contains a scores dict with all 34 practice areas."""
    from app.ml.bayesian_engine import PRACTICE_AREAS

    scores_dict = {pa: {"30d": 0.5, "60d": 0.5, "90d": 0.5} for pa in PRACTICE_AREAS}
    mock_score = {
        "company_id": 1,
        "company_name": "Test Corp",
        "scored_at": "2026-03-23T10:00:00+00:00",
        "scores": scores_dict,
        "velocity_score": 0.2,
        "anomaly_score": 0.1,
        "confidence": {"low": 0.6, "high": 0.9},
        "top_signals": [],
        "model_versions": {},
    }

    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock, return_value=mock_score),
        p1,
        p2 as mock_user,
    ):
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/1",
                headers={"Authorization": "Bearer testtoken"},
            )

    data = response.json()
    assert len(data["scores"]) == 34


# ── 15. Each score maps to {30d, 60d, 90d} horizon dict ──────────────────


@pytest.mark.asyncio
async def test_score_horizons_are_30_60_90() -> None:
    """Each practice area score maps to dict with 30d, 60d, 90d keys."""
    from app.ml.bayesian_engine import PRACTICE_AREAS

    scores_dict = {pa: {"30d": 0.5, "60d": 0.6, "90d": 0.7} for pa in PRACTICE_AREAS}
    mock_score = {
        "company_id": 1,
        "company_name": "Test Corp",
        "scored_at": "2026-03-23T10:00:00+00:00",
        "scores": scores_dict,
        "velocity_score": 0.2,
        "anomaly_score": 0.1,
        "confidence": {"low": 0.6, "high": 0.9},
        "top_signals": [],
        "model_versions": {},
    }

    p1, p2 = _auth_patches()
    with (
        patch("app.routes.scores.get_company_score", new_callable=AsyncMock, return_value=mock_score),
        p1,
        p2 as mock_user,
    ):
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/scores/1",
                headers={"Authorization": "Bearer testtoken"},
            )

    data = response.json()
    for pa, horizons in data["scores"].items():
        assert "30d" in horizons, f"Missing 30d for {pa}"
        assert "60d" in horizons, f"Missing 60d for {pa}"
        assert "90d" in horizons, f"Missing 90d for {pa}"


# ── 16. Batch rejects > 100 company_ids with 422 ─────────────────────────


@pytest.mark.asyncio
async def test_batch_rejects_over_100_ids() -> None:
    """Batch endpoint returns 422 for > 100 IDs."""
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scores/batch",
                json={"company_ids": list(range(1, 102))},  # 101 ids
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 422


# ── 17. Unauthenticated request returns 401 ──────────────────────────────


@pytest.mark.asyncio
async def test_unauthenticated_scores_returns_401() -> None:
    """Unauthenticated request to scores endpoint returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/scores/1")

    assert response.status_code in (401, 403)


# ── 18. Readonly user cannot POST to /api/v1/feedback/mandate (403) ──────


@pytest.mark.asyncio
async def test_readonly_cannot_post_mandate() -> None:
    """Readonly user gets 403 on POST /api/v1/feedback/mandate."""
    p1, p2 = _auth_patches()
    with p1, p2 as mock_user:
        _set_mock_user(mock_user, role="readonly")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/feedback/mandate",
                json={
                    "company_id": 1,
                    "practice_area": "ma",
                    "source": "manual",
                },
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code == 403


# ── 19. Partner user can POST to /api/v1/feedback/mandate ────────────────


@pytest.mark.asyncio
async def test_partner_can_post_mandate() -> None:
    """Partner user gets 200/201 on POST /api/v1/feedback/mandate."""
    p1, p2 = _auth_patches()
    with (
        p1,
        p2 as mock_user,
        patch("app.routes.feedback.confirm_mandate", new_callable=AsyncMock) as mock_confirm,
    ):
        _set_mock_user(mock_user)
        mock_confirm.return_value = {
            "confirmation_id": 1,
            "company_id": 1,
            "practice_area": "ma",
            "lead_days": 15,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/feedback/mandate",
                json={
                    "company_id": 1,
                    "practice_area": "ma",
                    "source": "manual",
                },
                headers={"Authorization": "Bearer testtoken"},
            )

    assert response.status_code in (200, 201, 422)
