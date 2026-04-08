"""Real-time adaptive detection loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from core.blockchain import LightweightBlockchain
from core.preprocess import PreprocessBundle, transform_with_preprocessor
from core.trust_engine import TrustEngine


@dataclass
class RealtimeDetectionEngine:
    model: object
    preprocessor: PreprocessBundle
    trust_engine: TrustEngine
    blockchain: LightweightBlockchain
    base_threshold: float = 0.5
    device_id_column: str = "device_id"
    use_trust_weighted_score: bool = True

    def process_record(self, record: Dict) -> Dict:
        device_id = str(record.get(self.device_id_column, "unknown_device"))

        feature_row = pd.DataFrame([record])
        transformed = transform_with_preprocessor(feature_row, self.preprocessor)

        score = float(self.model.predict_proba(transformed)[0][1])
        current_trust = self.trust_engine.get_trust(device_id)
        threshold = self.trust_engine.adaptive_threshold(self.base_threshold, current_trust)
        final_score = score * current_trust if self.use_trust_weighted_score else score
        prediction = int(final_score >= threshold)

        updated_trust = self.trust_engine.update_trust(device_id=device_id, anomaly=prediction)
        block = self.blockchain.append(
            device_id=device_id,
            prediction=prediction,
            trust=updated_trust,
        )

        return {
            "device_id": device_id,
            "anomaly_score": score,
            "final_score": final_score,
            "threshold": threshold,
            "prediction": prediction,
            "trust": updated_trust,
            "block_hash": block["hash"],
        }

    def run_stream(self, records: Iterable[Dict]) -> List[Dict]:
        return [self.process_record(record) for record in records]

    def persist(self, trust_path: str = "trust_state.json", blockchain_path: str = "blockchain.json") -> None:
        self.trust_engine.save(trust_path)
        self.blockchain.save(blockchain_path)
