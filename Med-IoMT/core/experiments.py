"""Research experiment runner: baseline vs adaptive IDS with plots and JSON outputs."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from core.blockchain import LightweightBlockchain
from core.data_loader import load_and_merge_datasets
from core.evaluation import evaluate_predictions, measure_prediction_latency, to_jsonable
from core.preprocess import DROP_COLUMNS, build_feature_frame, fit_preprocessor, transform_with_preprocessor
from core.realtime_engine import RealtimeDetectionEngine
from core.stacking_model import build_stacking_classifier
from core.trust_engine import TrustEngine


def _simulate_variant(
    model,
    preprocessor_bundle,
    records,
    device_id_column,
    base_threshold,
    alpha,
    beta,
    use_trust_weighted_score,
):
    engine = RealtimeDetectionEngine(
        model=model,
        preprocessor=preprocessor_bundle,
        trust_engine=TrustEngine(alpha=alpha, beta=beta),
        blockchain=LightweightBlockchain(),
        base_threshold=base_threshold,
        device_id_column=device_id_column,
        use_trust_weighted_score=use_trust_weighted_score,
    )

    outputs = []
    per_record_ms = []
    for record in records:
        start = time.perf_counter()
        outputs.append(engine.process_record(record))
        per_record_ms.append((time.perf_counter() - start) * 1000.0)

    return outputs, {
        "latency_mean_ms": float(np.mean(per_record_ms)) if per_record_ms else 0.0,
        "latency_std_ms": float(np.std(per_record_ms)) if per_record_ms else 0.0,
        "latency_min_ms": float(np.min(per_record_ms)) if per_record_ms else 0.0,
        "latency_max_ms": float(np.max(per_record_ms)) if per_record_ms else 0.0,
        "records": int(len(per_record_ms)),
    }


def _cross_dataset_experiment(merged: pd.DataFrame, label_col: str, random_state: int):
    unsw = merged[merged["dataset_source"] == "unsw_nb15"].copy()
    ton = merged[merged["dataset_source"] == "ton_iot"].copy()

    results = {}
    scenarios = [
        ("train_unsw_test_ton", unsw, ton),
        ("train_ton_test_unsw", ton, unsw),
    ]

    for name, train_df, test_df in scenarios:
        train_features = set(train_df.columns) - DROP_COLUMNS - {label_col}
        test_features = set(test_df.columns) - DROP_COLUMNS - {label_col}
        common_features = []
        for col in sorted(train_features.intersection(test_features)):
            if train_df[col].notna().any() and test_df[col].notna().any():
                common_features.append(col)
        if not common_features:
            results[name] = {"error": "No common feature columns between train/test domains."}
            continue

        X_train = train_df[common_features].copy()
        y_train = train_df[label_col].astype(int).to_numpy()
        X_test = test_df[common_features].copy()
        y_test = test_df[label_col].astype(int).to_numpy()

        preprocessor_bundle = fit_preprocessor(X_train)
        X_train_t = transform_with_preprocessor(X_train, preprocessor_bundle)
        X_test_t = transform_with_preprocessor(X_test, preprocessor_bundle)

        model = build_stacking_classifier(random_state=random_state)
        model.fit(X_train_t, y_train)

        y_pred = model.predict(X_test_t)
        metrics = evaluate_predictions(y_test, y_pred)
        metrics["train_samples"] = int(len(train_df))
        metrics["test_samples"] = int(len(test_df))
        results[name] = to_jsonable(metrics)

    return results


def _plot_variant_metrics(output_dir: Path, metric_table: dict):
    variants = list(metric_table.keys())
    metric_names = ["accuracy", "precision", "recall", "f1", "false_positive_rate"]

    x = np.arange(len(metric_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    for idx, variant in enumerate(variants):
        vals = [metric_table[variant][m] for m in metric_names]
        ax.bar(x + (idx - 1) * width, vals, width=width, label=variant)

    ax.set_xticks(x)
    ax.set_xticklabels(metric_names, rotation=20)
    ax.set_ylim(0, 1)
    ax.set_title("Baseline vs Adaptive IDS Metrics")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    fig.savefig(output_dir / "metrics_comparison.png", dpi=160)
    plt.close(fig)


def _plot_trust_evolution(output_dir: Path, outputs: list[dict], max_points: int = 300):
    if not outputs:
        return

    trust_series = [o["trust"] for o in outputs[:max_points]]
    score_series = [o["final_score"] for o in outputs[:max_points]]
    threshold_series = [o["threshold"] for o in outputs[:max_points]]

    x = np.arange(len(trust_series))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(x, trust_series, label="Trust", linewidth=2)
    ax.plot(x, score_series, label="Final Score", linewidth=1.5)
    ax.plot(x, threshold_series, label="Adaptive Threshold", linewidth=1.5)
    ax.set_title("Trust / Score / Threshold Evolution")
    ax.set_xlabel("Record Index")
    ax.set_ylabel("Value")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.25)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "trust_evolution.png", dpi=160)
    plt.close(fig)


def parse_args():
    parser = argparse.ArgumentParser(description="Run strict research experiments for adaptive IoMT IDS")
    parser.add_argument("--unsw_csv", required=True)
    parser.add_argument("--ton_csv", required=True)
    parser.add_argument("--label_col", default=None)
    parser.add_argument("--sample_size", type=int, default=60000, help="Total merged samples for experiments")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--base_threshold", type=float, default=0.5)
    parser.add_argument("--alpha", type=float, default=0.08)
    parser.add_argument("--beta", type=float, default=0.03)
    parser.add_argument("--random_state", type=int, default=42)
    parser.add_argument("--output_dir", default="research_outputs")
    parser.add_argument("--skip_cross_dataset", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = load_and_merge_datasets(args.unsw_csv, args.ton_csv, label_col=args.label_col)
    merged = bundle.data

    if args.sample_size and args.sample_size < len(merged):
        merged, _ = train_test_split(
            merged,
            train_size=args.sample_size,
            stratify=merged[bundle.label_column],
            random_state=args.random_state,
        )

    X, y, _ = build_feature_frame(merged, label_col=bundle.label_column)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=y,
    )

    preprocessor_bundle = fit_preprocessor(X_train)
    X_train_t = transform_with_preprocessor(X_train, preprocessor_bundle)
    X_test_t = transform_with_preprocessor(X_test, preprocessor_bundle)

    model = build_stacking_classifier(random_state=args.random_state)
    model.fit(X_train_t, y_train)

    prob = model.predict_proba(X_test_t)[:, 1]
    baseline_pred = (prob >= args.base_threshold).astype(int)
    baseline_metrics = evaluate_predictions(y_test, baseline_pred)
    baseline_latency = measure_prediction_latency(model, X_test_t, n_runs=5)

    test_records = X_test.copy()
    if bundle.device_id_column not in test_records.columns:
        test_records[bundle.device_id_column or "device_id"] = "unknown_device"
    records = test_records.to_dict(orient="records")

    adaptive_outputs, adaptive_latency = _simulate_variant(
        model=model,
        preprocessor_bundle=preprocessor_bundle,
        records=records,
        device_id_column=bundle.device_id_column or "device_id",
        base_threshold=args.base_threshold,
        alpha=args.alpha,
        beta=args.beta,
        use_trust_weighted_score=False,
    )
    adaptive_pred = np.array([o["prediction"] for o in adaptive_outputs], dtype=int)
    adaptive_metrics = evaluate_predictions(y_test, adaptive_pred)

    full_outputs, full_latency = _simulate_variant(
        model=model,
        preprocessor_bundle=preprocessor_bundle,
        records=records,
        device_id_column=bundle.device_id_column or "device_id",
        base_threshold=args.base_threshold,
        alpha=args.alpha,
        beta=args.beta,
        use_trust_weighted_score=True,
    )
    full_pred = np.array([o["prediction"] for o in full_outputs], dtype=int)
    full_metrics = evaluate_predictions(y_test, full_pred)

    result = {
        "config": {
            "sample_size": int(len(merged)),
            "test_size": float(args.test_size),
            "base_threshold": float(args.base_threshold),
            "alpha": float(args.alpha),
            "beta": float(args.beta),
            "random_state": int(args.random_state),
        },
        "baseline_static": {**to_jsonable(baseline_metrics), **to_jsonable(baseline_latency)},
        "adaptive_threshold_only": {**to_jsonable(adaptive_metrics), **to_jsonable(adaptive_latency)},
        "adaptive_threshold_trust_weighted": {**to_jsonable(full_metrics), **to_jsonable(full_latency)},
    }

    if not args.skip_cross_dataset:
        result["cross_dataset"] = _cross_dataset_experiment(merged, bundle.label_column, args.random_state)

    (output_dir / "experiment_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    metric_table = {
        "baseline": result["baseline_static"],
        "adaptive": result["adaptive_threshold_only"],
        "adaptive+trust": result["adaptive_threshold_trust_weighted"],
    }
    _plot_variant_metrics(output_dir, metric_table)
    _plot_trust_evolution(output_dir, full_outputs)

    (output_dir / "adaptive_outputs_sample.json").write_text(
        json.dumps(full_outputs[:300], indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))
    print(f"Saved research outputs to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
