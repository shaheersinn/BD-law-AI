"""
app/training/train_all.py — Azure batch training pipeline.

Trains all 34 × 3 = 102 BayesianEngine models + 34 TransformerScorer models.
Runs on Azure ML (never locally — requires GPU + large memory for full dataset).

How to run:
    python -m app.training.azure_job  (submits to Azure ML)
    python -m app.training.train_all  (direct run on Azure compute, not locally)

Pipeline steps:
    1. Pull features + labels from PostgreSQL
    2. For each of 34 practice areas:
       a. Build feature matrix + label vectors (30/60/90d)
       b. Train BayesianEngine (XGBoost + Optuna, 100 trials per horizon)
       c. Train TransformerScorer (10 epochs)
       d. Evaluate both on holdout (last 6 months)
       e. Record results in model_registry (PostgreSQL)
    3. Upload all artifacts to DigitalOcean Spaces
    4. Update orchestrator config
    5. Seed signal_decay_config + sector_signal_weights tables
    6. Run anomaly detector training on clean companies
    7. Run signal co-occurrence mining
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ── Entry point ────────────────────────────────────────────────────────────────


async def run_training_pipeline(
    output_base: Path = Path("/tmp/oracle_models"),  # noqa: S108
    n_optuna_trials: int = 100,
    n_transformer_epochs: int = 10,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Full training pipeline. Called from Azure batch job.

    Args:
        output_base:           Local directory for model artifacts.
        n_optuna_trials:       Optuna trials per horizon per practice area.
        n_transformer_epochs:  Transformer training epochs.
        dry_run:               If True, train on 10% of data (for CI validation).
    Returns:
        Training summary dict.
    """
    from app.database import get_db
    from app.ml.bayesian_engine import FEATURE_COLUMNS, PRACTICE_AREAS, BayesianEngine
    from app.ml.transformer_scorer import TransformerScorer
    from app.training.dataset_builder import DatasetBuilder
    from app.training.model_registry import ModelRegistry
    from app.training.spaces_uploader import upload_model_artifacts

    log.info("=" * 60)
    log.info("ORACLE ML Training Pipeline")
    log.info(
        "Practice areas: %d | Horizons: 3 | Optuna trials: %d", len(PRACTICE_AREAS), n_optuna_trials
    )
    log.info("=" * 60)

    output_base.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "practice_areas_trained": [],
        "practice_areas_failed": [],
        "model_selections": {},
        "total_training_seconds": 0.0,
    }

    import time

    pipeline_start = time.perf_counter()

    # ── Build datasets ─────────────────────────────────────────────────────────
    log.info("Building datasets from PostgreSQL...")
    async with get_db() as db:
        builder = DatasetBuilder(db)
        datasets = await builder.build_all_practice_area_datasets(
            feature_columns=FEATURE_COLUMNS,
            dry_run=dry_run,
        )
        clean_X = await builder.fetch_clean_company_features(feature_columns=FEATURE_COLUMNS)
        mandate_events_by_pa = await builder.fetch_mandate_events_for_cooccurrence()
        sector_training_data = await builder.fetch_sector_training_data(
            feature_columns=FEATURE_COLUMNS
        )

    log.info("Dataset build complete. %d practice areas have data.", len(datasets))

    # ── Train per practice area ────────────────────────────────────────────────
    registry = ModelRegistry()

    for pa in PRACTICE_AREAS:
        pa_data = datasets.get(pa)
        if pa_data is None:
            log.warning("No training data for %s — skipping", pa)
            summary["practice_areas_failed"].append(pa)
            continue

        pa_output = output_base / "bayesian" / pa
        pa_output.mkdir(parents=True, exist_ok=True)

        log.info(
            "Training %s (%d train, %d holdout samples)",
            pa,
            pa_data["n_train"],
            pa_data["n_holdout"],
        )

        # ── Bayesian training ──────────────────────────────────────────────────
        try:
            bayesian_results = BayesianEngine.train(
                practice_area=pa,
                X_train=pa_data["X_train"],
                y_train_30d=pa_data["y_train_30d"],
                y_train_60d=pa_data["y_train_60d"],
                y_train_90d=pa_data["y_train_90d"],
                X_holdout=pa_data["X_holdout"],
                y_holdout_30d=pa_data["y_holdout_30d"],
                y_holdout_60d=pa_data["y_holdout_60d"],
                y_holdout_90d=pa_data["y_holdout_90d"],
                output_dir=pa_output,
                n_trials=n_optuna_trials,
            )
            bayesian_f1_30 = next((r.f1_holdout for r in bayesian_results if r.horizon == 30), 0.0)
        except Exception:
            log.exception("BayesianEngine training failed for %s", pa)
            summary["practice_areas_failed"].append(pa)
            continue

        # ── Transformer training ───────────────────────────────────────────────
        transformer_f1_30 = 0.0
        if pa_data.get("X_seq_train") is not None:
            try:
                tf_output = output_base / "transformer" / pa
                tf_result = TransformerScorer.train(
                    practice_area=pa,
                    X_seq_train=pa_data["X_seq_train"],
                    y_train=pa_data["y_train_seq"],
                    X_seq_holdout=pa_data["X_seq_holdout"],
                    y_holdout=pa_data["y_holdout_seq"],
                    output_dir=tf_output,
                    n_epochs=n_transformer_epochs,
                )
                transformer_f1_30 = tf_result["holdout_metrics"].get("f1_30d", 0.0)
            except Exception:
                log.exception("TransformerScorer training failed for %s (non-fatal)", pa)

        # ── Record in model_registry ───────────────────────────────────────────
        from app.ml.bayesian_engine import ORCHESTRATOR_F1_THRESHOLD

        active_model = (
            "transformer"
            if transformer_f1_30 > bayesian_f1_30 + ORCHESTRATOR_F1_THRESHOLD
            else "bayesian"
        )
        registry.record(pa, bayesian_f1_30, transformer_f1_30, active_model, bayesian_results)

        summary["practice_areas_trained"].append(pa)
        summary["model_selections"][pa] = {
            "active": active_model,
            "bayesian_f1": bayesian_f1_30,
            "transformer_f1": transformer_f1_30,
        }
        log.info(
            "%s: active=%s bayesian_f1=%.3f transformer_f1=%.3f",
            pa,
            active_model,
            bayesian_f1_30,
            transformer_f1_30,
        )

    # ── Anomaly detector training ──────────────────────────────────────────────
    if clean_X is not None and len(clean_X) >= 100:
        log.info("Training AnomalyDetector on %d clean companies...", len(clean_X))
        try:
            from app.ml.anomaly_detector import AnomalyDetector

            anomaly_result = AnomalyDetector.train(
                X_clean=clean_X,
                output_dir=output_base / "anomaly",
                n_epochs=50,
            )
            log.info("AnomalyDetector trained: threshold=%.4f", anomaly_result["anomaly_threshold"])
        except Exception:
            log.exception("AnomalyDetector training failed (non-fatal)")
    else:
        log.warning("Insufficient clean company data for AnomalyDetector training")

    # ── Signal co-occurrence mining ────────────────────────────────────────────
    if mandate_events_by_pa:
        log.info("Mining signal co-occurrence rules...")
        try:
            from app.ml.cooccurrence import mine_all_practice_areas

            all_rules = mine_all_practice_areas(mandate_events_by_pa)
            total_rules = sum(len(v) for v in all_rules.values())
            log.info(
                "Co-occurrence: %d rules mined across %d practice areas",
                total_rules,
                len(all_rules),
            )
            summary["cooccurrence_rules"] = total_rules
        except Exception:
            log.exception("Co-occurrence mining failed (non-fatal)")

    # ── Sector weight calibration ──────────────────────────────────────────────
    if sector_training_data is not None:
        log.info("Calibrating sector signal weights...")
        try:
            from app.ml.bayesian_engine import FEATURE_COLUMNS as FEAT_COLS
            from app.ml.sector_weights import calibrate_sector_weights

            weights = calibrate_sector_weights(
                X_train=sector_training_data["X"],
                y_train=sector_training_data["y"],
                feature_columns=FEAT_COLS,
            )
            log.info("Sector weights calibrated for %d sectors", len(weights))
            summary["sector_weights_sectors"] = len(weights)
        except Exception:
            log.exception("Sector weight calibration failed (non-fatal)")

    # ── Upload artifacts to DigitalOcean Spaces ───────────────────────────────
    log.info("Uploading model artifacts to DO Spaces...")
    try:
        uploaded = await upload_model_artifacts(output_base)
        log.info("Uploaded %d artifact files to DO Spaces", uploaded)
        summary["artifacts_uploaded"] = uploaded
    except Exception:
        log.exception("DO Spaces upload failed (non-fatal — artifacts saved locally)")
        summary["artifacts_uploaded"] = 0

    # ── Flush registry to DB ───────────────────────────────────────────────────
    async with get_db() as db:
        await registry.flush_to_db(db)

    summary["total_training_seconds"] = time.perf_counter() - pipeline_start
    log.info("=" * 60)
    log.info(
        "Training complete: %d/%d practice areas trained in %.0fs",
        len(summary["practice_areas_trained"]),
        len(PRACTICE_AREAS),
        summary["total_training_seconds"],
    )
    log.info("=" * 60)

    return summary


if __name__ == "__main__":
    # Direct execution on Azure compute
    dry_run = "--dry-run" in sys.argv
    output_dir = Path(os.getenv("OUTPUT_DIR", "/tmp/oracle_models"))  # noqa: S108
    result = asyncio.run(run_training_pipeline(output_base=output_dir, dry_run=dry_run))
    print(json.dumps(result, indent=2, default=str))
