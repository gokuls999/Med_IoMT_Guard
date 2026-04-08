from __future__ import annotations

from copy import deepcopy


ATTACK_LIBRARY = {
    "dos": {
        "label": "DoS Flood",
        "description": "Network flood that increases latency and packet bursts.",
        "default_intensity": 0.75,
    },
    "spoof": {
        "label": "Device Spoofing",
        "description": "Impersonates trusted medical devices and raises auth anomalies.",
        "default_intensity": 0.65,
    },
    "tamper": {
        "label": "Data Tampering",
        "description": "Manipulates telemetry fields and command-risk features.",
        "default_intensity": 0.7,
    },
    "replay": {
        "label": "Replay Attack",
        "description": "Reuses previously valid request patterns with stale context.",
        "default_intensity": 0.6,
    },
    "ransomware": {
        "label": "Ransomware Burst",
        "description": "Creates endpoint stress and service degradation behavior.",
        "default_intensity": 0.8,
    },
}


DEFAULT_DEPARTMENTS = ["Emergency", "ICU", "Ward", "Radiology", "Pharmacy", "Cardiology"]
DEFAULT_DEVICE_TYPES = [
    "wearable_monitor",
    "infusion_pump",
    "ventilator",
    "bedside_sensor",
    "imaging_gateway",
]


def scenario_template(name: str = "hospital_attack_scenario") -> dict:
    return {
        "scenario_name": name,
        "created_at": "",
        "total_events": 5000,
        "seed": 42,
        "attacks": [],
    }


def get_attack_library() -> dict:
    return deepcopy(ATTACK_LIBRARY)
