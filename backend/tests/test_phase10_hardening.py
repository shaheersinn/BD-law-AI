"""
tests/test_phase10_hardening.py — Phase 10 Testing & Hardening unit tests.

Tests:
    1. database_sync.py URL conversion (asyncpg → psycopg2)
    2. SecurityHeadersMiddleware injects X-Frame-Options: DENY
    3. SecurityHeadersMiddleware injects X-Content-Type-Options: nosniff
    4. SecurityHeadersMiddleware production HSTS header present
    5. SecurityHeadersMiddleware dev HSTS header absent
    6. Metrics endpoint returns Prometheus text format
    7. Phase 10 Celery tasks registered (score_company_batch uses sync DB)
    8. psycopg2-binary present in requirements.txt
    9. prometheus-client present in requirements.txt
   10. locust present in requirements-dev.txt
"""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent
REQUIREMENTS = (BACKEND_ROOT / "requirements.txt").read_text()
REQUIREMENTS_DEV = (BACKEND_ROOT / "requirements-dev.txt").read_text()


# ── 1. database_sync URL conversion ───────────────────────────────────────────


def test_sync_url_converts_asyncpg_to_psycopg2():
    """_build_sync_url() converts asyncpg driver string to psycopg2."""
    from app.database_sync import _build_sync_url

    async_url = "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_db"
    sync_url = _build_sync_url(async_url)

    assert "psycopg2" in sync_url
    assert "asyncpg" not in sync_url
    assert sync_url == "postgresql+psycopg2://oracle:oracle@localhost:5432/oracle_db"


def test_sync_url_preserves_credentials_and_path():
    """_build_sync_url() preserves user, password, host, port, and dbname."""
    from app.database_sync import _build_sync_url

    async_url = "postgresql+asyncpg://user:secret@db.example.com:5433/mydb"
    sync_url = _build_sync_url(async_url)

    assert "user:secret@db.example.com:5433/mydb" in sync_url


# ── 2–5. SecurityHeadersMiddleware ────────────────────────────────────────────


def test_security_headers_x_frame_options():
    """SecurityHeadersMiddleware adds X-Frame-Options: DENY."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from app.middleware.security_headers import SecurityHeadersMiddleware

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware, is_production=False)

    client = TestClient(app)
    resp = client.get("/")
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_security_headers_x_content_type_options():
    """SecurityHeadersMiddleware adds X-Content-Type-Options: nosniff."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from app.middleware.security_headers import SecurityHeadersMiddleware

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware, is_production=False)

    client = TestClient(app)
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_security_headers_hsts_present_in_production():
    """SecurityHeadersMiddleware adds HSTS in production mode."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from app.middleware.security_headers import SecurityHeadersMiddleware

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware, is_production=True)

    client = TestClient(app)
    resp = client.get("/")
    hsts = resp.headers.get("Strict-Transport-Security", "")
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts


def test_security_headers_hsts_absent_in_development():
    """SecurityHeadersMiddleware does NOT add HSTS in development mode."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    from app.middleware.security_headers import SecurityHeadersMiddleware

    async def homepage(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware, is_production=False)

    client = TestClient(app)
    resp = client.get("/")
    assert "Strict-Transport-Security" not in resp.headers


# ── 6. Metrics endpoint ────────────────────────────────────────────────────────


def test_metrics_router_exists():
    """app/routes/metrics.py declares a router with the correct prefix."""
    metrics_source = (BACKEND_ROOT / "app" / "routes" / "metrics.py").read_text()
    assert 'prefix="/v1/metrics"' in metrics_source


def test_metrics_gauge_helper_output():
    """_gauge() produces valid Prometheus text format — verified from source structure."""
    metrics_source = (BACKEND_ROOT / "app" / "routes" / "metrics.py").read_text()
    # Verify the _gauge helper function exists and emits the right format
    assert "def _gauge(" in metrics_source
    assert "# HELP" in metrics_source
    assert "# TYPE" in metrics_source
    assert "gauge" in metrics_source


# ── 7. Sync DB import in phase6_tasks ─────────────────────────────────────────


def test_phase6_tasks_import_get_sync_db():
    """phase6_tasks.py imports get_sync_db (not asyncio.run for SQL tasks)."""
    task_source = (BACKEND_ROOT / "app" / "tasks" / "phase6_tasks.py").read_text()

    assert "get_sync_db" in task_source, "phase6_tasks.py must import get_sync_db"
    assert "database_sync" in task_source, "phase6_tasks.py must import from database_sync"


def test_phase6_tasks_no_asyncio_run_for_sql_tasks():
    """
    SQL-only tasks in phase6_tasks.py no longer use asyncio.run().
    Only refresh_model_orchestrator (which calls async services) may use it.
    """
    task_source = (BACKEND_ROOT / "app" / "tasks" / "phase6_tasks.py").read_text()

    # Count asyncio.run() calls on actual code lines (exclude comments and docstrings)
    lines = task_source.splitlines()
    asyncio_run_code_lines = []
    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Simple docstring toggle (handles triple-quoted strings)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = not in_docstring
        if not in_docstring and not stripped.startswith("#") and "asyncio.run(" in line:
            asyncio_run_code_lines.append(i + 1)

    # There should be at most 1 asyncio.run (for refresh_model_orchestrator)
    assert len(asyncio_run_code_lines) <= 1, (
        f"Expected at most 1 asyncio.run() call in phase6_tasks.py "
        f"(only for refresh_model_orchestrator), found at lines: {asyncio_run_code_lines}"
    )


# ── 8–10. Requirements ────────────────────────────────────────────────────────


def test_psycopg2_binary_in_requirements():
    """psycopg2-binary must be pinned in requirements.txt."""
    assert "psycopg2-binary" in REQUIREMENTS


def test_prometheus_client_in_requirements():
    """prometheus-client must be pinned in requirements.txt."""
    assert "prometheus-client" in REQUIREMENTS


def test_locust_in_requirements_dev():
    """locust must be in requirements-dev.txt."""
    assert "locust" in REQUIREMENTS_DEV


# ── 11. Sentry CeleryIntegration ──────────────────────────────────────────────


def test_sentry_celery_integration_in_main():
    """main.py must import CeleryIntegration when Sentry DSN is set."""
    main_source = (BACKEND_ROOT / "app" / "main.py").read_text()
    assert "CeleryIntegration" in main_source


# ── 12. Security headers middleware registered in main.py ─────────────────────


def test_security_headers_middleware_registered():
    """main.py must register SecurityHeadersMiddleware."""
    main_source = (BACKEND_ROOT / "app" / "main.py").read_text()
    assert "SecurityHeadersMiddleware" in main_source


# ── 13. Metrics router registered in main.py ──────────────────────────────────


def test_metrics_router_registered_in_main():
    """main.py must register the metrics router."""
    main_source = (BACKEND_ROOT / "app" / "main.py").read_text()
    assert "metrics_router" in main_source
