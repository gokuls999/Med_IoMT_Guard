"""Adaptive trust scoring engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class TrustEngine:
    alpha: float = 0.08
    beta: float = 0.03
    default_trust: float = 0.5
    trust_state: Dict[str, float] = field(default_factory=dict)

    def get_trust(self, device_id: str) -> float:
        return float(self.trust_state.get(device_id, self.default_trust))

    def update_trust(self, device_id: str, anomaly: int) -> float:
        current = self.get_trust(device_id)
        normal = 1 - int(anomaly)
        updated = current - (self.alpha * int(anomaly)) + (self.beta * normal)
        updated = max(0.0, min(1.0, updated))
        self.trust_state[device_id] = updated
        return updated

    @staticmethod
    def adaptive_threshold(base_threshold: float, trust: float, floor: float = 0.25) -> float:
        raw = base_threshold * (1.0 - trust)
        return max(floor, min(1.0, raw))

    def save(self, output_path: str = "trust_state.json") -> None:
        Path(output_path).write_text(json.dumps(self.trust_state, indent=2), encoding="utf-8")

    @classmethod
    def load(
        cls,
        input_path: str = "trust_state.json",
        alpha: float = 0.08,
        beta: float = 0.03,
        default_trust: float = 0.5,
    ) -> "TrustEngine":
        path = Path(input_path)
        if not path.exists():
            return cls(alpha=alpha, beta=beta, default_trust=default_trust)

        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(alpha=alpha, beta=beta, default_trust=default_trust, trust_state=data)
