from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SystemConfig:
    total_events: int = 5000
    num_devices: int = 140
    num_patients: int = 900
    random_seed: int = 42
    start_bed_occupancy_ratio: float = 0.62
    department_bed_capacity: Dict[str, int] = field(
        default_factory=lambda: {
            "Emergency": 40,
            "ICU": 28,
            "Ward": 120,
            "Radiology": 18,
            "Pharmacy": 14,
            "Cardiology": 32,
        }
    )
    use_external_attack_plan: bool = True
    external_attack_plan: str = "iomt_attack_lab/generated/attack_plan.json"
