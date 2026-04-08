"""Stacking model for IoMT intrusion detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
from joblib import dump, load
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from core.preprocess import PreprocessBundle, fit_preprocessor, transform_with_preprocessor

try:
    from xgboost import XGBClassifier
except Exception as exc:
    raise ImportError(
        "xgboost is required for this project. Install with: pip install xgboost"
    ) from exc


# ── GRU Network ──────────────────────────────────────────────────────────────

class _GRUNet(nn.Module):
    """Single-layer GRU followed by a fully-connected classifier head."""

    def __init__(self, input_dim: int, hidden_dim: int = 128, num_layers: int = 1):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len=1, features)
        _, h_n = self.gru(x)              # h_n: (num_layers, batch, hidden)
        out = self.fc(h_n[-1])            # last layer hidden state
        return out


class GRUClassifier(BaseEstimator, ClassifierMixin):
    """Sklearn-compatible GRU classifier wrapping PyTorch.

    Accepts 2-D numpy arrays (samples x features).  Internally reshapes to
    (samples, 1, features) -- treating each sample as a single-timestep
    sequence so the GRU learns temporal feature interactions via its gating
    mechanism.
    """

    def __init__(
        self,
        hidden_dim: int = 128,
        num_layers: int = 1,
        epochs: int = 30,
        batch_size: int = 256,
        lr: float = 1e-3,
        random_state: int = 42,
    ):
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.random_state = random_state
        self.classes_ = np.array([0, 1])

    def fit(self, X, y):
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_np = np.asarray(X, dtype=np.float32)
        y_np = np.asarray(y, dtype=np.int64)
        self.classes_ = np.unique(y_np)

        self.net_ = _GRUNet(X_np.shape[1], self.hidden_dim, self.num_layers)
        optimiser = torch.optim.Adam(self.net_.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()

        dataset = torch.utils.data.TensorDataset(
            torch.from_numpy(X_np).unsqueeze(1),   # (N, 1, F)
            torch.from_numpy(y_np),
        )
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True,
        )

        self.net_.train()
        for _ in range(self.epochs):
            for xb, yb in loader:
                optimiser.zero_grad()
                loss = criterion(self.net_(xb), yb)
                loss.backward()
                optimiser.step()
        return self

    def predict_proba(self, X):
        self.net_.eval()
        X_t = torch.from_numpy(np.asarray(X, dtype=np.float32)).unsqueeze(1)
        with torch.no_grad():
            logits = self.net_(X_t)
            probs = torch.softmax(logits, dim=1).numpy()
        return probs

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


# ── Model Bundle ─────────────────────────────────────────────────────────────

@dataclass
class TrainedModelBundle:
    model: Any
    preprocessor: PreprocessBundle


def build_stacking_classifier(random_state: int = 42) -> StackingClassifier:
    estimators = [
        (
            "rf",
            RandomForestClassifier(
                n_estimators=250,
                random_state=random_state,
                n_jobs=-1,
                class_weight="balanced_subsample",
            ),
        ),
        (
            "gru",
            GRUClassifier(
                hidden_dim=128,
                epochs=30,
                batch_size=256,
                lr=1e-3,
                random_state=random_state,
            ),
        ),
        (
            "xgb",
            XGBClassifier(
                n_estimators=300,
                max_depth=8,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=random_state,
                n_jobs=-1,
            ),
        ),
    ]

    return StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(max_iter=500),
        stack_method="predict_proba",
        n_jobs=1,
        passthrough=False,
    )


def train_stacking_model(
    X,
    y,
    preprocessor: PreprocessBundle | None = None,
    test_size: float = 0.2,
    random_state: int = 42,
):
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    preprocessor_bundle = preprocessor or fit_preprocessor(X_train)

    X_train_t = transform_with_preprocessor(X_train, preprocessor_bundle)
    X_test_t = transform_with_preprocessor(X_test, preprocessor_bundle)

    model = build_stacking_classifier(random_state=random_state)
    model.fit(X_train_t, y_train)

    return model, preprocessor_bundle, X_test, X_test_t, y_test


def save_trained_bundle(bundle: TrainedModelBundle, output_path: str = "trained_model.pkl") -> None:
    dump(bundle, output_path)


def load_trained_bundle(path: str = "trained_model.pkl") -> TrainedModelBundle:
    return load(path)
