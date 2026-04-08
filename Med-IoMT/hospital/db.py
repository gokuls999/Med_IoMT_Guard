"""IoMT Device Database — SQLite-backed device registry and live telemetry."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

DB_NAME = "hospital.db"

# ── Device type definitions (realistic IoMT inventory) ────────────────────────
DEVICE_TYPES = {
    # (type_name, criticality, description)
    "patient_monitor":     ("critical", "Multi-parameter bedside monitor"),
    "ventilator":          ("critical", "Mechanical ventilation system"),
    "infusion_pump":       ("critical", "IV infusion delivery system"),
    "defibrillator":       ("critical", "Cardiac defibrillation unit"),
    "ecg_monitor":         ("high",     "12-lead ECG recording system"),
    "pulse_oximeter":      ("high",     "SpO2 and heart rate sensor"),
    "blood_pressure_monitor": ("high",  "Non-invasive BP monitor"),
    "cgm_sensor":          ("high",     "Continuous glucose monitor"),
    "fetal_monitor":       ("high",     "Fetal heart rate monitor"),
    "smart_iv_pump":       ("high",     "Networked IV infusion pump"),
    "capnograph":          ("high",     "End-tidal CO2 monitor"),
    "dialysis_machine":    ("high",     "Hemodialysis unit"),
    "bipap_machine":       ("high",     "Bilevel positive airway pressure"),
    "wearable_monitor":    ("medium",   "Wearable vital signs tracker"),
    "bedside_sensor":      ("medium",   "Environmental bedside sensor"),
    "temperature_probe":   ("medium",   "Continuous temperature sensor"),
    "syringe_driver":      ("high",     "Precision medication syringe pump"),
    "imaging_gateway":     ("low",      "DICOM imaging network gateway"),
    "nurse_call_unit":     ("medium",   "Bedside nurse call terminal"),
    "medication_dispenser":("medium",   "Automated medication dispensing unit"),
}

DEPARTMENTS = [
    "Emergency", "ICU", "CCU", "NICU", "Ward-A", "Ward-B",
    "Radiology", "Cardiology", "Neurology", "Oncology",
    "Maternity", "Nephrology", "Pulmonology", "Surgery",
]

# ── Schema ────────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS iot_devices (
    device_id        TEXT PRIMARY KEY,
    device_type      TEXT NOT NULL,
    department       TEXT NOT NULL,
    criticality      TEXT NOT NULL DEFAULT 'medium',
    ip_address       TEXT,
    mac_address      TEXT,
    firmware_version TEXT DEFAULT 'v3.1.2',
    manufacturer     TEXT,
    model_number     TEXT,
    status           TEXT NOT NULL DEFAULT 'online',
    last_seen        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS iot_live_vitals (
    record_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT NOT NULL,
    device_id         TEXT NOT NULL,
    device_type       TEXT NOT NULL,
    department        TEXT NOT NULL,
    patient_id        TEXT,
    heart_rate        REAL,
    spo2              REAL,
    systolic_bp       REAL,
    diastolic_bp      REAL,
    respiration_rate  REAL,
    temperature_c     REAL,
    glucose_mg_dl     REAL,
    ecg_rhythm        TEXT,
    risk_flag         INTEGER NOT NULL DEFAULT 0
);
"""


def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db(base_dir: str) -> str:
    db_path = str(Path(base_dir) / DB_NAME)
    with _conn(db_path) as conn:
        conn.executescript(_DDL)
        conn.commit()
    return db_path


