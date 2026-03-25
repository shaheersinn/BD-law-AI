"""
app/ml/anomaly_detector.py — Enhancement 9: Autoencoder anomaly detection.

Trained ONLY on companies with no mandate labels (clean baseline).
High reconstruction error = company's feature vector deviates from normal
baseline → anomalous behaviour worth investigating.

anomaly_score stored per company per day in scoring_results.
Threshold: > 2 standard deviations above mean reconstruction error.

Training: Azure batch job only (call AnomalyDetector.train()).
Inference: AnomalyDetector().score(feature_vector) → anomaly_score [0, 1]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

log = logging.getLogger(__name__)

ANOMALY_STD_THRESHOLD: float = 2.0    # flag if reconstruction error > mean + 2*std
AUTOENCODER_HIDDEN_DIMS: list[int] = [64, 32, 16, 32, 64]   # symmetric bottleneck at 16
TRAINING_EPOCHS: int = 50
BATCH_SIZE: int = 128
LEARNING_RATE: float = 1e-3


def _build_autoencoder(n_features: int):  # type: ignore[return]
    """Build PyTorch autoencoder. Imported lazily to keep startup fast."""
    import torch
    import torch.nn as nn

    dims = [n_features] + AUTOENCODER_HIDDEN_DIMS + [n_features]
    layers = []
    for i in range(len(dims) - 1):
        layers.append(nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            layers.append(nn.ReLU())
        else:
            layers.append(nn.Sigmoid())  # output in [0,1] since features are normalised

    return nn.Sequential(*layers)


class AnomalyDetector:
    """
    Autoencoder-based anomaly detector for company feature vectors.

    Usage:
        detector = AnomalyDetector()
        detector.load()
        anomaly_score = detector.score(feature_dict)  # 0.0 = normal, 1.0 = very anomalous
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None    # torch.nn.Module
        self._scaler: Optional[Any] = None   # sklearn StandardScaler
        self._threshold: float = 0.0         # mean + 2*std reconstruction error
        self._mean_error: float = 0.0
        self._std_error: float = 0.0
        self._loaded = False

    def load(self, model_dir: Optional[Path] = None) -> None:
        """Load trained autoencoder from disk."""
        import torch

        if model_dir is None:
            from app.config import get_settings
            settings = get_settings()
            model_dir = Path(settings.models_dir) / "anomaly"

        weights_path = model_dir / "autoencoder.pt"
        scaler_path = model_dir / "scaler.pkl"
        stats_path = model_dir / "stats.pkl"

        if not weights_path.exists():
            log.warning("AnomalyDetector: weights not found at %s", weights_path)
            return

        from app.ml.bayesian_engine import FEATURE_COLUMNS
        n_features = len(FEATURE_COLUMNS)
        self._model = _build_autoencoder(n_features)
        self._model.load_state_dict(
            torch.load(weights_path, map_location=torch.device("cpu"))
        )
        self._model.eval()  # type: ignore[union-attr]

        if scaler_path.exists():
            self._scaler = joblib.load(scaler_path)

        if stats_path.exists():
            stats = joblib.load(stats_path)
            self._threshold = stats.get("threshold", 0.0)
            self._mean_error = stats.get("mean_error", 0.0)
            self._std_error = stats.get("std_error", 0.0)

        self._loaded = True
        log.info(
            "AnomalyDetector loaded. threshold=%.4f (mean=%.4f, std=%.4f)",
            self._threshold, self._mean_error, self._std_error,
        )

    def score(self, features: dict[str, float]) -> float:
        """
        Score a single company feature vector.

        Args:
            features: Feature dict (FEATURE_COLUMNS keys).
        Returns:
            anomaly_score in [0, 1]:
                0.0 = perfectly normal reconstruction
                1.0 = reconstruction error >> threshold (highly anomalous)
        """
        if not self._loaded or self._model is None:
            return 0.0

        import torch
        from app.ml.bayesian_engine import FEATURE_COLUMNS

        x = np.array(
            [features.get(col, 0.0) for col in FEATURE_COLUMNS],
            dtype=np.float32,
        ).reshape(1, -1)

        if self._scaler is not None:
            try:
                x = self._scaler.transform(x).astype(np.float32)
            except Exception:
                log.warning("AnomalyDetector: scaler transform failed, using raw features")

        x_tensor = torch.tensor(x, dtype=torch.float32)

        with torch.no_grad():
            reconstructed = self._model(x_tensor)

        reconstruction_error = float(
            torch.mean((x_tensor - reconstructed) ** 2).item()
        )

        if self._std_error < 1e-8:
            return 0.0

        # Normalise to [0, 1] using softcapped z-score
        z = (reconstruction_error - self._mean_error) / self._std_error
        # sigmoid(z - threshold_z): values above threshold map to > 0.5
        threshold_z = ANOMALY_STD_THRESHOLD
        anomaly_score = float(1.0 / (1.0 + np.exp(-(z - threshold_z))))
        return float(np.clip(anomaly_score, 0.0, 1.0))

    def score_batch(self, feature_rows: list[dict[str, float]]) -> list[float]:
        """Score multiple companies in one vectorised pass."""
        if not self._loaded or self._model is None:
            return [0.0] * len(feature_rows)

        import torch
        from app.ml.bayesian_engine import FEATURE_COLUMNS

        X = np.array(
            [[row.get(col, 0.0) for col in FEATURE_COLUMNS] for row in feature_rows],
            dtype=np.float32,
        )

        if self._scaler is not None:
            try:
                X = self._scaler.transform(X).astype(np.float32)
            except Exception:
                pass

        X_t = torch.tensor(X, dtype=torch.float32)

        with torch.no_grad():
            reconstructed = self._model(X_t)

        errors = torch.mean((X_t - reconstructed) ** 2, dim=1).numpy()

        if self._std_error < 1e-8:
            return [0.0] * len(feature_rows)

        zscores = (errors - self._mean_error) / self._std_error
        threshold_z = ANOMALY_STD_THRESHOLD
        scores = 1.0 / (1.0 + np.exp(-(zscores - threshold_z)))
        return [float(np.clip(s, 0.0, 1.0)) for s in scores]

    @staticmethod
    def train(
        X_clean: np.ndarray,    # Feature matrix from companies with NO mandate labels
        output_dir: Path,
        n_epochs: int = TRAINING_EPOCHS,
    ) -> dict[str, Any]:
        """
        Train autoencoder on clean (no-mandate) company feature vectors.

        CRITICAL: X_clean must contain ONLY companies with no mandate_labels.
        Including distressed companies contaminates the baseline.

        Args:
            X_clean:    [n_samples, n_features] — clean company features.
            output_dir: Where to save model + scaler + stats.
            n_epochs:   Training epochs.
        Returns:
            Training summary with reconstruction error stats.
        """
        import torch
        import torch.nn as nn
        from sklearn.preprocessing import StandardScaler
        from torch.utils.data import DataLoader, TensorDataset

        output_dir.mkdir(parents=True, exist_ok=True)

        if len(X_clean) < 100:
            raise ValueError(
                f"AnomalyDetector.train: need ≥ 100 clean samples, got {len(X_clean)}"
            )

        # Normalise features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean).astype(np.float32)
        joblib.dump(scaler, output_dir / "scaler.pkl")

        n_features = X_scaled.shape[1]
        model = _build_autoencoder(n_features)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)

        dataset = TensorDataset(torch.tensor(X_scaled))
        loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
        criterion = nn.MSELoss()

        log.info("Training AnomalyDetector on %d clean samples (%s)", len(X_clean), device)

        for epoch in range(n_epochs):
            model.train()
            epoch_loss = 0.0
            for (x_b,) in loader:
                x_b = x_b.to(device)
                optimizer.zero_grad()
                reconstructed = model(x_b)
                loss = criterion(reconstructed, x_b)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            if (epoch + 1) % 10 == 0:
                log.info("AnomalyDetector epoch %d/%d loss=%.5f", epoch + 1, n_epochs, epoch_loss / len(loader))

        # Compute reconstruction error stats on training set (for threshold)
        model.eval()
        X_t = torch.tensor(X_scaled).to(device)
        with torch.no_grad():
            reconstructed = model(X_t)
        errors = torch.mean((X_t - reconstructed) ** 2, dim=1).cpu().numpy()

        mean_err = float(np.mean(errors))
        std_err = float(np.std(errors))
        threshold = mean_err + ANOMALY_STD_THRESHOLD * std_err

        log.info(
            "AnomalyDetector: mean_err=%.5f std=%.5f threshold=%.5f",
            mean_err, std_err, threshold,
        )

        # Save model + stats
        torch.save(model.state_dict(), output_dir / "autoencoder.pt")
        joblib.dump(
            {"mean_error": mean_err, "std_error": std_err, "threshold": threshold},
            output_dir / "stats.pkl",
        )

        return {
            "n_clean_samples": len(X_clean),
            "mean_reconstruction_error": mean_err,
            "std_reconstruction_error": std_err,
            "anomaly_threshold": threshold,
            "n_epochs": n_epochs,
            "artifact_path": str(output_dir / "autoencoder.pt"),
        }


# Module-level singleton
_ANOMALY_DETECTOR: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    global _ANOMALY_DETECTOR
    if _ANOMALY_DETECTOR is None:
        _ANOMALY_DETECTOR = AnomalyDetector()
        _ANOMALY_DETECTOR.load()
    return _ANOMALY_DETECTOR
