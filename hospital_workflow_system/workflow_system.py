from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from config import SystemConfig
from hospital_db import add_appointment, add_billing_entry, init_db, seed_employees


DEPARTMENTS = ["Emergency", "ICU", "Ward", "Radiology", "Pharmacy", "Cardiology"]
DEVICE_TYPES = ["wearable_monitor", "infusion_pump", "ventilator", "bedside_sensor", "imaging_gateway"]
SUBSYSTEMS = [
    "registration",
    "triage",
    "consultation",
    "lab_test",
    "radiology_scan",
    "pharmacy_dispense",
    "bed_admission",
    "nursing_round",
    "telemonitoring",
    "discharge",
    "billing",
]
SUBSYSTEM_WEIGHTS = np.array([0.10, 0.10, 0.13, 0.11, 0.09, 0.11, 0.08, 0.10, 0.08, 0.05, 0.05], dtype=float)
SLA_TARGETS = {
    "registration": 16,
    "triage": 14,
    "consultation": 25,
    "lab_test": 32,
    "radiology_scan": 35,
    "pharmacy_dispense": 18,
    "bed_admission": 22,
    "nursing_round": 20,
    "telemonitoring": 10,
    "discharge": 30,
    "billing": 15,
}


def _build_device_registry(cfg: SystemConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed)
    departments = rng.choice(DEPARTMENTS, size=cfg.num_devices, replace=True)
    return pd.DataFrame(
        {
            "device_id": [f"dev_{i:04d}" for i in range(1, cfg.num_devices + 1)],
            "department": departments,
            "device_type": rng.choice(DEVICE_TYPES, size=cfg.num_devices, replace=True),
            "criticality": rng.choice(["high", "medium", "low"], size=cfg.num_devices, p=[0.34, 0.46, 0.20]),
        }
    )


def _subsystem_cost_inr(subsystem: str, rng: np.random.Generator) -> float:
    base = {
        "registration": (80, 220),
        "triage": (120, 260),
        "consultation": (500, 1400),
        "lab_test": (700, 2400),
        "radiology_scan": (1500, 4800),
        "pharmacy_dispense": (300, 2600),
        "bed_admission": (1200, 4800),
        "nursing_round": (220, 820),
        "telemonitoring": (150, 560),
        "discharge": (350, 1200),
        "billing": (100, 300),
    }[subsystem]
    return float(rng.uniform(base[0], base[1]))