# ── Manufacturers for realism ─────────────────────────────────────────────────
_MANUFACTURERS = {
    "patient_monitor":     [("Philips", "IntelliVue MX800"), ("GE Healthcare", "CARESCAPE B650"), ("Mindray", "BeneVision N22")],
    "ventilator":          [("Drager", "Evita V500"), ("Medtronic", "PB980"), ("Hamilton Medical", "Hamilton-C6")],
    "infusion_pump":       [("Baxter", "Sigma Spectrum"), ("B. Braun", "Infusomat Space"), ("ICU Medical", "Plum 360")],
    "defibrillator":       [("Zoll", "R Series Plus"), ("Philips", "HeartStart MRx"), ("Stryker", "LIFEPAK 15")],
    "ecg_monitor":         [("GE Healthcare", "MAC 5500 HD"), ("Philips", "TC70"), ("Nihon Kohden", "ECG-2550")],
    "pulse_oximeter":      [("Masimo", "Radical-7"), ("Nonin", "PalmSAT 2500"), ("Nellcor", "PM100N")],
    "blood_pressure_monitor": [("Omron", "HEM-907XL"), ("Welch Allyn", "ProBP 3400"), ("Mindray", "VS-900")],
    "cgm_sensor":          [("Dexcom", "G7"), ("Abbott", "FreeStyle Libre 3"), ("Medtronic", "Guardian 4")],
    "fetal_monitor":       [("Philips", "Avalon FM50"), ("GE Healthcare", "Corometrics 250cx")],
    "smart_iv_pump":       [("BD Alaris", "8015"), ("Ivenix", "Infusion System"), ("Fresenius Kabi", "Agilia VP")],
    "capnograph":          [("Medtronic", "Capnostream 35"), ("Masimo", "ISA OR+")],
    "dialysis_machine":    [("Fresenius", "5008S CorDiax"), ("Baxter", "AK 98"), ("Nipro", "Surdial 55Plus")],
    "bipap_machine":       [("Philips", "Trilogy Evo"), ("ResMed", "AirCurve 10 VAuto")],
    "wearable_monitor":    [("Biobeat", "BB-613WP"), ("VitalConnect", "VitalPatch"), ("Philips", "BX100")],
    "bedside_sensor":      [("Earlysense", "InSight+"), ("Leaf Healthcare", "Leaf Patient Sensor")],
    "temperature_probe":   [("3M", "Bair Hugger"), ("DeRoyal", "ContiTemp")],
    "syringe_driver":      [("BD", "Alaris CC"), ("Smiths Medical", "CADD-Solis")],
    "imaging_gateway":     [("Horos", "DICOM Gateway"), ("Merge Healthcare", "iConnect Access")],
    "nurse_call_unit":     [("Ascom", "Myco 3"), ("Hill-Rom", "Nurse Call")],
    "medication_dispenser":[("Omnicell", "XT Automated"), ("BD", "Pyxis MedStation ES")],
}


