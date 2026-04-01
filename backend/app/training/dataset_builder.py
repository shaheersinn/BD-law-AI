"""
app/training/dataset_builder.py — Pulls features + labels from PostgreSQL.

Builds train/holdout splits per practice area.
Holdout = last 6 months of data (never seen in training — hard rule).
Sequence data built for transformer (30-day rolling windows).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

HOLDOUT_MONTHS: int = 6


class DatasetBuilder:
    """Pulls and assembles training datasets from PostgreSQL."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def build_all_practice_area_datasets(
        self,
        feature_columns: list[str],
        dry_run: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """
        Build train/holdout splits for all 34 practice areas.

        Returns:
            {practice_area: {
                X_train, y_train_30d, y_train_60d, y_train_90d,
                X_holdout, y_holdout_30d, y_holdout_60d, y_holdout_90d,
                X_seq_train, y_train_seq,   # for transformer
                X_seq_holdout, y_holdout_seq,
                n_train, n_holdout,
            }}
        """
        holdout_cutoff = datetime.now(tz=UTC) - timedelta(days=HOLDOUT_MONTHS * 30)
        limit = 1000 if dry_run else None

        # Pull all company_features
        log.info("Fetching company_features from PostgreSQL...")
        features_df = await self._fetch_features(feature_columns, limit=limit)

        if features_df.empty:
            log.error("company_features table is empty — Phase 2 must be run first")
            return {}

        # Pull mandate_labels
        log.info("Fetching mandate_labels from PostgreSQL...")
        labels_df = await self._fetch_labels()

        if labels_df.empty:
            log.error("mandate_labels table is empty — Phase 3 must be run first")
            return {}

        log.info(
            "Loaded %d feature rows, %d label rows",
            len(features_df),
            len(labels_df),
        )

        # Build per-practice-area datasets
        from app.ml.bayesian_engine import PRACTICE_AREAS

        datasets: dict[str, dict[str, Any]] = {}

        for pa in PRACTICE_AREAS:
            try:
                pa_dataset = self._build_pa_dataset(
                    features_df=features_df,
                    labels_df=labels_df,
                    practice_area=pa,
                    feature_columns=feature_columns,
                    holdout_cutoff=holdout_cutoff,
                )
                if pa_dataset is not None:
                    datasets[pa] = pa_dataset
            except Exception:
                log.exception("Failed to build dataset for %s", pa)

        return datasets

    def _build_pa_dataset(
        self,
        features_df: pd.DataFrame,
        labels_df: pd.DataFrame,
        practice_area: str,
        feature_columns: list[str],
        holdout_cutoff: datetime,
    ) -> dict[str, Any] | None:
        """Build train/holdout for a single practice area."""
        # Filter labels for this practice area
        pa_labels = labels_df[labels_df["practice_area"] == practice_area].copy()

        # Merge features with labels on company_id + feature_date ≈ mandate window
        # Strategy: label a feature row as positive if there's a mandate
        # within [feature_date, feature_date + horizon] for that company.
        merged = features_df.merge(
            pa_labels[["company_id", "mandate_confirmed_at", "is_negative_label"]],
            on="company_id",
            how="left",
        )

        # Build label columns per horizon
        for horizon in [30, 60, 90]:

            def has_mandate_in_window(row: pd.Series, _h: int = horizon) -> int:  # noqa: B023
                if pd.isna(row.get("mandate_confirmed_at")):
                    return 0
                if row.get("is_negative_label", False):
                    return 0
                feature_date = row.get("feature_date")
                mandate_date = row.get("mandate_confirmed_at")
                if feature_date is None or mandate_date is None:
                    return 0
                try:
                    fd = pd.Timestamp(feature_date).to_pydatetime()
                    md = pd.Timestamp(mandate_date).to_pydatetime()
                    delta = (md - fd).days
                    return 1 if 0 <= delta <= _h else 0
                except Exception:
                    return 0

            merged[f"label_{horizon}d"] = merged.apply(has_mandate_in_window, axis=1)

        # De-duplicate: one row per company per feature_date
        merged = merged.drop_duplicates(subset=["company_id", "feature_date"])

        # Split train / holdout
        if "feature_date" in merged.columns:
            holdout_mask = pd.to_datetime(merged["feature_date"]) >= pd.Timestamp(holdout_cutoff)
        else:
            # If no date column, use last 20% as holdout
            n = len(merged)
            holdout_mask = pd.Series([i >= int(n * 0.8) for i in range(n)], index=merged.index)

        X_cols = [c for c in feature_columns if c in merged.columns]
        missing = [c for c in feature_columns if c not in merged.columns]
        if missing:
            log.warning(
                "%s: %d feature columns missing from features table: %s...",
                practice_area,
                len(missing),
                missing[:3],
            )

        train_df = merged[~holdout_mask]
        holdout_df = merged[holdout_mask]

        if len(train_df) < 20:
            log.warning("%s: only %d training samples — skipping", practice_area, len(train_df))
            return None

        X_train = train_df[X_cols].fillna(0).astype(np.float32)
        X_holdout = holdout_df[X_cols].fillna(0).astype(np.float32)

        result: dict[str, Any] = {
            "X_train": X_train,
            "y_train_30d": train_df["label_30d"],
            "y_train_60d": train_df["label_60d"],
            "y_train_90d": train_df["label_90d"],
            "X_holdout": X_holdout,
            "y_holdout_30d": holdout_df["label_30d"],
            "y_holdout_60d": holdout_df["label_60d"],
            "y_holdout_90d": holdout_df["label_90d"],
            "n_train": len(train_df),
            "n_holdout": len(holdout_df),
            # Sequence data for transformer (30-day rolling windows)
            "X_seq_train": self._build_sequences(train_df, X_cols),
            "y_train_seq": {h: train_df[f"label_{h}d"].values for h in [30, 60, 90]},
            "X_seq_holdout": self._build_sequences(holdout_df, X_cols),
            "y_holdout_seq": {h: holdout_df[f"label_{h}d"].values for h in [30, 60, 90]},
        }
        return result

    @staticmethod
    def _build_sequences(
        df: pd.DataFrame,
        feature_cols: list[str],
        seq_len: int = 30,
    ) -> np.ndarray | None:
        """
        Build [n_samples, seq_len, n_features] array for transformer.
        Attempts to sort by company_id + date and build rolling windows.
        Returns None if insufficient data for sequences.
        """
        try:
            if "feature_date" not in df.columns or len(df) < seq_len:
                return None

            df_sorted = df.sort_values(["company_id", "feature_date"])
            companies = df_sorted["company_id"].unique()
            sequences: list[np.ndarray] = []

            for company_id in companies:
                company_rows = df_sorted[df_sorted["company_id"] == company_id][feature_cols]
                if len(company_rows) == 0:
                    continue
                arr = company_rows.fillna(0).values.astype(np.float32)

                # Pad or truncate to seq_len
                if len(arr) < seq_len:
                    pad = np.zeros((seq_len - len(arr), arr.shape[1]), dtype=np.float32)
                    arr = np.vstack([pad, arr])
                else:
                    arr = arr[-seq_len:]

                sequences.append(arr)

            if not sequences:
                return None

            return np.stack(sequences)  # [n_companies, seq_len, n_features]

        except Exception:
            log.exception("Failed to build sequences")
            return None

    async def _fetch_features(
        self, feature_columns: list[str], limit: int | None = None
    ) -> pd.DataFrame:
        """Fetch company_features from PostgreSQL."""
        try:
            limit_clause = f"LIMIT {limit}" if limit else ""
            query = text(f"""
                SELECT company_id, feature_date, {", ".join(feature_columns)}
                FROM company_features
                ORDER BY feature_date DESC
                {limit_clause}
            """)  # nosec B608
            result = await self._db.execute(query)
            rows = result.fetchall()
            if not rows:
                return pd.DataFrame()
            cols = ["company_id", "feature_date"] + feature_columns
            return pd.DataFrame(rows, columns=cols)
        except Exception:
            log.exception("Failed to fetch company_features")
            return pd.DataFrame()

    async def _fetch_labels(self) -> pd.DataFrame:
        """Fetch mandate_labels from PostgreSQL."""
        try:
            query = text("""
                SELECT company_id, practice_area, mandate_confirmed_at, is_negative_label
                FROM mandate_labels
            """)
            result = await self._db.execute(query)
            rows = result.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(
                rows,
                columns=[
                    "company_id",
                    "practice_area",
                    "mandate_confirmed_at",
                    "is_negative_label",
                ],
            )
        except Exception:
            log.exception("Failed to fetch mandate_labels")
            return pd.DataFrame()

    async def fetch_clean_company_features(self, feature_columns: list[str]) -> np.ndarray | None:
        """
        Fetch feature vectors for companies with NO mandate labels.
        Used for AnomalyDetector training (clean baseline only).
        """
        try:
            query = text(f"""
                SELECT cf.{", cf.".join(feature_columns)}
                FROM company_features cf
                WHERE cf.company_id NOT IN (
                    SELECT DISTINCT company_id FROM mandate_labels
                    WHERE is_negative_label = false
                )
                LIMIT 10000
            """)  # nosec B608
            result = await self._db.execute(query)
            rows = result.fetchall()
            if not rows:
                return None
            arr = np.array([[float(v or 0) for v in row] for row in rows], dtype=np.float32)
            log.info("Fetched %d clean company feature vectors", len(arr))
            return arr
        except Exception:
            log.exception("Failed to fetch clean company features")
            return None

    async def fetch_mandate_events_for_cooccurrence(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch signal types per mandate event for co-occurrence mining."""
        try:
            query = text("""
                SELECT ml.practice_area, ml.company_id, ml.mandate_confirmed_at,
                       sr.signal_type
                FROM mandate_labels ml
                JOIN signal_records sr ON sr.company_id = ml.company_id
                WHERE ml.is_negative_label = false
                  AND sr.published_at >= ml.mandate_confirmed_at - INTERVAL '90 days'
                  AND sr.published_at <= ml.mandate_confirmed_at
            """)
            result = await self._db.execute(query)
            rows = result.fetchall()

            events_by_pa: dict[str, dict[str, set[str]]] = {}
            for row in rows:
                pa = row[0]
                company_id = row[1]
                signal_type = row[3]
                key = f"{company_id}_{row[2]}"  # company + mandate date
                events_by_pa.setdefault(pa, {}).setdefault(key, set()).add(signal_type)

            # Convert to list of {practice_area, signal_types: [...]}
            output: dict[str, list[dict[str, Any]]] = {}
            for pa, company_events in events_by_pa.items():
                output[pa] = [
                    {"signal_types": list(signals)} for signals in company_events.values()
                ]

            return output
        except Exception:
            log.exception("Failed to fetch mandate events for co-occurrence")
            return {}

    async def fetch_sector_training_data(self, feature_columns: list[str]) -> dict[str, Any] | None:
        """Fetch features + sector labels for sector weight calibration."""
        try:
            query = text(f"""
                SELECT cf.{", cf.".join(feature_columns)}, c.sector,
                       CASE WHEN ml.company_id IS NOT NULL THEN 1 ELSE 0 END as has_mandate
                FROM company_features cf
                JOIN companies c ON c.id = cf.company_id
                LEFT JOIN mandate_labels ml ON ml.company_id = cf.company_id
                    AND ml.is_negative_label = false
                LIMIT 50000
            """)  # nosec B608
            result = await self._db.execute(query)
            rows = result.fetchall()
            if not rows:
                return None

            import pandas as pd

            df = pd.DataFrame(rows, columns=feature_columns + ["sector", "has_mandate"])
            X = df[feature_columns].fillna(0)
            y = df["has_mandate"]
            X["sector"] = df["sector"]

            return {"X": X, "y": y}
        except Exception:
            log.exception("Failed to fetch sector training data")
            return None