def generate_hospital_workflow(cfg: SystemConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.random_seed)
    devices = _build_device_registry(cfg)

    patient_ids = [f"pat_{i:05d}" for i in range(1, cfg.num_patients + 1)]
    dept_weights = np.array([0.16, 0.13, 0.30, 0.11, 0.14, 0.16], dtype=float)
    bed_capacity = cfg.department_bed_capacity
    occupancy = {k: int(v * cfg.start_bed_occupancy_ratio) for k, v in bed_capacity.items()}

    start = datetime.now(timezone.utc)
    rows = []
    for i in range(cfg.total_events):
        ts = start + timedelta(seconds=i * 2)
        department = str(rng.choice(DEPARTMENTS, p=dept_weights))
        subsystem = str(rng.choice(SUBSYSTEMS, p=SUBSYSTEM_WEIGHTS / SUBSYSTEM_WEIGHTS.sum()))

        in_dept = devices[devices["department"] == department]
        pool = in_dept if (not in_dept.empty and rng.random() < 0.78) else devices
        d = pool.iloc[int(rng.integers(0, len(pool)))]

        patient_id = str(rng.choice(patient_ids))
        encounter_id = f"enc_{rng.integers(100000, 999999)}"
        priority = str(rng.choice(["critical", "high", "medium", "low"], p=[0.09, 0.21, 0.46, 0.24]))

        wait_min = float(max(0.2, rng.normal(8.5, 4.8)))
        service_min = float(max(0.2, rng.normal(12.5, 6.7)))
        if priority == "critical":
            wait_min *= 0.55
            service_min *= 1.25

        sla_target = int(SLA_TARGETS[subsystem])
        total_cycle = wait_min + service_min
        sla_breached = int(total_cycle > sla_target)

        latency_ms = float(max(3.0, rng.normal(54, 14)))
        cpu_pct = float(np.clip(rng.normal(43, 15), 5, 99))
        packet_rate = float(np.clip(rng.normal(185, 58), 20, 1300))
        payload_kb = float(np.clip(rng.normal(4.1, 1.5), 0.2, 22))
        command_risk = float(np.clip(rng.normal(0.18, 0.10), 0, 1))
        auth_fail_count = int(rng.random() < 0.025)

        patient_alert = int((priority in {"critical", "high"}) and (rng.random() < 0.07))
        cost_inr = _subsystem_cost_inr(subsystem, rng)
        if subsystem == "billing":
            cost_inr *= 0.25

        bed_change = 0
        if subsystem == "bed_admission" and occupancy[department] < bed_capacity[department]:
            bed_change = 1
            occupancy[department] += 1
        elif subsystem == "discharge" and occupancy[department] > 0:
            bed_change = -1
            occupancy[department] -= 1

        status = "completed"
        if sla_breached and rng.random() < 0.20:
            status = "delayed"
        if patient_alert and rng.random() < 0.08:
            status = "escalated"

        rows.append(
            {
                "timestamp": ts.isoformat(),
                "event_id": f"evt_{i+1:07d}",
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "department": department,
                "subsystem": subsystem,
                "device_id": d["device_id"],
                "device_type": d["device_type"],
                "device_criticality": d["criticality"],
                "priority": priority,
                "wait_min": wait_min,
                "service_min": service_min,
                "cycle_min": total_cycle,
                "sla_target_min": sla_target,
                "sla_breached": sla_breached,
                "status": status,
                "bed_change": bed_change,
                "latency_ms": latency_ms,
                "cpu_pct": cpu_pct,
                "packet_rate": packet_rate,
                "payload_kb": payload_kb,
                "command_risk": command_risk,
                "auth_fail_count": auth_fail_count,
                "patient_alert": patient_alert,
                "cost_inr": cost_inr,
                "security_flag": int((command_risk > 0.62) or (auth_fail_count >= 2)),
            }
        )

    return pd.DataFrame(rows)


def _bed_snapshot(df: pd.DataFrame, cfg: SystemConfig) -> pd.DataFrame:
    out = []
    for dept, cap in cfg.department_bed_capacity.items():
        change = int(df.loc[df["department"] == dept, "bed_change"].sum())
        current = int(min(cap, max(0, cap * cfg.start_bed_occupancy_ratio + change)))
        out.append({"department": dept, "capacity": int(cap), "occupied": int(current), "occupancy_ratio": float(current / cap if cap else 0.0)})
    return pd.DataFrame(out)


def compute_kpis(df: pd.DataFrame, cfg: SystemConfig) -> Dict:
    billing_df = df[df["subsystem"].isin(["consultation", "lab_test", "radiology_scan", "pharmacy_dispense", "bed_admission", "billing"])]
    subsystem_perf = (
        df.groupby("subsystem")
        .agg(events=("event_id", "count"), avg_wait_min=("wait_min", "mean"), avg_cycle_min=("cycle_min", "mean"), sla_breach_rate=("sla_breached", "mean"))
        .reset_index()
        .sort_values("events", ascending=False)
    )

    patient_journey = (
        df.groupby("patient_id")
        .agg(touchpoints=("event_id", "count"), avg_cycle_min=("cycle_min", "mean"), departments_visited=("department", lambda s: int(s.nunique())))
        .reset_index()
    )

    security_signals = {
        "high_command_risk_events": int((df["command_risk"] > 0.7).sum()),
        "auth_fail_spikes": int((df["auth_fail_count"] >= 2).sum()),
        "security_flagged_events": int(df["security_flag"].sum()),
        "high_risk_devices": int(df.loc[df["security_flag"] == 1, "device_id"].nunique()),
    }

    bed_df = _bed_snapshot(df, cfg)

    return {
        "executive": {
            "total_events": int(len(df)),
            "unique_patients": int(df["patient_id"].nunique()),
            "unique_devices": int(df["device_id"].nunique()),
            "patient_alerts": int(df["patient_alert"].sum()),
            "sla_breach_rate": float(df["sla_breached"].mean()),
            "avg_latency_ms": float(df["latency_ms"].mean()),
            "ops_status": "stable" if float(df["sla_breached"].mean()) < 0.18 else "stressed",
        },
        "operations": {
            "by_department_events": {k: int(v) for k, v in df["department"].value_counts().to_dict().items()},
            "subsystem_performance": subsystem_perf.to_dict(orient="records"),
            "bed_snapshot": bed_df.to_dict(orient="records"),
        },
        "finance": {
            "revenue_inr": float(billing_df["cost_inr"].sum()),
            "avg_revenue_per_billable_event": float(billing_df["cost_inr"].mean()),
            "top_revenue_subsystems": billing_df.groupby("subsystem")["cost_inr"].sum().sort_values(ascending=False).head(5).to_dict(),
        },
        "security_readiness": security_signals,
        "patient_journey_summary": {
            "avg_touchpoints": float(patient_journey["touchpoints"].mean()),
            "avg_departments_visited": float(patient_journey["departments_visited"].mean()),
            "avg_cycle_min": float(patient_journey["avg_cycle_min"].mean()),
        },
    }, patient_journey


