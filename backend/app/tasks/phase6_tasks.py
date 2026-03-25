"""
app/tasks/phase6_tasks.py — Phase 6 ML scoring Celery tasks.

Implements Agents 023-027 + ML maintenance tasks:
    Agent 023 — Model Selector (orchestrator refresh)
    Agent 024 — Anomaly Escalation
    Agent 025 — Score Decay (stale score cleanup)
    Agent 026 — Sector Baseline calibration
    Agent 027 — CCAA Cascade signal amplifier

Also implements support tasks:
    - score_company_batch: Score N companies on demand
    - run_active_learning: Weekly uncertainty identification
    - mine_cooccurrence_rules: Monthly Apriori mining
    - run_cross_jurisdiction_propagation: Daily propagation
    - update_graph_features: Daily graph centrality update
    - seed_decay_config: One-time default lambda seeding
"""

from __future__ import annotations

from typing import Any

import structlog

from app.tasks.celery_app import celery_app

log = structlog.get_logger(__name__)


# ── Agent 023: Model Selector ─────────────────────────────────────────────────


@celery_app.task(
    name="agents.refresh_model_orchestrator",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
    queue="agents",
    acks_late=True,
)
def refresh_model_orchestrator(self: Any) -> dict[str, Any]:
    """
    Agent 023 — Reload orchestrator model selections from model_registry.
    Runs every 6 hours. Hot-reloads without API restart.
    """
    import asyncio

    from app.database import get_db
    from app.ml.orchestrator import get_orchestrator
    from app.training.model_registry import load_registry_from_db

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                registry = await load_registry_from_db(db)

            orchestrator = get_orchestrator()
            orchestrator.update_from_registry(registry)

            report = orchestrator.get_selection_report()
            transformer_count = sum(1 for r in report if r["active_model"] == "transformer")

            return {
                "registry_records": len(registry),
                "transformer_active": transformer_count,
                "bayesian_active": len(report) - transformer_count,
            }

        result = asyncio.run(_run())
        log.info("agent_023_model_selector", **result)
        return result

    except Exception as exc:
        log.exception("agent_023_model_selector_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Agent 024: Anomaly Escalation ─────────────────────────────────────────────


@celery_app.task(
    name="agents.run_anomaly_escalation",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    time_limit=600,
    soft_time_limit=540,
    queue="agents",
    acks_late=True,
)
def run_anomaly_escalation(self: Any, anomaly_threshold: float = 0.7) -> dict[str, Any]:
    """
    Agent 024 — Identify companies with high anomaly scores.
    Escalates to active_learning_queue with high priority.
    Runs daily after scoring pipeline.
    """
    import asyncio

    from app.database import get_db

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                from sqlalchemy import text

                result = await db.execute(
                    text("""
                        SELECT company_id, anomaly_score, scored_at
                        FROM scoring_results
                        WHERE scored_at >= NOW() - INTERVAL '24 hours'
                          AND anomaly_score >= :threshold
                        ORDER BY anomaly_score DESC
                        LIMIT 200
                    """),
                    {"threshold": anomaly_threshold},
                )
                anomalous = result.fetchall()

                escalated = 0
                for row in anomalous:
                    company_id, anomaly_score, scored_at = row
                    # Insert/update active learning queue with high priority
                    await db.execute(
                        text("""
                            INSERT INTO active_learning_queue
                                (company_id, practice_area, priority_score, status)
                            VALUES (:company_id, 'anomaly', :priority, 'pending')
                            ON CONFLICT DO NOTHING
                        """),
                        {"company_id": company_id, "priority": float(anomaly_score)},
                    )
                    escalated += 1

                await db.commit()

            return {"anomalous_companies": len(anomalous), "escalated": escalated}

        result = asyncio.run(_run())
        log.info("agent_024_anomaly_escalation", **result)
        return result

    except Exception as exc:
        log.exception("agent_024_anomaly_escalation_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Agent 025: Score Decay ─────────────────────────────────────────────────────


@celery_app.task(
    name="agents.clean_stale_scores",
    bind=True,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240,
    queue="agents",
    acks_late=True,
)
def clean_stale_scores(self: Any, retention_days: int = 90) -> dict[str, Any]:
    """
    Agent 025 — Archive scoring_results older than retention_days.
    Runs weekly. Prevents table bloat.
    """
    import asyncio

    from app.database import get_db

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                from sqlalchemy import text

                result = await db.execute(
                    text("""
                        DELETE FROM scoring_results
                        WHERE scored_at < NOW() - INTERVAL ':days days'
                    """),
                    {"days": retention_days},
                )
                await db.commit()
                return {"deleted_rows": result.rowcount}

        result = asyncio.run(_run())
        log.info("agent_025_score_decay", **result)
        return result

    except Exception as exc:
        log.exception("agent_025_score_decay_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Agent 026: Sector Baseline ─────────────────────────────────────────────────


@celery_app.task(
    name="agents.update_sector_baseline",
    bind=True,
    max_retries=2,
    time_limit=600,
    soft_time_limit=540,
    queue="agents",
    acks_late=True,
)
def update_sector_baseline(self: Any) -> dict[str, Any]:
    """
    Agent 026 — Recalibrate sector-normal score baselines monthly.
    Updates sector_signal_weights table from latest training data.
    """
    # Stub: full implementation requires running mini-calibration from live data
    # Full calibration happens in Azure training job
    log.info("agent_026_sector_baseline: scheduled recalibration (full run via Azure)")
    return {"status": "deferred_to_azure_training"}


# ── Agent 027: CCAA Cascade ────────────────────────────────────────────────────


@celery_app.task(
    name="agents.run_ccaa_cascade",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
    queue="agents",
    acks_late=True,
)
def run_ccaa_cascade(self: Any) -> dict[str, Any]:
    """
    Agent 027 — CCAA cascade signal amplifier.
    When a new CCAA filing is detected, simultaneously amplify signals for:
    - Class Actions (same company)
    - Securities (same company — shareholder class action follows)
    - Employment (mass layoff follows restructuring)
    """
    import asyncio

    from app.database import get_db

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                from sqlalchemy import text

                # Find recent CCAA signals not yet cascaded
                result = await db.execute(
                    text("""
                        SELECT DISTINCT sr.company_id
                        FROM signal_records sr
                        WHERE sr.signal_type = 'canlii_ccaa'
                          AND sr.published_at >= NOW() - INTERVAL '7 days'
                          AND NOT EXISTS (
                              SELECT 1 FROM signal_records sr2
                              WHERE sr2.company_id = sr.company_id
                                AND sr2.signal_type = 'ccaa_cascade_applied'
                          )
                    """)
                )
                ccaa_companies = [row[0] for row in result.fetchall()]
                cascaded = 0

                for company_id in ccaa_companies:
                    # Create cascade signals for co-occurring practice areas
                    cascade_signals = [
                        ("class_actions_cascade", "class_actions", 0.85),
                        ("securities_cascade", "securities", 0.75),
                        ("employment_cascade", "employment", 0.70),
                    ]
                    for signal_type, _pa, confidence in cascade_signals:
                        await db.execute(
                            text("""
                                INSERT INTO signal_records
                                    (company_id, signal_type, signal_value, confidence_score,
                                     source_id, published_at, is_canary)
                                VALUES (:company_id, :signal_type, '{}', :confidence,
                                        'ccaa_cascade_agent', NOW(), false)
                                ON CONFLICT DO NOTHING
                            """),
                            {
                                "company_id": company_id,
                                "signal_type": signal_type,
                                "confidence": confidence,
                            },
                        )
                    cascaded += 1

                await db.commit()
            return {"ccaa_companies_found": len(ccaa_companies), "cascaded": cascaded}

        result = asyncio.run(_run())
        log.info("agent_027_ccaa_cascade", **result)
        return result

    except Exception as exc:
        log.exception("agent_027_ccaa_cascade_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Scoring batch task ─────────────────────────────────────────────────────────


@celery_app.task(
    name="scoring.score_company_batch",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
    queue="scoring",
    acks_late=True,
)
def score_company_batch(self: Any, company_ids: list[int]) -> dict[str, Any]:
    """
    Score a batch of companies using the orchestrator.
    Stores results in scoring_results table.
    Triggered by live feed events and nightly batch.

    Performance: one bulk SELECT → in-memory ML scoring → one bulk INSERT.
    No per-company DB round-trips inside the scoring loop.
    """
    import asyncio
    import json

    from app.database import get_db
    from app.ml.orchestrator import get_orchestrator

    try:

        async def _run() -> dict[str, Any]:
            orchestrator = get_orchestrator()
            if not orchestrator._loaded:
                log.warning("scoring_batch: orchestrator not loaded, loading now")
                orchestrator.load()

            from app.ml.anomaly_detector import get_anomaly_detector
            from app.ml.velocity_scorer import aggregate_company_velocity

            async with get_db() as db:
                from sqlalchemy import text

                # ── Phase A: Bulk fetch latest features for all companies ────
                feat_result = await db.execute(
                    text("""
                        SELECT DISTINCT ON (company_id) *
                        FROM company_features
                        WHERE company_id = ANY(:ids)
                        ORDER BY company_id, feature_date DESC
                    """),
                    {"ids": list(company_ids)},
                )
                feature_map: dict[int, dict] = {
                    row["company_id"]: dict(row) for row in feat_result.mappings()
                }

                # ── Phase B: In-memory scoring (zero DB I/O) ────────────────
                rows_to_insert: list[dict] = []
                failed = 0

                for company_id in company_ids:
                    features = feature_map.get(company_id)
                    if features is None:
                        log.warning("score_company_batch: no features for company %d", company_id)
                        failed += 1
                        continue
                    try:
                        horizon_scores = orchestrator.score_company(features)
                        scores_json = {pa: hs.as_dict() for pa, hs in horizon_scores.items()}
                        velocity = aggregate_company_velocity(
                            {pa: {"30d": hs.score_30d} for pa, hs in horizon_scores.items()}
                        )
                        anomaly = get_anomaly_detector().score(features)
                        rows_to_insert.append(
                            {
                                "company_id": company_id,
                                "scores": json.dumps(scores_json),
                                "velocity_score": velocity,
                                "anomaly_score": anomaly,
                                "model_versions": json.dumps(
                                    {pa: hs.model_version for pa, hs in horizon_scores.items()}
                                ),
                            }
                        )
                    except Exception:
                        log.exception(
                            "score_company_batch: scoring failed for company %d", company_id
                        )
                        failed += 1

                # ── Phase C: Bulk INSERT (one executemany call) ──────────────
                if rows_to_insert:
                    await db.execute(
                        text("""
                            INSERT INTO scoring_results
                                (company_id, scored_at, scores, velocity_score,
                                 anomaly_score, model_versions)
                            VALUES (:company_id, NOW(), :scores::jsonb, :velocity_score,
                                    :anomaly_score, :model_versions::jsonb)
                        """),
                        rows_to_insert,
                    )
                    await db.commit()

            scored = len(rows_to_insert)
            return {"scored": scored, "failed": failed, "total": len(company_ids)}

        result = asyncio.run(_run())
        log.info("scoring_batch_complete", **result)
        return result

    except Exception as exc:
        log.exception("scoring_batch_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Active learning task ───────────────────────────────────────────────────────


@celery_app.task(
    name="agents.run_active_learning",
    bind=True,
    max_retries=2,
    time_limit=600,
    soft_time_limit=540,
    queue="agents",
    acks_late=True,
)
def run_active_learning(self: Any) -> dict[str, Any]:
    """Weekly: identify uncertain companies and queue for priority scraping."""
    import asyncio
    import json

    from app.database import get_db
    from app.ml.active_learning import (
        build_active_learning_queue_rows,
        identify_uncertain_companies,
    )

    try:

        async def _run() -> dict[str, Any]:
            async with get_db() as db:
                from sqlalchemy import text

                result = await db.execute(
                    text("""
                        SELECT company_id, scores
                        FROM scoring_results
                        WHERE scored_at >= NOW() - INTERVAL '24 hours'
                    """)
                )
                rows = result.fetchall()

                company_scores: dict[int, dict[str, dict[int, float]]] = {}
                for row in rows:
                    cid = row[0]
                    scores = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                    # Convert string keys to int
                    company_scores[cid] = {
                        pa: {int(k): v for k, v in hs.items()} for pa, hs in scores.items()
                    }

                uncertain = identify_uncertain_companies(company_scores)
                queue_rows = build_active_learning_queue_rows(uncertain)

                for queue_row in queue_rows:
                    await db.execute(
                        text("""
                            INSERT INTO active_learning_queue
                                (company_id, practice_area, priority_score, status)
                            VALUES (:company_id, :practice_area, :priority_score, 'pending')
                            ON CONFLICT DO NOTHING
                        """),
                        queue_row,
                    )
                await db.commit()

            return {
                "uncertain_companies": len(uncertain),
                "queue_rows_added": len(queue_rows),
            }

        result = asyncio.run(_run())
        log.info("active_learning_complete", **result)
        return result

    except Exception as exc:
        log.exception("active_learning_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


# ── Seed decay config (one-time) ──────────────────────────────────────────────


@celery_app.task(
    name="agents.seed_decay_config",
    bind=True,
    max_retries=2,
    time_limit=120,
    soft_time_limit=90,
    queue="agents",
    acks_late=True,
)
def seed_decay_config(self: Any) -> dict[str, Any]:
    """
    Seed signal_decay_config table with default lambda values.
    Called once after Phase 6 migration runs.
    Subsequent calibrations come from Azure training jobs.
    """
    import asyncio

    from app.database import get_db
    from app.ml.temporal_decay import build_default_decay_config_rows

    try:

        async def _run() -> dict[str, Any]:
            rows = build_default_decay_config_rows()
            async with get_db() as db:
                from sqlalchemy import text

                inserted = 0
                for row in rows:
                    result = await db.execute(
                        text("""
                            INSERT INTO signal_decay_config
                                (signal_type, practice_area, lambda_value,
                                 half_life_days, calibrated, source)
                            VALUES (:signal_type, :practice_area, :lambda_value,
                                    :half_life_days, :calibrated, :source)
                            ON CONFLICT (signal_type, practice_area) DO NOTHING
                        """),
                        row,
                    )
                    inserted += result.rowcount
                await db.commit()
            return {"inserted": inserted, "total": len(rows)}

        result = asyncio.run(_run())
        log.info("seed_decay_config_complete", **result)
        return result

    except Exception as exc:
        log.exception("seed_decay_config_failed", error=str(exc))
        raise self.retry(exc=exc) from exc
