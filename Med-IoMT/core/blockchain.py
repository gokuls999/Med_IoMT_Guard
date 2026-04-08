"""Lightweight blockchain ledger for prediction events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class LightweightBlockchain:
    chain: List[Dict] = field(default_factory=list)

    @staticmethod
    def _hash_payload(prev_hash: str, device_id: str, prediction: int, trust: float, timestamp: str) -> str:
        payload = f"{prev_hash}{device_id}{prediction}{trust:.6f}{timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append(self, device_id: str, prediction: int, trust: float, timestamp: str | None = None) -> Dict:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        prev_hash = self.chain[-1]["hash"] if self.chain else "0"
        block_hash = self._hash_payload(prev_hash, device_id, int(prediction), float(trust), ts)

        block = {
            "index": len(self.chain),
            "timestamp": ts,
            "device_id": str(device_id),
            "prediction": int(prediction),
            "trust": float(trust),
            "prev_hash": prev_hash,
            "hash": block_hash,
        }
        self.chain.append(block)
        return block

    def verify(self) -> bool:
        prev_hash = "0"
        for block in self.chain:
            expected_hash = self._hash_payload(
                prev_hash,
                block["device_id"],
                int(block["prediction"]),
                float(block["trust"]),
                block["timestamp"],
            )
            if block.get("prev_hash") != prev_hash or block.get("hash") != expected_hash:
                return False
            prev_hash = block["hash"]
        return True

    def save(self, output_path: str = "blockchain.json") -> None:
        Path(output_path).write_text(json.dumps(self.chain, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, input_path: str = "blockchain.json") -> "LightweightBlockchain":
        path = Path(input_path)
        if not path.exists():
            return cls()
        chain = json.loads(path.read_text(encoding="utf-8"))
        return cls(chain=chain)
