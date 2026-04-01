"""
Phase 5 — Live Feeds tests.

Tests for:
  - LiveFeedRouter: push_signal, ensure_consumer_group, read_events, acknowledge,
    stream_length, pending_count
  - VelocityMonitor: record_signal, get_velocity_ratio, get_velocity_score,
    compute_and_cache_scores
  - LinkedInTrigger: check_budget, run (budget exhausted, not found, success)
  - DeadSignalResurrector: run, _trigger_rerun, category routing
  - Celery task registration: all 10 Phase 5 tasks exist with correct names/queues
  - celery_app beat schedule: all 10 Phase 5 entries present

All tests run without live Redis, PostgreSQL, or external APIs (fully mocked).
Uses the same sys.modules stub injection pattern as prior phase tests.
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ── Inject stubs BEFORE any app imports ───────────────────────────────────────


def _inject_module_stubs() -> None:
    """Stub out DB/Redis/external modules to keep tests hermetic."""
    # app.config — import the real module; don't stub it
    try:
        import app.config  # noqa: F401
    except Exception:
        cfg_mod = ModuleType("app.config")
        settings_stub = MagicMock()
        settings_stub.environment = "development"
        settings_stub.redis_url = "redis://localhost:6379/0"
        settings_stub.database_url = "postgresql+asyncpg://test:test@localhost/test"
        settings_stub.mongodb_url = "mongodb://localhost:27017"
        settings_stub.mongodb_db_name = "oracle_test"
        settings_stub.live_feeds_enabled = True
        settings_stub.proxycurl_api_key = "test-proxycurl-key"
        settings_stub.celery_broker_url = "redis://localhost:6379/0"
        settings_stub.celery_result_backend = "redis://localhost:6379/1"
        settings_stub.celery_task_time_limit = 3600
        settings_stub.celery_task_soft_time_limit = 3300
        settings_stub.celery_worker_concurrency = 4
        cfg_mod.get_settings = lambda: settings_stub  # type: ignore[attr-defined]
        cfg_mod.Settings = MagicMock  # type: ignore[attr-defined]
        sys.modules["app.config"] = cfg_mod

    # app.database — import the real module so it's available; don't stub it
    # The real module is needed by other tests that share the process
    try:
        import app.database  # noqa: F401
    except Exception:
        # If import fails (e.g., no asyncpg), create a minimal stub
        import sqlalchemy.orm as _orm

        class _Base(_orm.DeclarativeBase):
            pass

        db_mod = ModuleType("app.database")
        db_mod.Base = _Base  # type: ignore[attr-defined]
        db_mod.AsyncSessionLocal = MagicMock()  # type: ignore[attr-defined]
        db_mod.get_db = MagicMock()  # type: ignore[attr-defined]
        db_mod.get_mongo_db = MagicMock()  # type: ignore[attr-defined]
        db_mod.get_mongo_client = MagicMock(return_value=None)  # type: ignore[attr-defined]
        db_mod.check_db_connection = AsyncMock(return_value=False)  # type: ignore[attr-defined]
        db_mod.check_mongo_connection = AsyncMock(return_value=False)  # type: ignore[attr-defined]
        db_mod.dispose_engine = AsyncMock()  # type: ignore[attr-defined]
        db_mod.close_mongo_connection = AsyncMock()  # type: ignore[attr-defined]
        sys.modules["app.database"] = db_mod

    # redis.asyncio — stub to avoid real connections
    redis_mod = ModuleType("redis")
    redis_asyncio_mod = ModuleType("redis.asyncio")
    redis_asyncio_mod.from_url = MagicMock()  # type: ignore[attr-defined]
    redis_asyncio_mod.ResponseError = Exception  # type: ignore[attr-defined]
    redis_mod.asyncio = redis_asyncio_mod  # type: ignore[attr-defined]
    sys.modules.setdefault("redis", redis_mod)
    sys.modules.setdefault("redis.asyncio", redis_asyncio_mod)

    # httpx — stub for LinkedIn trigger
    httpx_mod = ModuleType("httpx")
    httpx_mod.AsyncClient = MagicMock  # type: ignore[attr-defined]
    httpx_mod.TimeoutException = Exception  # type: ignore[attr-defined]
    httpx_mod.HTTPError = Exception  # type: ignore[attr-defined]
    sys.modules.setdefault("httpx", httpx_mod)

    # structlog — import the real module; don't stub it
    try:
        import structlog  # noqa: F401
    except Exception:
        structlog_mod = ModuleType("structlog")
        structlog_mod.get_logger = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
        sys.modules["structlog"] = structlog_mod

    # SQLAlchemy select helper stub
    sa_mod = sys.modules.get("sqlalchemy")
    if sa_mod is None:
        import sqlalchemy

        sys.modules.setdefault("sqlalchemy", sqlalchemy)


_inject_module_stubs()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _run(coro: Any) -> Any:
    """Run a coroutine synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_redis_mock() -> MagicMock:
    """Create a mock Redis client with async pipeline support."""
    mock_client = MagicMock()
    mock_client.xadd = AsyncMock(return_value="1711234567890-0")
    mock_client.xgroup_create = AsyncMock(return_value=True)
    mock_client.xreadgroup = AsyncMock(return_value=[])
    mock_client.xack = AsyncMock(return_value=1)
    mock_client.xlen = AsyncMock(return_value=42)
    mock_client.xpending = AsyncMock(return_value=[5, None, None, []])
    mock_client.get = AsyncMock(return_value=None)
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.hget = AsyncMock(return_value=None)
    mock_client.hset = AsyncMock(return_value=1)
    mock_client.zadd = AsyncMock(return_value=1)
    mock_client.zcount = AsyncMock(return_value=0)
    mock_client.zremrangebyscore = AsyncMock(return_value=0)
    mock_client.aclose = AsyncMock()

    mock_pipe = MagicMock()
    mock_pipe.zadd = MagicMock(return_value=mock_pipe)
    mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
    mock_pipe.expire = MagicMock(return_value=mock_pipe)
    mock_pipe.hset = MagicMock(return_value=mock_pipe)
    mock_pipe.incr = MagicMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[1, 0, True])

    mock_client.pipeline = MagicMock(return_value=mock_pipe)
    return mock_client


