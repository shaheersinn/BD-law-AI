"""
app/ml/transformer_scorer.py — Transformer temporal attention scorer.

PyTorch multi-head attention over 30-day signal sequence.
Shared encoder → 3 horizon-specific output heads (multi-task learning).

This model earns control of a practice area only when it beats the
BayesianEngine by ≥ ORCHESTRATOR_F1_THRESHOLD on holdout F1.
Training: Azure batch job only. Never train in production.

Architecture:
    Input: [batch, seq_len=30, n_features] time-series of daily feature vectors
    → LearnedPositionalEncoding
    → TransformerEncoder (4 layers, 8 heads, d_model=128)
    → GlobalAttentionPooling (collapses seq_len → 1)
    → Three heads: [30d, 60d, 90d] mandate probability
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812
from torch.utils.data import DataLoader, TensorDataset

from app.config import get_settings
from app.ml.bayesian_engine import FEATURE_COLUMNS, HORIZONS, PRACTICE_AREAS

log = logging.getLogger(__name__)
settings = get_settings()

# ── Hyperparameters ────────────────────────────────────────────────────────────

SEQUENCE_LENGTH: int = 30  # days of feature history used as input
D_MODEL: int = 128  # transformer embedding dimension
N_HEADS: int = 8  # attention heads
N_LAYERS: int = 4  # transformer encoder layers
D_FF: int = 256  # feedforward dimension
DROPOUT: float = 0.1
LEARNING_RATE: float = 1e-4
WEIGHT_DECAY: float = 1e-2
N_EPOCHS: int = 10
BATCH_SIZE: int = 64
WARMUP_STEPS: int = 100


# ── Model definition ───────────────────────────────────────────────────────────


class LearnedPositionalEncoding(nn.Module):
    """Learnable positional encoding. Better than fixed sinusoidal for legal event timing."""

    def __init__(self, seq_len: int, d_model: int) -> None:
        super().__init__()
        self.encoding = nn.Embedding(seq_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, seq_len, d_model]
        seq_len = x.size(1)
        positions = torch.arange(seq_len, device=x.device)
        return x + self.encoding(positions).unsqueeze(0)


class GlobalAttentionPooling(nn.Module):
    """Collapses sequence dimension via learned attention weights."""

    def __init__(self, d_model: int) -> None:
        super().__init__()
        self.attention = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, seq_len, d_model]
        weights = F.softmax(self.attention(x), dim=1)  # [batch, seq_len, 1]
        return (x * weights).sum(dim=1)  # [batch, d_model]


class MandateTransformer(nn.Module):
    """
    Multi-task transformer scorer.
    Input:  [batch, seq_len, n_features]
    Output: [batch, 3] — probabilities for 30d, 60d, 90d mandate horizons
    """

    def __init__(
        self,
        n_features: int,
        seq_len: int = SEQUENCE_LENGTH,
        d_model: int = D_MODEL,
        n_heads: int = N_HEADS,
        n_layers: int = N_LAYERS,
        d_ff: int = D_FF,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        self.input_projection = nn.Linear(n_features, d_model)
        self.pos_encoding = LearnedPositionalEncoding(seq_len, d_model)
        self.input_norm = nn.LayerNorm(d_model)
        self.input_dropout = nn.Dropout(dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,  # [batch, seq, d_model]
            norm_first=True,  # Pre-LN: more stable training
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.pool = GlobalAttentionPooling(d_model)

        # Three horizon-specific heads (shared encoder → separate classification heads)
        for horizon in HORIZONS:
            setattr(
                self,
                f"head_{horizon}d",
                nn.Sequential(
                    nn.Linear(d_model, 64),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(64, 1),
                ),
            )

    def forward(self, x: torch.Tensor) -> dict[int, torch.Tensor]:
        """
        Args:
            x: [batch, seq_len, n_features] — time-series feature matrix
        Returns:
            dict mapping horizon → [batch] probability tensor
        """
        # Project to model dimension
        h = self.input_projection(x)  # [batch, seq_len, d_model]
        h = self.pos_encoding(h)
        h = self.input_norm(h)
        h = self.input_dropout(h)

        # Transformer encoding
        h = self.transformer(h)  # [batch, seq_len, d_model]

        # Pool to single vector
        h = self.pool(h)  # [batch, d_model]

        # Horizon heads
        outputs = {}
        for horizon in HORIZONS:
            head = getattr(self, f"head_{horizon}d")
            outputs[horizon] = torch.sigmoid(head(h).squeeze(-1))  # [batch]

        return outputs


# ── Scorer (inference wrapper) ─────────────────────────────────────────────────


class TransformerScorer:
    """
    Wrapper around MandateTransformer for production inference.

    Loads model weights from disk. Call .load() at API startup.
    Only used after orchestrator confirms this model beats BayesianEngine
    on holdout F1 for this practice area.
    """

    def __init__(self, practice_area: str) -> None:
        if practice_area not in PRACTICE_AREAS:
            raise ValueError(f"Unknown practice area: {practice_area}")
        self.practice_area = practice_area
        self._model: MandateTransformer | None = None
        self._device = torch.device("cpu")
        self._model_version = "unloaded"
        self._loaded = False

    def load(self, model_dir: Path | None = None) -> None:
        """Load model weights from disk."""
        if model_dir is None:
            model_dir = Path(settings.models_dir) / "transformer" / self.practice_area

        weights_path = model_dir / "model.pt"
        if not weights_path.exists():
            log.warning(
                "TransformerScorer %s: weights not found at %s", self.practice_area, weights_path
            )
            return

        n_features = len(FEATURE_COLUMNS)
        self._model = MandateTransformer(n_features=n_features)
        self._model.load_state_dict(torch.load(weights_path, map_location=self._device))
        self._model.eval()

        version_path = model_dir / "version.txt"
        if version_path.exists():
            self._model_version = version_path.read_text().strip()

        self._loaded = True
        log.info(
            "TransformerScorer %s loaded (version=%s)", self.practice_area, self._model_version
        )

    def score(self, sequence: list[dict[str, float]]) -> dict[int, float]:
        """
        Score a single company using its 30-day feature history.

        Args:
            sequence: List of daily feature dicts (most recent last).
                      Padded to SEQUENCE_LENGTH with zeros if shorter.
        Returns:
            dict: {30: probability, 60: probability, 90: probability}
        """
        if not self._loaded or self._model is None:
            raise RuntimeError(
                f"TransformerScorer {self.practice_area} not loaded. Call .load() first."
            )

        # Build sequence tensor
        x = _sequence_to_tensor(sequence, SEQUENCE_LENGTH)  # [1, seq_len, n_features]

        t0 = time.perf_counter()
        with torch.no_grad():
            outputs = self._model(x)

        scores = {
            horizon: float(np.clip(outputs[horizon].item(), 0.001, 0.999)) for horizon in HORIZONS
        }
        log.debug(
            "TransformerScorer %s inference: %.1fms",
            self.practice_area,
            (time.perf_counter() - t0) * 1000,
        )
        return scores

    @staticmethod
    def train(
        practice_area: str,
        X_seq_train: np.ndarray,  # noqa: N803  # [n_samples, seq_len, n_features]
        y_train: dict[int, np.ndarray],  # {30: labels, 60: labels, 90: labels}
        X_seq_holdout: np.ndarray,  # noqa: N803
        y_holdout: dict[int, np.ndarray],
        output_dir: Path,
        n_epochs: int = N_EPOCHS,
    ) -> dict[str, Any]:
        """
        Train MandateTransformer. Called from Azure batch job only.

        Returns:
            Training summary with holdout metrics per horizon.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        n_features = X_seq_train.shape[2]
        model = MandateTransformer(n_features=n_features)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)

        # Build DataLoader
        X_t = torch.tensor(X_seq_train, dtype=torch.float32)
        y_tensors = {h: torch.tensor(y, dtype=torch.float32) for h, y in y_train.items()}
        dataset = TensorDataset(X_t, *[y_tensors[h] for h in HORIZONS])
        loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)

        optimizer = torch.optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=n_epochs * len(loader)
        )

        log.info(
            "Training TransformerScorer %s on %s (%d samples, %d epochs)",
            practice_area,
            device,
            len(X_seq_train),
            n_epochs,
        )

        best_val_loss = float("inf")
        training_history: list[dict[str, float]] = []

        for epoch in range(n_epochs):
            model.train()
            epoch_loss = 0.0

            for batch in loader:
                X_b = batch[0].to(device)
                y_b = {h: batch[i + 1].to(device) for i, h in enumerate(HORIZONS)}

                optimizer.zero_grad()
                outputs = model(X_b)

                # Multi-task loss: sum of weighted BCE per horizon
                loss = torch.tensor(0.0, device=device)
                for h in HORIZONS:
                    loss = loss + F.binary_cross_entropy(
                        outputs[h], y_b[h], weight=None, reduction="mean"
                    )

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                epoch_loss += loss.item()

            # Validation pass
            model.eval()
            val_loss = _evaluate_transformer_loss(model, X_seq_holdout, y_holdout, device)
            epoch_avg = epoch_loss / max(len(loader), 1)

            log.info(
                "Epoch %d/%d — train_loss=%.4f val_loss=%.4f",
                epoch + 1,
                n_epochs,
                epoch_avg,
                val_loss,
            )
            training_history.append(
                {"epoch": epoch + 1, "train_loss": epoch_avg, "val_loss": val_loss}
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), output_dir / "model_best.pt")

        # Load best and compute F1 per horizon
        model.load_state_dict(torch.load(output_dir / "model_best.pt", map_location=device))
        model.eval()

        holdout_metrics = _compute_transformer_holdout_metrics(
            model, X_seq_holdout, y_holdout, device
        )
        log.info("TransformerScorer %s holdout metrics: %s", practice_area, holdout_metrics)

        # Save final model (same as best)
        torch.save(model.state_dict(), output_dir / "model.pt")

        import datetime

        version = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (output_dir / "version.txt").write_text(version)

        return {
            "practice_area": practice_area,
            "epochs": n_epochs,
            "best_val_loss": best_val_loss,
            "holdout_metrics": holdout_metrics,
            "training_history": training_history,
            "artifact_path": str(output_dir / "model.pt"),
        }


