"""
Hospital Bridge — connects the Quantum IoMT Dashboard to MediCore HMS.

Reads live IoMT device vitals from hospital_workflow_system/outputs/hospital.db
and converts them into PatientSignal objects for the quantum pipeline.

Aggregation strategy: one "patient" per hospital department, vitals
averaged across all devices in that department from the live_vitals table.
"""
import os
import sqlite3
import numpy as np
from pathlib import Path

_HERE      = Path(__file__).parent
HOSPITAL_DB = _HERE.parent / "hospital_workflow_system" / "outputs" / "hospital.db"

# Physiological defaults for imputation when a department lacks a reading
_DEFAULTS = {
    "heart_rate":   75.0,
    "spo2":         98.0,
    "systolic_bp":  120.0,
    "diastolic_bp": 80.0,
    "temperature_c": 37.0,
}

N_TIMESTEPS = 200   # synthetic time-series length generated per patient


# ── Connectivity helpers ───────────────────────────────────────────────────────
def db_path() -> str:
    return str(HOSPITAL_DB)

def is_available() -> bool:
    """True when the hospital DB file exists and is a valid SQLite file."""
    if not HOSPITAL_DB.exists():
        return False
    try:
        conn = sqlite3.connect(str(HOSPITAL_DB))
        conn.execute("SELECT 1 FROM iot_live_vitals LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False


# ── Data fetch ─────────────────────────────────────────────────────────────────
def _fetch_department_rows() -> list[dict]:
    """
    Aggregate all iot_live_vitals by department.
    Returns one row per department with averaged vitals and risk label.
    """
    conn = sqlite3.connect(str(HOSPITAL_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            department,
            COUNT(DISTINCT device_id)                              AS n_devices,
            AVG(CASE WHEN heart_rate    IS NOT NULL THEN heart_rate    END) AS heart_rate,
            AVG(CASE WHEN spo2          IS NOT NULL THEN spo2          END) AS spo2,
            AVG(CASE WHEN systolic_bp   IS NOT NULL THEN systolic_bp   END) AS systolic_bp,
            AVG(CASE WHEN diastolic_bp  IS NOT NULL THEN diastolic_bp  END) AS diastolic_bp,
            AVG(CASE WHEN temperature_c IS NOT NULL THEN temperature_c END) AS temperature_c,
            SUM(risk_flag)                                         AS risk_events,
            COUNT(*)                                               AS total_readings
        FROM iot_live_vitals
        GROUP BY department
        ORDER BY department
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _fetch_device_rows(max_devices: int = 60) -> list[dict]:
    """
    One row per device (latest aggregated reading).
    Returns individual device data for the detailed view.
    """
    conn = sqlite3.connect(str(HOSPITAL_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            v.device_id,
            v.device_type,
            v.department,
            d.criticality,
            d.status,
            AVG(CASE WHEN heart_rate    IS NOT NULL THEN heart_rate    END) AS heart_rate,
            AVG(CASE WHEN spo2          IS NOT NULL THEN spo2          END) AS spo2,
            AVG(CASE WHEN systolic_bp   IS NOT NULL THEN systolic_bp   END) AS systolic_bp,
            AVG(CASE WHEN diastolic_bp  IS NOT NULL THEN diastolic_bp  END) AS diastolic_bp,
            AVG(CASE WHEN temperature_c IS NOT NULL THEN temperature_c END) AS temperature_c,
            SUM(risk_flag)  AS risk_events,
            COUNT(*)        AS total_readings
        FROM iot_live_vitals v
        LEFT JOIN iot_devices d ON v.device_id = d.device_id
        GROUP BY v.device_id
        ORDER BY v.department, v.device_id
        LIMIT ?
    """, (max_devices,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Conversion to PatientSignal ────────────────────────────────────────────────
def _row_to_patient_signal(row: dict, patient_id: int, seed: int = 0):
    """Convert one aggregated DB row into a PatientSignal with synthetic time series."""
    from data_generator import PatientSignal, _ecg_synthetic

    rng = np.random.RandomState(seed + patient_id)
    t   = np.linspace(0, 4 * np.pi, N_TIMESTEPS)

    # Impute missing vitals with defaults
    hr   = float(row.get("heart_rate")   or _DEFAULTS["heart_rate"])
    spo2 = float(row.get("spo2")         or _DEFAULTS["spo2"])
    sbp  = float(row.get("systolic_bp")  or _DEFAULTS["systolic_bp"])
    dbp  = float(row.get("diastolic_bp") or _DEFAULTS["diastolic_bp"])
    temp = float(row.get("temperature_c")or _DEFAULTS["temperature_c"])

    # Risk label — flag if >10 % of readings raised an alert
    risk_events    = int(row.get("risk_events", 0) or 0)
    total_readings = int(row.get("total_readings", 1) or 1)
    label = int((risk_events / max(total_readings, 1)) > 0.10)

    noise = 1.0 + label * 0.8

    # ECG — HR-scaled QRS complex
    hr_factor = hr / 65.0
    ecg = _ecg_synthetic(t, hr_factor, noise=0.08 * noise, rng=rng)

    # BP time series
    sbp_sig = sbp + rng.normal(0, 4.0 * noise, N_TIMESTEPS)
    dbp_sig = dbp + rng.normal(0, 3.0 * noise, N_TIMESTEPS)

    # Temperature
    temp_sig = temp + rng.normal(0, 0.12 * noise, N_TIMESTEPS)

    # EEG proxy
    alpha = np.sin(10 * t) * (1.0 - 0.4 * label)
    beta  = np.sin(25 * t) * (1.0 + 0.6 * label)
    eeg   = alpha + beta + rng.normal(0, 0.25 * noise, N_TIMESTEPS)

    # SpO2
    spo2_sig = np.clip(spo2 + rng.normal(0, 0.7 * noise, N_TIMESTEPS), 55, 100)

    return PatientSignal(
        patient_id=patient_id,
        label=label,
        ecg=ecg, sbp=sbp_sig, dbp=dbp_sig,
        temp=temp_sig, eeg=eeg, spo2=spo2_sig,
    )


# ── Public API ─────────────────────────────────────────────────────────────────
def fetch_hospital_patients(seed: int = 0) -> tuple[list, list[dict]]:
    """
    Returns (patient_signals, raw_dept_rows).
    One PatientSignal per hospital department.
    """
    rows    = _fetch_department_rows()
    signals = [_row_to_patient_signal(r, i, seed) for i, r in enumerate(rows)]
    return signals, rows


def fetch_device_summary() -> list[dict]:
    """Return per-device summary rows for the connection status panel."""
    return _fetch_device_rows()


def get_stats() -> dict:
    """Quick stats for the sidebar connection panel."""
    try:
        conn = sqlite3.connect(str(HOSPITAL_DB))
        n_devices = conn.execute("SELECT COUNT(DISTINCT device_id) FROM iot_live_vitals").fetchone()[0]
        n_records = conn.execute("SELECT COUNT(*) FROM iot_live_vitals").fetchone()[0]
        n_alerts  = conn.execute("SELECT SUM(risk_flag) FROM iot_live_vitals").fetchone()[0]
        depts     = conn.execute("SELECT COUNT(DISTINCT department) FROM iot_live_vitals").fetchone()[0]
        conn.close()
        return {
            "n_devices": n_devices,
            "n_records": n_records,
            "n_alerts":  int(n_alerts or 0),
            "n_depts":   depts,
        }
    except Exception:
        return {}
