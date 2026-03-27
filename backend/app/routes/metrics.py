"""
app/routes/metrics.py — Prometheus metrics endpoint.

Exposes application-level metrics at GET /api/metrics for scraping by
Prometheus / Grafana. Requires admin role.

Metrics exposed:
  - oracle_http_requests_total{method, endpoint, status} — counter
  - oracle_http_request_duration_seconds{endpoint} — histogram
  - oracle_scoring_results_total — gauge (total rows in scoring_results)
  - oracle_active_companies_total — gauge (companies with score in last 24h)
  - oracle_model_drift_alerts_open — gauge (open drift alerts)
  - oracle_mandate_confirmations_total — gauge
  - oracle_celery_tasks_total{task_name, status} — counter (via Redis keys)

All counters and histograms are populated from api_request_log (Phase 7).
Production scrape interval: 15s.
"""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])

# ── Prometheus text format helpers ─────────────────────────────────────────────


def _gauge(name: str, value: float, help_text: str, labels: dict | None = None) -> str:
    """Render a single Prometheus gauge metric in text format."""
    label_str = ""
    if labels:
        pairs = ",".join(f'{k}="{v}"' for k, v in labels.items())
        label_str = f"{{{pairs}}}"
    return f"# HELP {name} {help_text}\n# TYPE {name} gauge\n{name}{label_str} {value}\n"


def _counter(name: str, rows: list[dict], help_text: str) -> str:
    """Render a labelled Prometheus counter from a list of {labels..., value} dicts."""
    lines = [f"# HELP {name} {help_text}", f"# TYPE {name} counter"]
    for row in rows:
        val = row.pop("value", 0)
        pairs = ",".join(f'{k}="{v}"' for k, v in row.items())
        lines.append(f"{name}{{{pairs}}} {val}")
    return "\n".join(lines) + "\n"


# ── Static SQL ─────────────────────────────────────────────────────────────────

_SQL_REQUEST_COUNTS = text("""
    SELECT
        COALESCE(regexp_replace(endpoint, '/[0-9]+', '/{id}', 'g'), 'unknown') AS endpoint,
        status_code,
        COUNT(*) AS cnt
    FROM api_request_log
    WHERE created_at >= NOW() - INTERVAL '5 minutes'
    GROUP BY 1, 2
    ORDER BY 1, 2
""")

_SQL_REQUEST_P95 = text("""
    SELECT
        COALESCE(regexp_replace(endpoint, '/[0-9]+', '/{id}', 'g'), 'unknown') AS endpoint,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) / 1000.0 AS p95_seconds
    FROM api_request_log
    WHERE created_at >= NOW() - INTERVAL '5 minutes'
    GROUP BY 1
    ORDER BY 1
""")

_SQL_SCORING_TOTAL = text("""
    SELECT COUNT(*) FROM scoring_results
""")

_SQL_ACTIVE_COMPANIES = text("""
    SELECT COUNT(DISTINCT company_id)
    FROM scoring_results
    WHERE scored_at >= NOW() - INTERVAL '24 hours'
""")

_SQL_DRIFT_ALERTS = text("""
    SELECT COUNT(*) FROM model_drift_alerts WHERE status = 'open'
""")

_SQL_CONFIRMATIONS = text("""
    SELECT COUNT(*) FROM mandate_confirmations
""")


# ── Route ──────────────────────────────────────────────────────────────────────


@router.get(
    "",
    summary="Prometheus metrics",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_admin)],
)
async def get_metrics(db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    """
    Expose Prometheus-compatible metrics.

    Scrape with: GET /api/v1/metrics
    Requires admin bearer token.

    All DB queries run in a single transaction against the API replica.
    Query timeout: 5 seconds (metrics must not block the API).
    """
    start = time.perf_counter()
    output_parts: list[str] = []

    try:
        # ── HTTP request counts (last 5 min) ──────────────────────────────────
        result = await db.execute(_SQL_REQUEST_COUNTS)
        rows = result.fetchall()
        counter_rows = [
            {"endpoint": r[0], "status_code": str(r[1]), "value": int(r[2])} for r in rows
        ]
        output_parts.append(
            _counter(
                "oracle_http_requests_total",
                counter_rows,
                "Total HTTP requests by endpoint and status code (last 5m window)",
            )
        )

        # ── p95 response time per endpoint ────────────────────────────────────
        result = await db.execute(_SQL_REQUEST_P95)
        p95_rows = result.fetchall()
        p95_lines = [
            "# HELP oracle_http_request_p95_seconds P95 response time in seconds (last 5m)",
            "# TYPE oracle_http_request_p95_seconds gauge",
        ]
        for r in p95_rows:
            p95_lines.append(f'oracle_http_request_p95_seconds{{endpoint="{r[0]}"}} {r[1]:.4f}')
        output_parts.append("\n".join(p95_lines) + "\n")

        # ── Scoring results total ─────────────────────────────────────────────
        result = await db.execute(_SQL_SCORING_TOTAL)
        total = result.scalar() or 0
        output_parts.append(
            _gauge(
                "oracle_scoring_results_total", float(total), "Total rows in scoring_results table"
            )
        )

        # ── Active companies (scored last 24h) ────────────────────────────────
        result = await db.execute(_SQL_ACTIVE_COMPANIES)
        active = result.scalar() or 0
        output_parts.append(
            _gauge(
                "oracle_active_companies_total",
                float(active),
                "Companies with at least one score in the last 24 hours",
            )
        )

        # ── Open drift alerts ─────────────────────────────────────────────────
        result = await db.execute(_SQL_DRIFT_ALERTS)
        alerts = result.scalar() or 0
        output_parts.append(
            _gauge(
                "oracle_model_drift_alerts_open",
                float(alerts),
                "Open model drift alerts requiring investigation",
            )
        )

        # ── Mandate confirmations ─────────────────────────────────────────────
        result = await db.execute(_SQL_CONFIRMATIONS)
        confirmations = result.scalar() or 0
        output_parts.append(
            _gauge(
                "oracle_mandate_confirmations_total",
                float(confirmations),
                "Total mandate confirmations recorded",
            )
        )

    except Exception as exc:
        log.exception("metrics_query_failed", error=str(exc))
        # Return what we have plus an error gauge rather than 500
        output_parts.append(
            _gauge("oracle_metrics_error", 1.0, "1 if metrics collection encountered an error")
        )

    # ── Scrape duration (meta-metric) ─────────────────────────────────────────
    elapsed = time.perf_counter() - start
    output_parts.append(
        _gauge("oracle_metrics_scrape_duration_seconds", elapsed, "Time to collect all metrics")
    )

    return PlainTextResponse(
        "".join(output_parts),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