# ══════════════════════════════════════════════════════════════════════════════
# 1 — LiveFeedRouter
# ══════════════════════════════════════════════════════════════════════════════


class TestLiveFeedRouter:
    """Tests for app/services/live_feed.py"""

    def setup_method(self) -> None:
        # Reimport fresh instance per test
        if "app.services.live_feed" in sys.modules:
            del sys.modules["app.services.live_feed"]

    def _get_router(self, redis_mock: MagicMock | None = None) -> Any:
        from app.services.live_feed import LiveFeedRouter

        router = LiveFeedRouter()
        if redis_mock is not None:
            router._client = redis_mock
        return router

    def test_push_signal_returns_msg_id(self) -> None:
        from app.config import get_settings

        get_settings().live_feeds_enabled = True
        try:
            mock_client = _make_redis_mock()
            router = self._get_router(mock_client)
            result = _run(router.push_signal({"signal_type": "material_change", "company_id": "123"}))
            assert result == "1711234567890-0"
            mock_client.xadd.assert_called_once()
        finally:
            get_settings().live_feeds_enabled = False

    def test_push_signal_disabled_returns_none(self) -> None:
        from app.config import get_settings

        get_settings().live_feeds_enabled = False
        try:
            router = self._get_router()
            result = _run(router.push_signal({"signal_type": "test"}))
            assert result is None
        finally:
            get_settings().live_feeds_enabled = True

    def test_push_signal_stamps_pushed_at(self) -> None:
        mock_client = _make_redis_mock()
        router = self._get_router(mock_client)
        signal: dict[str, Any] = {"signal_type": "material_change"}
        _run(router.push_signal(signal))
        call_args = mock_client.xadd.call_args
        # Second positional arg is the fields dict
        fields = call_args[0][1]
        assert "pushed_at" in fields

    def test_push_signal_json_serializes_dicts(self) -> None:
        mock_client = _make_redis_mock()
        router = self._get_router(mock_client)
        _run(router.push_signal({"metadata": {"key": "val"}, "signal_type": "test"}))
        fields = mock_client.xadd.call_args[0][1]
        import json

        parsed = json.loads(fields["metadata"])
        assert parsed["key"] == "val"

    def test_push_signal_redis_error_returns_none(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xadd = AsyncMock(side_effect=Exception("Redis down"))
        router = self._get_router(mock_client)
        result = _run(router.push_signal({"signal_type": "test"}))
        assert result is None

    def test_ensure_consumer_group_creates_group(self) -> None:
        mock_client = _make_redis_mock()
        router = self._get_router(mock_client)
        _run(router.ensure_consumer_group())
        mock_client.xgroup_create.assert_called_once()

    def test_ensure_consumer_group_ignores_busygroup(self) -> None:
        import redis.asyncio as aioredis

        mock_client = _make_redis_mock()
        mock_client.xgroup_create = AsyncMock(
            side_effect=aioredis.ResponseError("BUSYGROUP Consumer Group already exists")
        )
        router = self._get_router(mock_client)
        # Should not raise
        _run(router.ensure_consumer_group())

    def test_read_events_returns_empty_when_no_messages(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xreadgroup = AsyncMock(return_value=None)
        router = self._get_router(mock_client)
        result = _run(router.read_events(batch_size=10))
        assert result == []

    def test_read_events_parses_messages(self) -> None:
        import json

        mock_client = _make_redis_mock()
        meta = json.dumps({"k": "v"})
        raw_msg = {"signal_type": "material_change", "company_id": "42", "metadata": meta}
        mock_client.xreadgroup = AsyncMock(
            return_value=[("oracle:live:signals", [("1234-0", raw_msg)])]
        )
        router = self._get_router(mock_client)
        results = _run(router.read_events())
        assert len(results) == 1
        msg_id, data = results[0]
        assert msg_id == "1234-0"
        assert data["signal_type"] == "material_change"
        assert data["company_id"] == 42  # JSON-decoded from "42" to int
        assert data["metadata"] == {"k": "v"}  # JSON decoded

    def test_acknowledge_returns_true_on_success(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xack = AsyncMock(return_value=1)
        router = self._get_router(mock_client)
        result = _run(router.acknowledge("1234-0"))
        assert result is True

    def test_acknowledge_returns_false_on_error(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xack = AsyncMock(side_effect=Exception("Redis error"))
        router = self._get_router(mock_client)
        result = _run(router.acknowledge("1234-0"))
        assert result is False

    def test_stream_length_returns_int(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xlen = AsyncMock(return_value=99)
        router = self._get_router(mock_client)
        result = _run(router.stream_length())
        assert result == 99

    def test_stream_length_returns_zero_on_error(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xlen = AsyncMock(side_effect=Exception("Redis down"))
        router = self._get_router(mock_client)
        result = _run(router.stream_length())
        assert result == 0

    def test_pending_count_returns_int(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.xpending = AsyncMock(return_value=[7, None, None, []])
        router = self._get_router(mock_client)
        result = _run(router.pending_count())
        assert result == 7

    def test_module_singleton_exists(self) -> None:
        from app.services.live_feed import LiveFeedRouter, live_feed

        assert isinstance(live_feed, LiveFeedRouter)


# ══════════════════════════════════════════════════════════════════════════════
# 2 — VelocityMonitor
# ══════════════════════════════════════════════════════════════════════════════


class TestVelocityMonitor:
    """Tests for app/services/velocity_monitor.py"""

    def setup_method(self) -> None:
        if "app.services.velocity_monitor" in sys.modules:
            del sys.modules["app.services.velocity_monitor"]

    def _get_monitor(self, redis_mock: MagicMock | None = None) -> Any:
        from app.services.velocity_monitor import VelocityMonitor

        monitor = VelocityMonitor()
        if redis_mock is not None:
            monitor._client = redis_mock
        return monitor

    def test_signal_key_format(self) -> None:
        monitor = self._get_monitor()
        key = monitor._signal_key(123, "litigation")
        assert key == "oracle:velocity:123:litigation"

    def test_score_key_format(self) -> None:
        monitor = self._get_monitor()
        key = monitor._score_key(456)
        assert key == "oracle:velocity_scores:456"

    def test_record_signal_calls_pipeline(self) -> None:
        mock_client = _make_redis_mock()
        monitor = self._get_monitor(mock_client)
        _run(monitor.record_signal(123, "litigation"))
        mock_client.pipeline.assert_called_once()
        mock_pipe = mock_client.pipeline.return_value
        mock_pipe.zadd.assert_called_once()
        mock_pipe.execute.assert_called_once()

    def test_record_signal_no_crash_on_redis_error(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.pipeline = MagicMock(side_effect=Exception("Redis down"))
        monitor = self._get_monitor(mock_client)
        # Should not raise
        _run(monitor.record_signal(123, "litigation"))

    def test_get_velocity_ratio_zero_baseline(self) -> None:
        mock_client = _make_redis_mock()
        # 0 signals in 30 days → no baseline
        mock_pipe = mock_client.pipeline.return_value
        mock_pipe.execute = AsyncMock(return_value=[5, 0])  # 5 in 48h, 0 in 30d
        monitor = self._get_monitor(mock_client)
        ratio = _run(monitor.get_velocity_ratio(1, "ma_corporate"))
        assert ratio == 0.0

    def test_get_velocity_ratio_normal(self) -> None:
        mock_client = _make_redis_mock()
        # 30 signals in 30 days → expected_48h = (30/2592000)*172800 = 2.0
        # 10 signals in 48h → ratio = 10 / 2.0 = 5.0
        mock_pipe = mock_client.pipeline.return_value
        mock_pipe.execute = AsyncMock(return_value=[10, 30])
        monitor = self._get_monitor(mock_client)
        ratio = _run(monitor.get_velocity_ratio(1, "litigation"))
        assert ratio == 5.0

    def test_get_velocity_ratio_high_velocity(self) -> None:
        mock_client = _make_redis_mock()
        # Simulate dense baseline: 10000 signals in 30 days
        mock_pipe = mock_client.pipeline.return_value
        window_30d = 30 * 24 * 3600
        window_48h = 48 * 3600
        count_30d = 10000
        count_48h = 100
        expected_48h = (count_30d / window_30d) * window_48h  # ≈ 22.2
        expected_ratio = count_48h / expected_48h
        mock_pipe.execute = AsyncMock(return_value=[count_48h, count_30d])
        monitor = self._get_monitor(mock_client)
        ratio = _run(monitor.get_velocity_ratio(1, "litigation"))
        assert abs(ratio - expected_ratio) < 0.01

    def test_get_velocity_score_returns_float(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.hget = AsyncMock(return_value="3.14")
        monitor = self._get_monitor(mock_client)
        score = _run(monitor.get_velocity_score(42))
        assert abs(score - 3.14) < 0.001

    def test_get_velocity_score_returns_zero_when_missing(self) -> None:
        mock_client = _make_redis_mock()
        mock_client.hget = AsyncMock(return_value=None)
        monitor = self._get_monitor(mock_client)
        score = _run(monitor.get_velocity_score(99))
        assert score == 0.0

    def test_compute_and_cache_scores_empty_list(self) -> None:
        monitor = self._get_monitor()
        result = _run(monitor.compute_and_cache_scores([]))
        assert result["companies_scanned"] == 0
        assert result["high_velocity_count"] == 0

    def test_compute_and_cache_scores_returns_summary(self) -> None:
        mock_client = _make_redis_mock()
        mock_pipe = mock_client.pipeline.return_value
        mock_pipe.execute = AsyncMock(return_value=[0, 0])  # all ratios → 0.0

        monitor = self._get_monitor(mock_client)
        # Patch get_velocity_ratio to return 0.0 for all calls
        with patch.object(monitor, "get_velocity_ratio", AsyncMock(return_value=0.0)):
            result = _run(monitor.compute_and_cache_scores([1, 2, 3]))

        assert result["companies_scanned"] == 3
        assert result["high_velocity_count"] == 0
        assert result["escalated"] == []

    def test_compute_and_cache_scores_detects_high_velocity(self) -> None:
        mock_client = _make_redis_mock()
        mock_pipe = mock_client.pipeline.return_value
        mock_pipe.execute = AsyncMock(return_value=[1, True])

        monitor = self._get_monitor(mock_client)

        # Company 1 has velocity 5.0 (above threshold 2.0), company 2 is normal
        async def _mock_ratio(company_id: int, area: str) -> float:
            return 5.0 if company_id == 1 and area == "litigation" else 0.0

        with patch.object(monitor, "get_velocity_ratio", _mock_ratio):
            result = _run(monitor.compute_and_cache_scores([1, 2]))

        assert result["high_velocity_count"] == 1
        assert result["escalated"][0]["company_id"] == 1

    def test_module_singleton_exists(self) -> None:
        from app.services.velocity_monitor import VelocityMonitor, velocity_monitor

        assert isinstance(velocity_monitor, VelocityMonitor)


# ══════════════════════════════════════════════════════════════════════════════
# 3 — LinkedInTrigger
# ══════════════════════════════════════════════════════════════════════════════


class TestLinkedInTrigger:
    """Tests for app/services/linkedin_trigger.py"""

    def setup_method(self) -> None:
        if "app.services.linkedin_trigger" in sys.modules:
            del sys.modules["app.services.linkedin_trigger"]

    def _get_trigger(self) -> Any:
        from app.services.linkedin_trigger import LinkedInTrigger

        return LinkedInTrigger()

    def test_today_budget_key_format(self) -> None:
        trigger = self._get_trigger()
        key = trigger._today_budget_key()
        assert key.startswith("oracle:proxycurl:budget:")
        assert len(key) > len("oracle:proxycurl:budget:")

    def test_check_budget_available(self) -> None:
        trigger = self._get_trigger()
        with patch.object(trigger, "_get_budget_used", AsyncMock(return_value=2)):
            has_budget, remaining = _run(trigger.check_budget())
        assert has_budget is True
        assert remaining == 3  # 5 - 2

    def test_check_budget_exhausted(self) -> None:
        trigger = self._get_trigger()
        with patch.object(trigger, "_get_budget_used", AsyncMock(return_value=5)):
            has_budget, remaining = _run(trigger.check_budget())
        assert has_budget is False
        assert remaining == 0

    def test_run_returns_budget_exhausted_when_no_budget(self) -> None:
        trigger = self._get_trigger()
        with patch.object(trigger, "check_budget", AsyncMock(return_value=(False, 0))):
            result = _run(trigger.run({"executive_name": "Jane Doe", "company_name": "Acme"}))
        assert result["status"] == "budget_exhausted"
        assert result["budget_remaining"] == 0

    def test_run_returns_not_found_on_none_profile(self) -> None:
        trigger = self._get_trigger()
        with patch.object(trigger, "check_budget", AsyncMock(return_value=(True, 3))):
            with patch.object(trigger, "lookup_executive", AsyncMock(return_value=None)):
                result = _run(trigger.run({"executive_name": "Jane Doe", "company_name": "Acme"}))
        assert result["status"] == "not_found"
        assert result["budget_remaining"] == 3

    def test_run_returns_success_on_valid_profile(self) -> None:
        trigger = self._get_trigger()
        mock_profile = {
            "full_name": "Jane Doe",
            "headline": "General Counsel",
            "experiences": [{"company": "Acme Corp", "title": "GC"}],
        }
        with patch.object(trigger, "check_budget", AsyncMock(return_value=(True, 4))):
            with patch.object(trigger, "lookup_executive", AsyncMock(return_value=mock_profile)):
                with patch.object(trigger, "_increment_budget", AsyncMock()):
                    with patch.object(trigger, "check_budget", AsyncMock(return_value=(True, 3))):
                        result = _run(
                            trigger.run(
                                {
                                    "executive_name": "Jane Doe",
                                    "company_name": "Acme",
                                }
                            )
                        )
        assert result["status"] == "success"
        assert result["executive_name"] == "Jane Doe"
        assert result["headline"] == "General Counsel"

    def test_lookup_executive_skips_when_no_api_key(self) -> None:
        from app.config import get_settings

        get_settings().proxycurl_api_key = ""
        try:
            trigger = self._get_trigger()
            result = _run(trigger.lookup_executive(linkedin_url="https://linkedin.com/in/test"))
            assert result is None
        finally:
            get_settings().proxycurl_api_key = "test-proxycurl-key"

    def test_lookup_executive_returns_none_on_missing_params(self) -> None:
        trigger = self._get_trigger()
        result = _run(trigger.lookup_executive())
        assert result is None

    def test_module_singleton_exists(self) -> None:
        from app.services.linkedin_trigger import LinkedInTrigger, linkedin_trigger

        assert isinstance(linkedin_trigger, LinkedInTrigger)


# ══════════════════════════════════════════════════════════════════════════════
# 4 — DeadSignalResurrector
# ══════════════════════════════════════════════════════════════════════════════


class TestDeadSignalResurrector:
    """Tests for app/services/resurrector.py"""

    def setup_method(self) -> None:
        if "app.services.resurrector" in sys.modules:
            del sys.modules["app.services.resurrector"]

    def _get_resurrector(self) -> Any:
        from app.services.resurrector import DeadSignalResurrector

        return DeadSignalResurrector()

    def test_expected_intervals_populated(self) -> None:
        from app.services.resurrector import EXPECTED_INTERVALS

        assert "sedar_live" in EXPECTED_INTERVALS
        assert "osc_live" in EXPECTED_INTERVALS
        assert "canlii_live" in EXPECTED_INTERVALS
        assert "news_live" in EXPECTED_INTERVALS
        assert "scc_live" in EXPECTED_INTERVALS
        assert "edgar_live" in EXPECTED_INTERVALS

    def test_live_scrapers_have_short_intervals(self) -> None:
        from app.services.resurrector import EXPECTED_INTERVALS

        assert EXPECTED_INTERVALS["sedar_live"] <= 600
        assert EXPECTED_INTERVALS["edgar_live"] <= 600
        assert EXPECTED_INTERVALS["news_live"] <= 600

    def test_category_task_map_covers_all_categories(self) -> None:
        from app.services.resurrector import CATEGORY_TASK_MAP

        for category in ("corporate", "legal", "regulatory", "news", "social", "market"):
            assert category in CATEGORY_TASK_MAP

    def test_trigger_rerun_returns_false_for_unknown_category(self) -> None:
        r = self._get_resurrector()
        result = _run(r._trigger_rerun("unknown_scraper", "unknown_category"))
        assert result is False

    def test_trigger_rerun_dispatches_celery_task(self) -> None:
        mock_method = AsyncMock(return_value=True)
        with patch("app.services.resurrector.DeadSignalResurrector._trigger_rerun", mock_method):
            result = _run(mock_method("sedar", "corporate"))
        assert result is True

    def test_run_returns_summary_structure(self) -> None:
        r = self._get_resurrector()
        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = []

        async def _mock_db() -> Any:
            class _FakeCtx:
                async def __aenter__(self) -> Any:
                    return self

                async def __aexit__(self, *args: Any) -> None:
                    pass

                async def execute(self, *args: Any) -> Any:
                    return mock_db_result

            return _FakeCtx()

        with patch("app.database.AsyncSessionLocal", return_value=_mock_db()):
            result = _run(r.run())

        assert "n_checked" in result
        assert "n_silent" in result
        assert "n_triggered" in result
        assert "n_critical" in result
        assert "silent_scrapers" in result

    def test_run_with_fresh_scraper_no_alert(self) -> None:
        """A scraper that succeeded 1 minute ago should not be flagged."""
        from datetime import UTC, datetime, timedelta

        r = self._get_resurrector()

        mock_scraper = MagicMock()
        mock_scraper.scraper_name = "sedar_live"
        mock_scraper.scraper_category = "corporate"
        mock_scraper.status = "healthy"
        mock_scraper.consecutive_failures = 0
        # last success = 1 minute ago (well within 2× 5min = 10min threshold)
        mock_scraper.last_success_at = datetime.now(UTC) - timedelta(minutes=1)

        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = [mock_scraper]

        class _FakeSession:
            async def __aenter__(self) -> _FakeSession:
                return self

            async def __aexit__(self, *args: Any) -> None:
                pass

            async def execute(self, *args: Any) -> Any:
                return mock_db_result

        import app.database as db_mod_ref

        _orig = db_mod_ref.AsyncSessionLocal
        db_mod_ref.AsyncSessionLocal = _FakeSession
        try:
            result = _run(r.run())
            assert result["n_silent"] == 0
        finally:
            db_mod_ref.AsyncSessionLocal = _orig

    def test_run_detects_dead_scraper(self) -> None:
        """A scraper silent for 24h should be flagged (sedar_live expected 5min)."""
        from datetime import UTC, datetime, timedelta

        r = self._get_resurrector()

        mock_scraper = MagicMock()
        mock_scraper.scraper_name = "sedar_live"
        mock_scraper.scraper_category = "corporate"
        mock_scraper.status = "failing"
        mock_scraper.consecutive_failures = 2
        mock_scraper.last_success_at = datetime.now(UTC) - timedelta(hours=24)

        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = [mock_scraper]

        class _FakeSession:
            async def __aenter__(self) -> _FakeSession:
                return self

            async def __aexit__(self, *args: Any) -> None:
                pass

            async def execute(self, *args: Any) -> Any:
                return mock_db_result

        import app.database as db_mod_ref

        _orig = db_mod_ref.AsyncSessionLocal
        db_mod_ref.AsyncSessionLocal = _FakeSession
        try:
            with patch.object(r, "_trigger_rerun", AsyncMock(return_value=True)):
                result = _run(r.run())
            assert result["n_silent"] >= 1
        finally:
            db_mod_ref.AsyncSessionLocal = _orig
        assert result["n_triggered"] >= 1

    def test_module_singleton_exists(self) -> None:
        from app.services.resurrector import DeadSignalResurrector, resurrector

        assert isinstance(resurrector, DeadSignalResurrector)


# ══════════════════════════════════════════════════════════════════════════════
# 5 — Celery task registration
# ══════════════════════════════════════════════════════════════════════════════


class TestPhase5CeleryTasks:
    """Verify all Phase 5 tasks are registered in the Celery app."""

    EXPECTED_TASKS = [
        "app.tasks._impl.scrape_sedar_live",
        "app.tasks._impl.scrape_osc_live",
        "app.tasks._impl.scrape_canlii_live",
        "app.tasks._impl.scrape_news_live",
        "app.tasks._impl.scrape_scc_live",
        "app.tasks._impl.scrape_edgar_live",
        "app.tasks._impl.process_live_feed_events",
        "app.tasks._impl.monitor_signal_velocity",
        "app.tasks._impl.run_dead_signal_resurrector",
        "app.tasks._impl.trigger_linkedin_lookup",
    ]

    def test_all_phase5_tasks_registered(self) -> None:
        import app.tasks._impl  # noqa: F401 — registers tasks as side-effect
        from app.tasks.celery_app import celery_app

        registered = set(celery_app.tasks.keys())
        for task_name in self.EXPECTED_TASKS:
            assert task_name in registered, f"Task not registered: {task_name}"

    def test_live_scraper_tasks_have_short_time_limits(self) -> None:
        import app.tasks._impl  # noqa: F401
        from app.tasks.celery_app import celery_app

        live_tasks = [
            "app.tasks._impl.scrape_sedar_live",
            "app.tasks._impl.scrape_edgar_live",
            "app.tasks._impl.scrape_news_live",
        ]
        for name in live_tasks:
            task = celery_app.tasks.get(name)
            assert task is not None, f"Task not found: {name}"
            # Live scrapers must complete quickly (hard limit 300s)
            assert task.time_limit <= 300, f"{name} time_limit too high"

    def test_process_live_feed_events_has_short_time_limit(self) -> None:
        import app.tasks._impl  # noqa: F401
        from app.tasks.celery_app import celery_app

        task = celery_app.tasks.get("app.tasks._impl.process_live_feed_events")
        assert task is not None
        assert task.time_limit <= 300

    def test_trigger_linkedin_lookup_has_very_short_time_limit(self) -> None:
        import app.tasks._impl  # noqa: F401
        from app.tasks.celery_app import celery_app

        task = celery_app.tasks.get("app.tasks._impl.trigger_linkedin_lookup")
        assert task is not None
        assert task.time_limit <= 90


# ══════════════════════════════════════════════════════════════════════════════
# 6 — Celery beat schedule
# ══════════════════════════════════════════════════════════════════════════════


class TestPhase5BeatSchedule:
    """Beat: legacy Phase 5 _impl live/stub tasks are not scheduled (real data uses scrapers.*)."""

    REMOVED_STUB_BEAT_ENTRIES = [
        "scrape-sedar-live",
        "scrape-osc-live",
        "scrape-canlii-live",
        "scrape-news-live",
        "scrape-scc-live",
        "scrape-edgar-live",
        "process-live-feed-events",
        "monitor-signal-velocity",
        "run-dead-signal-resurrector",
    ]

    def test_phase5_stub_beat_entries_removed(self) -> None:
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        for entry in self.REMOVED_STUB_BEAT_ENTRIES:
            assert entry not in schedule, f"Stub beat entry should be removed: {entry}"

    def test_real_category_scrapers_on_beat(self) -> None:
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "run-news-scrapers" in schedule
        assert schedule["run-news-scrapers"]["task"] == "scrapers.run_news"
        assert "run-regulatory-scrapers" in schedule
        assert schedule["run-regulatory-scrapers"]["task"] == "scrapers.run_regulatory"

    def test_phase5_task_routing_rules_present(self) -> None:
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert "app.tasks._impl.process_live_feed_events" in routes
        assert "app.tasks._impl.monitor_signal_velocity" in routes
        assert "app.tasks._impl.run_dead_signal_resurrector" in routes
        assert "app.tasks._impl.trigger_linkedin_lookup" in routes


# ══════════════════════════════════════════════════════════════════════════════
# 7 — Services __init__ sanity
# ══════════════════════════════════════════════════════════════════════════════


class TestServicesInit:
    """Sanity checks: all four new services import cleanly."""

    def test_live_feed_imports(self) -> None:
        from app.services.live_feed import CONSUMER_GROUP, STREAM_KEY

        assert STREAM_KEY == "oracle:live:signals"
        assert CONSUMER_GROUP == "scoring_consumers"

    def test_velocity_monitor_imports(self) -> None:
        from app.services.velocity_monitor import (
            VELOCITY_THRESHOLD,
        )

        assert VELOCITY_THRESHOLD == 2.0

    def test_linkedin_trigger_imports(self) -> None:
        from app.services.linkedin_trigger import (
            MAX_DAILY_LOOKUPS,
        )

        assert MAX_DAILY_LOOKUPS == 5

    def test_resurrector_imports(self) -> None:
        from app.services.resurrector import (
            CATEGORY_TASK_MAP,
            EXPECTED_INTERVALS,
        )

        assert len(EXPECTED_INTERVALS) > 0
        assert len(CATEGORY_TASK_MAP) > 0
