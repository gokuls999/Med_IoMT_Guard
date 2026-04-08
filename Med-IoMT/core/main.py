"""End-to-end training, evaluation, and realtime demo pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from core.blockchain import LightweightBlockchain
from core.data_loader import load_and_merge_datasets
from core.evaluation import evaluate_predictions
from core.preprocess import build_feature_frame
from core.realtime_engine import RealtimeDetectionEngine
from core.stacking_model import TrainedModelBundle, save_trained_bundle, train_stacking_model
from core.trust_engine import TrustEngine


def parse_args():
    parser = argparse.ArgumentParser(description="Adaptive Trust-Aware Stacking IDS for IoMT")
    parser.add_argument("--unsw_csv", required=True, help="Path to UNSW-NB15 CSV")
    parser.add_argument("--ton_csv", required=True, help="Path to ToN-IoT CSV")
    parser.add_argument("--label_col", default=None, help="Optional explicit label column")
    parser.add_argument("--alpha", type=float, default=0.08)
    parser.add_argument("--beta", type=float, default=0.03)
    parser.add_argument("--base_threshold", type=float, default=0.5)
    parser.add_argument("--demo_records", type=int, default=20, help="How many records to run in realtime loop")
    parser.add_argument(
        "--disable_trust_weighted_score",
        action="store_true",
        help="Disable final_score = trust * stacking_prediction in realtime engine",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    bundle = load_and_merge_datasets(args.unsw_csv, args.ton_csv, label_col=args.label_col)
    X, y, _ = build_feature_frame(bundle.data, label_col=bundle.label_column)

    model, preprocessor_bundle, _X_test_raw, X_test_t, y_test = train_stacking_model(X, y)

    y_pred = model.predict(X_test_t)
    metrics = evaluate_predictions(y_test, y_pred)
    print("Evaluation metrics:")
    print(json.dumps(metrics, indent=2))

    trained_bundle = TrainedModelBundle(model=model, preprocessor=preprocessor_bundle)
    save_trained_bundle(trained_bundle, output_path=str(PROJECT / "trained_model.pkl"))

    trust_engine = TrustEngine(alpha=args.alpha, beta=args.beta)
    blockchain = LightweightBlockchain()
    rt_engine = RealtimeDetectionEngine(
        model=model,
        preprocessor=preprocessor_bundle,
        trust_engine=trust_engine,
        blockchain=blockchain,
        base_threshold=args.base_threshold,
        device_id_column=bundle.device_id_column or "device_id",
        use_trust_weighted_score=not args.disable_trust_weighted_score,
    )

    demo_df = bundle.data.head(args.demo_records).copy()
    demo_records = demo_df.to_dict(orient="records")
    outcomes = rt_engine.run_stream(demo_records)

    print(f"Processed {len(outcomes)} records in realtime loop.")
    print("First 3 outcomes:")
    print(json.dumps(outcomes[:3], indent=2))

    rt_engine.persist(
        trust_path=str(PROJECT / "trust_state.json"),
        blockchain_path=str(PROJECT / "blockchain.json"),
    )
    print("Saved artifacts: trained_model.pkl, trust_state.json, blockchain.json")


if __name__ == "__main__":
    main()
