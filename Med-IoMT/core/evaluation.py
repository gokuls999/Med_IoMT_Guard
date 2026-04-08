"""Evaluation utilities for IDS model performance and experiments."""

from __future__ import annotations

import time
from typing import Dict

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score


def evaluate_predictions(y_true, y_pred) -> Dict[str, float]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    total_negatives = tn + fp
    fpr = float(fp / total_negatives) if total_negatives else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_positive_rate": fpr,
        "true_positives": int(tp),
        "false_negatives": int(fn),
    }


def measure_prediction_latency(model, X, n_runs: int = 5) -> Dict[str, float]:
    X = np.asarray(X)
    timings_ms = []
    for _ in range(n_runs):
        start = time.perf_counter()
        _ = model.predict_proba(X)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        timings_ms.append(elapsed_ms)

    return {
        "latency_mean_ms": float(np.mean(timings_ms)),
        "latency_std_ms": float(np.std(timings_ms)),
        "latency_min_ms": float(np.min(timings_ms)),
        "latency_max_ms": float(np.max(timings_ms)),
        "runs": int(n_runs),
        "samples": int(len(X)),
    }


def to_jsonable(metrics: Dict) -> Dict:
    out = {}
    for k, v in metrics.items():
        if isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.floating,)):
            out[k] = float(v)
        else:
            out[k] = v
    return out