def _seed_operational_db(db_path: str, events: pd.DataFrame) -> None:
    # Seed a small slice of system-generated appointments and billing entries.
    sample = events.sample(n=min(180, len(events)), random_state=42)
    for i, row in enumerate(sample.itertuples(index=False), start=1):
        if row.subsystem in {"consultation", "lab_test", "radiology_scan"}:
            add_appointment(
                db_path=db_path,
                appointment_id=f"apt_seed_{i:05d}",
                patient_id=row.patient_id,
                department=row.department,
                clinician_id=None,
                slot_time=row.timestamp,
                status="completed",
                source="system",
            )
        if row.subsystem in {"consultation", "lab_test", "radiology_scan", "pharmacy_dispense", "billing"}:
            add_billing_entry(
                db_path=db_path,
                bill_id=f"bill_seed_{i:05d}",
                patient_id=row.patient_id,
                category=row.subsystem,
                amount_inr=float(row.cost_inr),
                payment_status="paid" if (i % 5 != 0) else "pending",
                created_at=row.timestamp,
                source="system",
            )


def _apply_external_attacks(events: pd.DataFrame, cfg: SystemConfig) -> tuple[pd.DataFrame, Dict]:
    base = events.copy()
    base["attack_active"] = 0
    base["attack_type"] = "none"
    base["attack_intensity"] = 0.0
    if not cfg.use_external_attack_plan:
        return base, {"enabled": False, "reason": "disabled_by_config"}

    project_root = Path(__file__).resolve().parents[1]
    attack_lab_root = project_root / "iomt_attack_lab"
    plan_path = (project_root / cfg.external_attack_plan).resolve()

    if not attack_lab_root.exists():
        return base, {"enabled": False, "reason": f"attack_lab_missing:{attack_lab_root}"}
    if not plan_path.exists():
        return base, {"enabled": False, "reason": f"plan_missing:{plan_path}"}

    try:
        if str(attack_lab_root) not in sys.path:
            sys.path.insert(0, str(attack_lab_root))
        from attack_simulator import apply_attack_plan, load_attack_plan  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive import guard
        return base, {"enabled": False, "reason": f"import_error:{exc}"}

    try:
        plan = load_attack_plan(plan_path)
        attacked, summary = apply_attack_plan(base, plan)
        summary = dict(summary or {})
        summary["enabled"] = True
        summary["plan_path"] = str(plan_path)
        return attacked, summary
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        return base, {"enabled": False, "reason": f"apply_error:{exc}", "plan_path": str(plan_path)}


def run_system(output_dir: str = "outputs", cfg: SystemConfig | None = None) -> dict:
    cfg = cfg or SystemConfig()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    events = generate_hospital_workflow(cfg)
    events, attack_summary = _apply_external_attacks(events, cfg)
    kpis, patient_journey = compute_kpis(events, cfg)

    events.to_csv(out / "hospital_workflow_events.csv", index=False)
    patient_journey.to_csv(out / "patient_journey_summary.csv", index=False)

    db_path = init_db(str(out))
    seed_employees(db_path)
    _seed_operational_db(db_path, events)

    report = {"config": asdict(cfg), "kpis": kpis, "database": {"path": db_path}, "attack_injection": attack_summary}
    (out / "hospital_kpi_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