# ── Helpers ────────────────────────────────────────────────────────────────────


def _sequence_to_tensor(
    sequence: list[dict[str, float]],
    seq_len: int,
) -> torch.Tensor:
    """Convert a list of feature dicts to a padded [1, seq_len, n_features] tensor."""
    n_features = len(FEATURE_COLUMNS)
    arr = np.zeros((seq_len, n_features), dtype=np.float32)

    # Fill from the end (most recent last)
    for i, row in enumerate(sequence[-seq_len:]):
        offset = max(seq_len - len(sequence), 0) + i
        arr[offset] = [row.get(col, 0.0) for col in FEATURE_COLUMNS]

    return torch.tensor(arr, dtype=torch.float32).unsqueeze(0)


def _evaluate_transformer_loss(
    model: MandateTransformer,
    X_seq: np.ndarray,  # noqa: N803
    y: dict[int, np.ndarray],
    device: torch.device,
) -> float:
    """Compute multi-task validation loss."""
    X_t = torch.tensor(X_seq, dtype=torch.float32).to(device)
    y_t = {h: torch.tensor(labels, dtype=torch.float32).to(device) for h, labels in y.items()}

    with torch.no_grad():
        outputs = model(X_t)
        total_loss = sum(F.binary_cross_entropy(outputs[h], y_t[h]).item() for h in HORIZONS)
    return total_loss / len(HORIZONS)


def _compute_transformer_holdout_metrics(
    model: MandateTransformer,
    X_seq: np.ndarray,  # noqa: N803
    y: dict[int, np.ndarray],
    device: torch.device,
) -> dict[str, Any]:
    """F1 and PR-AUC on holdout per horizon."""
    from sklearn.metrics import average_precision_score, f1_score

    X_t = torch.tensor(X_seq, dtype=torch.float32).to(device)
    with torch.no_grad():
        outputs = model(X_t)

    metrics: dict[str, Any] = {}
    for h in HORIZONS:
        probs = outputs[h].cpu().numpy()
        labels = y[h]
        preds = (probs >= 0.5).astype(int)
        metrics[f"f1_{h}d"] = float(f1_score(labels, preds, zero_division=0))
        if labels.sum() > 0:
            metrics[f"pr_auc_{h}d"] = float(average_precision_score(labels, probs))
        else:
            metrics[f"pr_auc_{h}d"] = 0.0

    return metrics
