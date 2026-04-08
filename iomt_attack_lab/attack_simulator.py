from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from attack_profiles import DEFAULT_DEPARTMENTS, DEFAULT_DEVICE_TYPES


def load_attack_plan(path: str | Path) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def save_attack_plan(plan: dict, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = dict(plan)
    out["created_at"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return p


def _clip01(values: pd.Series) -> pd.Series:
    return values.clip(0.0, 1.0)


def _attack_mask(df: pd.DataFrame, attack: dict, total_events: int) -> pd.Series:
    start_pct = float(attack.get("start_pct", 0.0))
    end_pct = float(attack.get("end_pct", 1.0))
    start_i = int(max(0, min(total_events - 1, round(start_pct * total_events))))
    end_i = int(max(start_i, min(total_events - 1, round(end_pct * total_events))))

    idx = pd.Series(np.arange(total_events), index=df.index)
    mask = idx.between(start_i, end_i, inclusive="both")

    target_depts = set(attack.get("target_departments") or [])
    target_types = set(attack.get("target_device_types") or [])
    if target_depts:
        mask &= df["department"].isin(target_depts)
    if target_types:
        mask &= df["device_type"].isin(target_types)
    return mask


def apply_attack_plan(events: pd.DataFrame, plan: dict) -> tuple[pd.DataFrame, dict]:
    df = events.copy()
    total_events = len(df)
    if total_events == 0:
        return df, {"total_attacks_injected": 0, "attack_breakdown": {}}

    if "attack_active" not in df.columns:
        df["attack_active"] = 0
    if "attack_type" not in df.columns:
        df["attack_type"] = "none"
    if "attack_intensity" not in df.columns:
        df["attack_intensity"] = 0.0

    rng = np.random.default_rng(int(plan.get("seed", 42)))
    attacks = plan.get("attacks", [])
    breakdown: dict[str, int] = {}

    for attack in attacks:
        attack_type = str(attack.get("attack_type", "")).strip().lower()
        if not attack_type:
            continue
        intensity = float(np.clip(float(attack.get("intensity", 0.5)), 0.05, 1.0))
        mask = _attack_mask(df, attack, total_events)
        n = int(mask.sum())
        if n == 0:
            continue

        df.loc[mask, "attack_active"] = 1
        df.loc[mask, "attack_type"] = attack_type
        df.loc[mask, "attack_intensity"] = intensity

        noise = pd.Series(rng.normal(0, 1, size=n), index=df[mask].index)

        if attack_type == "dos":
            df.loc[mask, "latency_ms"] = (df.loc[mask, "latency_ms"] * (1.3 + 1.7 * intensity)).clip(5, 2500)
            df.loc[mask, "packet_rate"] = (df.loc[mask, "packet_rate"] * (1.8 + 2.2 * intensity)).clip(20, 5000)
            df.loc[mask, "wait_min"] = (df.loc[mask, "wait_min"] * (1.1 + 0.7 * intensity)).clip(0.2, 120)
            df.loc[mask, "status"] = np.where(df.loc[mask, "status"] == "completed", "delayed", df.loc[mask, "status"])

        elif attack_type == "spoof":
            inc = (0.18 + 0.45 * intensity + 0.02 * noise).clip(0.01, 0.95)
            df.loc[mask, "command_risk"] = _clip01(df.loc[mask, "command_risk"] + inc)
            extra_auth = (rng.random(n) < (0.35 + 0.45 * intensity)).astype(int)
            df.loc[mask, "auth_fail_count"] = df.loc[mask, "auth_fail_count"] + extra_auth

        elif attack_type == "tamper":
            drift = (0.12 + 0.4 * intensity + 0.03 * noise).clip(0.02, 0.9)
            df.loc[mask, "command_risk"] = _clip01(df.loc[mask, "command_risk"] + drift)
            df.loc[mask, "payload_kb"] = (df.loc[mask, "payload_kb"] * (1.05 + 0.8 * intensity)).clip(0.2, 40)
            alert_bump = (rng.random(n) < (0.1 + 0.5 * intensity)).astype(int)
            df.loc[mask, "patient_alert"] = np.maximum(df.loc[mask, "patient_alert"], alert_bump)

        elif attack_type == "replay":
            df.loc[mask, "latency_ms"] = (df.loc[mask, "latency_ms"] * (1.05 + 0.35 * intensity)).clip(5, 2000)
            df.loc[mask, "command_risk"] = _clip01(df.loc[mask, "command_risk"] + (0.08 + 0.28 * intensity))
            extra_auth = (rng.random(n) < (0.2 + 0.4 * intensity)).astype(int)
            df.loc[mask, "auth_fail_count"] = df.loc[mask, "auth_fail_count"] + extra_auth

        elif attack_type == "ransomware":
            df.loc[mask, "cpu_pct"] = (df.loc[mask, "cpu_pct"] * (1.4 + 1.1 * intensity)).clip(5, 100)
            df.loc[mask, "latency_ms"] = (df.loc[mask, "latency_ms"] * (1.35 + 0.9 * intensity)).clip(5, 2500)
            df.loc[mask, "wait_min"] = (df.loc[mask, "wait_min"] * (1.2 + 0.7 * intensity)).clip(0.2, 180)
            df.loc[mask, "status"] = np.where(df.loc[mask, "status"] == "completed", "escalated", df.loc[mask, "status"])

        # Recompute cycle and SLA after attack-induced timing changes so impact is visible.
        df.loc[mask, "cycle_min"] = df.loc[mask, "wait_min"] + df.loc[mask, "service_min"]
        df.loc[mask, "sla_breached"] = np.maximum(
            df.loc[mask, "sla_breached"],
            (df.loc[mask, "cycle_min"] > df.loc[mask, "sla_target_min"]).astype(int),
        )
        df.loc[mask, "security_flag"] = np.maximum(
            df.loc[mask, "security_flag"],
            ((df.loc[mask, "command_risk"] > 0.62) | (df.loc[mask, "auth_fail_count"] >= 2)).astype(int),
        )

        breakdown[attack_type] = breakdown.get(attack_type, 0) + n

    summary = {
        "total_attacks_injected": int(df["attack_active"].sum()),
        "attack_breakdown": {k: int(v) for k, v in breakdown.items()},
        "attack_types": sorted(list(breakdown.keys())),
    }
    return df, summary


def build_plan(
    total_events: int,
    seed: int,
    attack_rows: list[dict],
    scenario_name: str = "hospital_attack_scenario",
) -> dict:
    attacks = []
    for row in attack_rows:
        attack_type = str(row.get("attack_type", "")).strip().lower()
        if not attack_type:
            continue
        attacks.append(
            {
                "attack_type": attack_type,
                "intensity": float(np.clip(float(row.get("intensity", 0.5)), 0.05, 1.0)),
                "start_pct": float(np.clip(float(row.get("start_pct", 0.0)), 0.0, 1.0)),
                "end_pct": float(np.clip(float(row.get("end_pct", 1.0)), 0.0, 1.0)),
                "target_departments": row.get("target_departments") or DEFAULT_DEPARTMENTS,
                "target_device_types": row.get("target_device_types") or DEFAULT_DEVICE_TYPES,
            }
        )
    return {
        "scenario_name": scenario_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_events": int(total_events),
        "seed": int(seed),
        "attacks": attacks,
    }
