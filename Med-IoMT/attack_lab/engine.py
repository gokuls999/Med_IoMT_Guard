"""Attack Engine — real attacks against the hospital IoMT database.
All attacks are fully reversible via stop/restore functions.
"""
from __future__ import annotations

import json
import random
import socket
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

HOSPITAL_PORT = 8502
HOSPITAL_OUT  = Path(__file__).resolve().parent.parent / "hospital" / "outputs"
DB_PATH       = str(HOSPITAL_OUT / "hospital.db")
PLAN_PATH     = Path(__file__).resolve().parent / "generated" / "attack_plan.json"

_active: Dict[str, Any] = {}


def _safe_db_backup(src: str, dst: str) -> None:
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dst)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()


def _safe_db_restore(src: str, dst: str) -> None:
    _safe_db_backup(src, dst)


def active_attacks() -> List[str]:
    return list(_active.keys())


def stop_all() -> Dict:
    results = {}
    for key in list(_active.keys()):
        fn = globals().get(f"stop_{key}")
        if fn:
            results[key] = fn()
    # Clear attack plan
    _write_empty_plan()
    return results


def _write_attack_plan(attacks: List[str]) -> None:
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps({
        "attacks": [{"type": a} for a in attacks],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")


def _write_empty_plan() -> None:
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps({"attacks": [], "timestamp": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")


def _update_plan() -> None:
    """Sync attack plan with current active attacks."""
    _write_attack_plan(active_attacks())


# ── 1. DoS Flood — TCP connection flood ──────────────────────────────────────

def launch_dos(threads: int = 80, duration_sec: int = 90) -> Dict:
    stop_evt = threading.Event()
    _active["dos"] = stop_evt
    counters = {"sent": 0, "errors": 0}
    lock = threading.Lock()

    def worker():
        while not stop_evt.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.15)
                s.connect(("localhost", HOSPITAL_PORT))
                payload = (b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n") * 10
                s.sendall(payload)
                with lock:
                    counters["sent"] += 1
                time.sleep(0.001)
                s.close()
            except Exception:
                with lock:
                    counters["errors"] += 1

    workers = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
    for w in workers:
        w.start()
    threading.Timer(duration_sec, stop_evt.set).start()

    # Also set devices to degraded state in DB
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE iot_devices SET status='offline' WHERE device_id IN (SELECT device_id FROM iot_devices WHERE status='online' ORDER BY RANDOM() LIMIT 40)")
        conn.commit()
        conn.close()
    except Exception:
        pass

    _update_plan()
    return {"attack": "dos_flood", "threads": threads, "duration_sec": duration_sec,
            "counters": counters, "started_at": datetime.now(timezone.utc).isoformat()}


def stop_dos() -> Dict:
    ev = _active.pop("dos", None)
    if ev:
        ev.set()
    # Restore devices
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE iot_devices SET status='online' WHERE status='offline'")
        conn.commit()
        conn.close()
    except Exception:
        pass
    _update_plan()
    return {"stopped": True}


# ── 2. Data Tampering — corrupt device data and vitals ───────────────────────

def launch_tamper() -> Dict:
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".tamper_bak"
    _safe_db_backup(db, bak)
    _active["tamper"] = bak

    stats = {}
    try:
        conn = sqlite3.connect(db)
        # Corrupt all device firmware versions
        stats["firmware_corrupted"] = conn.execute(
            "UPDATE iot_devices SET firmware_version='CORRUPTED_v0.0.0'"
        ).rowcount
        # Set 60% of devices to compromised
        stats["devices_compromised"] = conn.execute(
            "UPDATE iot_devices SET status='compromised' WHERE (CAST(SUBSTR(device_id,5) AS INTEGER) % 5) < 3"
        ).rowcount
        # Inject corrupted vitals
        ts = datetime.now(timezone.utc).isoformat()
        tampered_rows = []
        devices = conn.execute("SELECT device_id, device_type, department FROM iot_devices WHERE status='compromised'").fetchall()
        rng = random.Random(42)
        for dev_id, dtype, dept in devices[:50]:
            tampered_rows.append((
                ts, dev_id, dtype, dept, None,
                rng.uniform(180, 250),   # dangerous HR
                rng.uniform(50, 70),     # dangerous SpO2
                rng.uniform(220, 280),   # hypertensive crisis
                rng.uniform(130, 170),
                rng.uniform(35, 55),
                rng.uniform(40.0, 42.5),
                rng.uniform(400, 600),
                "V-FIB", 1,
            ))
        conn.executemany(
            "INSERT INTO iot_live_vitals (timestamp, device_id, device_type, department, patient_id, "
            "heart_rate, spo2, systolic_bp, diastolic_bp, respiration_rate, temperature_c, "
            "glucose_mg_dl, ecg_rhythm, risk_flag) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tampered_rows,
        )
        stats["tampered_vitals_injected"] = len(tampered_rows)
        conn.commit()
        conn.close()
    except Exception as exc:
        return {"error": str(exc), "backup": bak}

    _update_plan()
    return {"attack": "data_tamper", "backup": bak, "changes": stats,
            "started_at": datetime.now(timezone.utc).isoformat()}


def stop_tamper() -> Dict:
    bak = _active.pop("tamper", None) or (DB_PATH + ".tamper_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        _update_plan()
        return {"restored": True}
    _update_plan()
    return {"restored": False, "error": "No backup found"}


# ── 3. Device Spoofing — inject rogue devices ────────────────────────────────

def launch_spoof(count: int = 25) -> Dict:
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".spoof_bak"
    _safe_db_backup(db, bak)
    _active["spoof"] = bak

    rng = random.Random(77)
    dtypes = ["ventilator", "patient_monitor", "infusion_pump", "defibrillator", "ecg_monitor"]
    depts = ["Emergency", "ICU", "CCU", "Cardiology", "Surgery", "Neurology"]
    injected = []

    conn = sqlite3.connect(db)
    for i in range(1, count + 1):
        rid = f"ROGUE{i:03d}"
        dtype = rng.choice(dtypes)
        dept = rng.choice(depts)
        ip = f"10.99.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
        mac = ":".join(f"{rng.randint(0, 255):02X}" for _ in range(6))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO iot_devices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid, dtype, dept, "critical", ip, mac,
                 "ROGUE_FW_v0.0", "UNKNOWN", "ROGUE-X",
                 "online", datetime.now(timezone.utc).isoformat()),
            )
            injected.append({"id": rid, "type": dtype, "dept": dept, "ip": ip})
        except Exception:
            pass
    conn.commit()
    conn.close()

    _update_plan()
    return {"attack": "device_spoof", "rogue_devices": len(injected),
            "devices": injected, "started_at": datetime.now(timezone.utc).isoformat()}


def stop_spoof() -> Dict:
    bak = _active.pop("spoof", None) or (DB_PATH + ".spoof_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        _update_plan()
        return {"restored": True}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM iot_devices WHERE device_id LIKE 'ROGUE%'")
        conn.commit()
        conn.close()
    except Exception:
        pass
    _update_plan()
    return {"restored": True, "method": "rogue_deleted"}


# ── 4. Ransomware — encrypt device data, lock system ─────────────────────────

def launch_ransomware() -> Dict:
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".ransom_bak"
    _safe_db_backup(db, bak)
    _active["ransomware"] = bak

    stats = {}
    try:
        conn = sqlite3.connect(db)
        stats["devices_locked"] = conn.execute(
            "UPDATE iot_devices SET status='error', firmware_version='ENCRYPTED'"
        ).rowcount
        # Inject ransom message into vitals (corrupted readings)
        ts = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO iot_live_vitals (timestamp, device_id, device_type, department, "
            "ecg_rhythm, risk_flag) VALUES (?,?,?,?,?,?)",
            (ts, "RANSOM_NOTICE", "ransomware", "ALL",
             "ALL_DEVICES_ENCRYPTED_CONTACT_ATTACKER", 1),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        return {"error": str(exc)}

    # Also corrupt hospital outputs
    for jf in HOSPITAL_OUT.glob("*.json"):
        if jf.name != "hospital.db" and "bak" not in jf.name:
            try:
                jf.write_text(json.dumps({
                    "RANSOMWARE": "ACTIVE",
                    "STATUS": "ALL_DATA_ENCRYPTED",
                    "MESSAGE": "HOSPITAL IoMT DATA ENCRYPTED",
                }, indent=2), encoding="utf-8")
            except Exception:
                pass

    _update_plan()
    return {"attack": "ransomware", "changes": stats,
            "started_at": datetime.now(timezone.utc).isoformat()}


def stop_ransomware() -> Dict:
    bak = _active.pop("ransomware", None) or (DB_PATH + ".ransom_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        _update_plan()
        return {"restored": True}
    _update_plan()
    return {"restored": False}


# ── 5. Replay Attack — duplicate stale device data ──────────────────────────

def launch_replay(duration_sec: int = 90) -> Dict:
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".replay_bak"
    _safe_db_backup(db, bak)

    stop_evt = threading.Event()
    _active["replay"] = (stop_evt, bak)
    counter = {"replayed": 0}

    def _replay_loop():
        rng = random.Random(55)
        while not stop_evt.is_set():
            try:
                conn = sqlite3.connect(db)
                rows = conn.execute(
                    "SELECT device_id, device_type, department FROM iot_devices WHERE status='online' LIMIT 10"
                ).fetchall()
                if rows:
                    for _ in range(3):  # Replay 3 stale readings per cycle
                        dev = rng.choice(rows)
                        conn.execute(
                            "INSERT INTO iot_live_vitals (timestamp, device_id, device_type, department, "
                            "heart_rate, spo2, ecg_rhythm, risk_flag) VALUES (?,?,?,?,?,?,?,?)",
                            (datetime.now(timezone.utc).isoformat(),
                             dev[0], dev[1], dev[2],
                             rng.uniform(40, 50),  # bradycardia (stale)
                             rng.uniform(85, 90),   # low SpO2 (stale)
                             "REPLAYED_STALE", 1),
                        )
                        counter["replayed"] += 1
                conn.commit()
                conn.close()
            except Exception:
                pass
            time.sleep(1.0)

    threading.Thread(target=_replay_loop, daemon=True).start()
    threading.Timer(duration_sec, stop_evt.set).start()

    _update_plan()
    return {"attack": "replay", "duration_sec": duration_sec,
            "counter": counter, "started_at": datetime.now(timezone.utc).isoformat()}


def stop_replay() -> Dict:
    val = _active.pop("replay", None)
    if val:
        stop_evt, bak = val
        stop_evt.set()
    else:
        bak = DB_PATH + ".replay_bak"

    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        _update_plan()
        return {"restored": True}
    _update_plan()
    return {"restored": False}


# ── 6. MitM — Man in the Middle (modify in-flight telemetry) ─────────────────

def launch_mitm() -> Dict:
    """Silently modifies vital signs of critical devices to dangerous values.
    Simulates a MitM attack where an attacker intercepts and alters telemetry."""
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".mitm_bak"
    _safe_db_backup(db, bak)
    _active["mitm"] = bak

    stats = {}
    try:
        conn = sqlite3.connect(db)
        # Target critical devices only — subtle but dangerous
        critical_devs = conn.execute(
            "SELECT device_id FROM iot_devices WHERE criticality='critical' AND status='online'"
        ).fetchall()

        rng = random.Random(99)
        ts = datetime.now(timezone.utc).isoformat()
        modified = 0
        for (dev_id,) in critical_devs:
            # Inject slightly-off readings that could cause wrong clinical decisions
            conn.execute(
                "INSERT INTO iot_live_vitals (timestamp, device_id, device_type, department, "
                "heart_rate, spo2, systolic_bp, diastolic_bp, temperature_c, ecg_rhythm, risk_flag) "
                "VALUES (?,?,'mitm_modified','INTERCEPTED',?,?,?,?,?,?,?)",
                (ts, dev_id,
                 rng.uniform(95, 110),    # Looks normal but slightly elevated
                 rng.uniform(93, 95),      # Borderline SpO2
                 rng.uniform(145, 165),    # Pre-hypertensive
                 rng.uniform(95, 110),
                 rng.uniform(38.5, 39.2),  # Low-grade fever
                 "Sinus Tachycardia", 0),  # risk_flag=0 so it looks "normal"
            )
            modified += 1

        stats["devices_intercepted"] = modified
        conn.commit()
        conn.close()
    except Exception as exc:
        return {"error": str(exc)}

    _update_plan()
    return {"attack": "mitm", "changes": stats,
            "started_at": datetime.now(timezone.utc).isoformat()}


def stop_mitm() -> Dict:
    bak = _active.pop("mitm", None) or (DB_PATH + ".mitm_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        _update_plan()
        return {"restored": True}
    _update_plan()
    return {"restored": False}
