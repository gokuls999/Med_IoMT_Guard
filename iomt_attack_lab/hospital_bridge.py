from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
HOSPITAL_ROOT = PROJECT_ROOT / "hospital_workflow_system"
HOSPITAL_OUT = HOSPITAL_ROOT / "outputs"
PLAN_PATH = ROOT / "generated" / "attack_plan.json"


def _prepare_imports() -> None:
    if str(HOSPITAL_ROOT) not in sys.path:
        sys.path.insert(0, str(HOSPITAL_ROOT))


def _delta(after: float, before: float) -> float:
    return float(after - before)


def launch_attack_in_hospital(total_events: int, seed: int) -> dict[str, Any]:
    """Generate baseline and attacked hospital outputs from Attack Lab click."""
    _prepare_imports()
    from config import SystemConfig  # type: ignore
    from workflow_system import compute_kpis, generate_hospital_workflow, run_system  # type: ignore

    HOSPITAL_OUT.mkdir(parents=True, exist_ok=True)

    cfg_base = SystemConfig(total_events=int(total_events), random_seed=int(seed), use_external_attack_plan=False)
    before_events = generate_hospital_workflow(cfg_base)
    before_kpis, _ = compute_kpis(before_events, cfg_base)
    before_events.to_csv(HOSPITAL_OUT / "hospital_workflow_events_before_attack.csv", index=False)

    cfg_attack = SystemConfig(total_events=int(total_events), random_seed=int(seed), use_external_attack_plan=True)
    attack_report = run_system(output_dir=str(HOSPITAL_OUT), cfg=cfg_attack)
    after_kpis = attack_report["kpis"]

    compare = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_path": str(PLAN_PATH),
        "total_events": int(total_events),
        "seed": int(seed),
        "attack_injection": attack_report.get("attack_injection", {}),
        "before": {
            "executive": before_kpis["executive"],
            "security_readiness": before_kpis["security_readiness"],
        },
        "after": {
            "executive": after_kpis["executive"],
            "security_readiness": after_kpis["security_readiness"],
        },
    }
    compare["delta"] = {
        "sla_breach_rate": _delta(
            compare["after"]["executive"]["sla_breach_rate"],
            compare["before"]["executive"]["sla_breach_rate"],
        ),
        "avg_latency_ms": _delta(
            compare["after"]["executive"]["avg_latency_ms"],
            compare["before"]["executive"]["avg_latency_ms"],
        ),
        "security_flagged_events": int(
            compare["after"]["security_readiness"]["security_flagged_events"]
            - compare["before"]["security_readiness"]["security_flagged_events"]
        ),
        "high_risk_devices": int(
            compare["after"]["security_readiness"]["high_risk_devices"]
            - compare["before"]["security_readiness"]["high_risk_devices"]
        ),
    }

    (HOSPITAL_OUT / "attack_baseline_report.json").write_text(json.dumps(compare["before"], indent=2), encoding="utf-8")
    (HOSPITAL_OUT / "attack_impact_report.json").write_text(json.dumps(compare, indent=2), encoding="utf-8")

    return compare


def load_attack_impact() -> dict[str, Any] | None:
    p = HOSPITAL_OUT / "attack_impact_report.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def undo_last_attack() -> bool:
    """
    Completely undo the last attack by restoring the pre-attack hospital event CSV.
    Overwrites the live events CSV with the clean baseline, clears the impact report,
    and regenerates a clean attack plan (zero attacks) so hospital_workflow reads
    unmodified data on next run.
    Returns True if restoration succeeded, False if no baseline was found.
    """
    import shutil
    before_csv  = HOSPITAL_OUT / "hospital_workflow_events_before_attack.csv"
    events_csv  = HOSPITAL_OUT / "hospital_workflow_events.csv"
    impact_json = HOSPITAL_OUT / "attack_impact_report.json"
    plan_path   = ROOT / "generated" / "attack_plan.json"

    if not before_csv.exists():
        return False

    # Restore pre-attack events
    shutil.copy2(str(before_csv), str(events_csv))

    # Remove impact report so dashboard shows clean state
    if impact_json.exists():
        impact_json.unlink()

    # Write empty attack plan so any future run_system call stays clean
    empty_plan = {
        "scenario_name": "clean_state",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_events": 5000,
        "seed": 42,
        "attacks": [],
    }
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(empty_plan, indent=2), encoding="utf-8")

    return True