def seed_devices(db_path: str, total_devices: int = 200) -> None:
    """Seed IoMT device registry. Idempotent."""
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM iot_devices").fetchone()[0]
    if n >= total_devices:
        return

    rng = np.random.default_rng(42)
    type_names = list(DEVICE_TYPES.keys())
    # Weight distribution: more monitors/pumps, fewer gateways
    weights = np.array([
        12, 10, 14, 4, 8, 10, 8, 6, 4, 8,
        5, 4, 4, 10, 8, 6, 5, 3, 6, 5,
    ], dtype=float)
    weights = weights / weights.sum()

    rows = []
    for i in range(1, total_devices + 1):
        dtype = str(rng.choice(type_names, p=weights))
        crit = DEVICE_TYPES[dtype][0]
        dept = str(rng.choice(DEPARTMENTS))
        subnet = int(rng.integers(1, 8))
        host = int(rng.integers(10, 254))
        mac = ":".join(f"{int(rng.integers(0, 256)):02X}" for _ in range(6))
        mfg_choices = _MANUFACTURERS.get(dtype, [("Generic", "Model-X")])
        mfg, model = mfg_choices[int(rng.integers(0, len(mfg_choices)))]
        fw_major = int(rng.integers(2, 6))
        fw_minor = int(rng.integers(0, 10))
        fw_patch = int(rng.integers(0, 10))

        # Most devices online, some in maintenance/offline
        r = float(rng.random())
        if r < 0.88:
            status = "online"
        elif r < 0.95:
            status = "maintenance"
        else:
            status = "offline"

        last_seen = datetime.now(timezone.utc)
        if status != "online":
            last_seen -= timedelta(hours=float(rng.integers(1, 48)))

        rows.append((
            f"dev_{i:04d}", dtype, dept, crit,
            f"10.{subnet}.{int(rng.integers(1, 20))}.{host}",
            mac, f"v{fw_major}.{fw_minor}.{fw_patch}",
            mfg, model, status, last_seen.isoformat(),
        ))

    with _conn(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO iot_devices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def get_devices(db_path: str, department: str = "all", status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM iot_devices"
    clauses, params = [], []
    if department != "all":
        clauses.append("department=?"); params.append(department)
    if status != "all":
        clauses.append("status=?"); params.append(status)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY department, device_type, device_id"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_device_counts(db_path: str) -> Dict:
    """Quick device summary stats."""
    with _conn(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM iot_devices").fetchone()[0]
        online = conn.execute("SELECT COUNT(*) FROM iot_devices WHERE status='online'").fetchone()[0]
        offline = conn.execute("SELECT COUNT(*) FROM iot_devices WHERE status='offline'").fetchone()[0]
        maint = conn.execute("SELECT COUNT(*) FROM iot_devices WHERE status='maintenance'").fetchone()[0]
        compromised = conn.execute("SELECT COUNT(*) FROM iot_devices WHERE status IN ('compromised','error','corrupted')").fetchone()[0]
        critical = conn.execute("SELECT COUNT(*) FROM iot_devices WHERE criticality='critical'").fetchone()[0]
    return {
        "total": total, "online": online, "offline": offline,
        "maintenance": maint, "compromised": compromised, "critical": critical,
    }


def get_dept_device_summary(db_path: str) -> pd.DataFrame:
    q = """SELECT department,
           COUNT(*) as total,
           SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) as online,
           SUM(CASE WHEN status='offline' THEN 1 ELSE 0 END) as offline,
           SUM(CASE WHEN status IN ('compromised','error','corrupted') THEN 1 ELSE 0 END) as compromised
           FROM iot_devices GROUP BY department ORDER BY department"""
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


# ── Live telemetry generation ─────────────────────────────────────────────────
_TARGETS = {
    "heart_rate": 75.0, "spo2": 98.0, "systolic_bp": 118.0,
    "diastolic_bp": 78.0, "respiration_rate": 15.0,
    "temperature_c": 36.8, "glucose_mg_dl": 100.0,
}
_SIGMA = {
    "heart_rate": 2.5, "spo2": 0.4, "systolic_bp": 2.8,
    "diastolic_bp": 1.8, "respiration_rate": 0.6,
    "temperature_c": 0.08, "glucose_mg_dl": 3.5,
}
_LIMITS = {
    "heart_rate": (45, 160), "spo2": (88, 100), "systolic_bp": (90, 180),
    "diastolic_bp": (55, 120), "respiration_rate": (8, 35),
    "temperature_c": (35.5, 40.5), "glucose_mg_dl": (55, 350),
}

_NO_VITALS_TYPES = {"imaging_gateway", "nurse_call_unit", "medication_dispenser"}
_NO_RHYTHM_TYPES = {
    "infusion_pump", "smart_iv_pump", "pulse_oximeter", "blood_pressure_monitor",
    "temperature_probe", "capnograph", "dialysis_machine", "bipap_machine",
    "cgm_sensor", "syringe_driver",
}


def generate_vitals(
    db_path: str,
    prev_states: Optional[dict] = None,
) -> tuple:
    """Generate one telemetry row per device. Returns (DataFrame, new_states)."""
    rng = np.random.default_rng(int(datetime.now(timezone.utc).timestamp()) % 100000)
    devices = get_devices(db_path)
    if devices.empty:
        return pd.DataFrame(), {}

    def _drift(prev_val: float, key: str) -> float:
        target, sigma = _TARGETS[key], _SIGMA[key]
        lo, hi = _LIMITS[key]
        new = prev_val + float(rng.normal(0, sigma)) + 0.01 * (target - prev_val)
        return float(np.clip(new, lo, hi))

    def _baseline(key: str) -> float:
        lo, hi = _LIMITS[key]
        return float(np.clip(rng.normal(_TARGETS[key], _SIGMA[key] * 5), lo, hi))

    rows = []
    new_states: dict = {}
    ts_now = datetime.now(timezone.utc).isoformat()

    for _, d in devices.iterrows():
        dtype = str(d["device_type"])
        dev_id = str(d["device_id"])
        dev_status = str(d["status"])
        prev = (prev_states or {}).get(dev_id, {})

        # Offline / compromised devices: produce no telemetry or corrupted data
        if dev_status in ("offline", "compromised", "error", "corrupted"):
            if dev_status == "offline":
                continue
            # Corrupted: send wildly abnormal values
            rows.append((
                ts_now, dev_id, dtype, str(d["department"]), None,
                float(rng.uniform(150, 220)),  # tachycardia
                float(rng.uniform(60, 80)),     # low SpO2
                float(rng.uniform(200, 260)),   # hypertensive crisis
                float(rng.uniform(120, 160)),
                float(rng.uniform(30, 50)),
                float(rng.uniform(39.5, 41.5)),
                float(rng.uniform(300, 500)),
                "V-FIB" if rng.random() < 0.3 else "V-TACH",
                1,
            ))
            continue

        if dtype in _NO_VITALS_TYPES:
            continue

        if prev:
            hr = _drift(prev.get("heart_rate", _TARGETS["heart_rate"]), "heart_rate")
            spo2 = _drift(prev.get("spo2", _TARGETS["spo2"]), "spo2")
            sys_bp = _drift(prev.get("systolic_bp", _TARGETS["systolic_bp"]), "systolic_bp")
            dia_bp = _drift(prev.get("diastolic_bp", _TARGETS["diastolic_bp"]), "diastolic_bp")
            rr = _drift(prev.get("respiration_rate", _TARGETS["respiration_rate"]), "respiration_rate")
            temp = _drift(prev.get("temperature_c", _TARGETS["temperature_c"]), "temperature_c")
            glu = _drift(prev.get("glucose_mg_dl", _TARGETS["glucose_mg_dl"]), "glucose_mg_dl")
        else:
            hr, spo2 = _baseline("heart_rate"), _baseline("spo2")
            sys_bp, dia_bp = _baseline("systolic_bp"), _baseline("diastolic_bp")
            rr, temp, glu = _baseline("respiration_rate"), _baseline("temperature_c"), _baseline("glucose_mg_dl")

        rhythm = "Normal Sinus" if dtype not in _NO_RHYTHM_TYPES else "N/A"
        if dtype == "ecg_monitor" and rng.random() < 0.03:
            rhythm = str(rng.choice(["A-FIB", "SVT", "Bradycardia"]))
        if dtype == "defibrillator" and rng.random() < 0.05:
            rhythm = "V-TACH"
            hr = float(rng.uniform(160, 210))

        # Device-specific: null irrelevant fields
        if dtype == "cgm_sensor":
            glu = float(np.clip(glu * 1.4 if not prev else glu, 70, 350))
            hr = spo2 = sys_bp = dia_bp = rr = temp = np.nan
        elif dtype in ("pulse_oximeter",):
            sys_bp = dia_bp = rr = temp = glu = np.nan
        elif dtype in ("blood_pressure_monitor",):
            hr = spo2 = rr = temp = glu = np.nan
        elif dtype == "temperature_probe":
            hr = spo2 = sys_bp = dia_bp = rr = glu = np.nan
        elif dtype == "capnograph":
            hr = sys_bp = dia_bp = temp = glu = np.nan

        risk = 0
        if not np.isnan(hr) and (hr > 130 or hr < 50): risk = 1
        if not np.isnan(spo2) and spo2 < 92: risk = 1
        if not np.isnan(sys_bp) and sys_bp > 170: risk = 1
        if not np.isnan(temp) and temp > 39.5: risk = 1

        pid = prev.get("patient_id") or (f"pat_{int(rng.integers(1, 200)):04d}" if rng.random() < 0.8 else None)

        new_states[dev_id] = {
            "heart_rate": hr, "spo2": spo2, "systolic_bp": sys_bp,
            "diastolic_bp": dia_bp, "respiration_rate": rr,
            "temperature_c": temp, "glucose_mg_dl": glu, "patient_id": pid,
        }

        rows.append((
            ts_now, dev_id, dtype, str(d["department"]), pid,
            hr, spo2, sys_bp, dia_bp, rr, temp, glu, rhythm, risk,
        ))

    cols = [
        "timestamp", "device_id", "device_type", "department", "patient_id",
        "heart_rate", "spo2", "systolic_bp", "diastolic_bp",
        "respiration_rate", "temperature_c", "glucose_mg_dl", "ecg_rhythm", "risk_flag",
    ]
    df = pd.DataFrame(rows, columns=cols)

    # Write to DB
    if not df.empty:
        with _conn(db_path) as conn:
            df.to_sql("iot_live_vitals", conn, if_exists="append", index=False)
            # Trim old vitals to prevent DB bloat
            conn.execute("DELETE FROM iot_live_vitals WHERE record_id NOT IN (SELECT record_id FROM iot_live_vitals ORDER BY record_id DESC LIMIT 10000)")

    return df, new_states


def get_live_vitals(db_path: str, limit: int = 500, device_id: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM iot_live_vitals"
    params = []
    if device_id != "all":
        q += " WHERE device_id=?"
        params.append(device_id)
    q += " ORDER BY record_id DESC LIMIT ?"
    params.append(limit)
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)
