"""
Hospital Management System – Data Layer
SQLite-backed database module for all hospital modules.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

DB_NAME = "hospital.db"

# ── Reference data for seeding ───────────────────────────────────────────────
_MALE = [
    "Arjun","Rahul","Suresh","Ramesh","Vikram","Anil","Sanjay","Manish",
    "Deepak","Rajesh","Mohan","Vinod","Ashok","Ganesh","Naresh","Mahesh",
    "Ravi","Vijay","Ajay","Arun","Srinivas","Venkat","Prakash","Santosh",
    "Kartik","Rohit","Dev","Amit","Naveen","Harish",
]
_FEMALE = [
    "Priya","Kavitha","Lakshmi","Sunita","Meena","Anitha","Rekha","Seetha",
    "Radha","Usha","Geetha","Shobha","Padma","Malathi","Asha","Nirmala",
    "Savitha","Saranya","Divya","Pooja","Anjali","Sneha","Renu","Meghna",
    "Pallavi","Sudha","Shanthi","Revathi","Yamini","Deepa",
]
_LAST = [
    "Kumar","Sharma","Patel","Singh","Nair","Reddy","Iyer","Pillai",
    "Menon","Gupta","Verma","Joshi","Shah","Rao","Krishnan","Bhat",
    "Naidu","Mishra","Thakur","Choudhury",
]
_BLOOD   = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
_CITIES  = ["Mumbai","Delhi","Chennai","Bangalore","Hyderabad","Pune","Ahmedabad","Kochi"]
_DIAGS   = [
    "Hypertension","Type 2 Diabetes","Community-Acquired Pneumonia",
    "Acute Myocardial Infarction","Acute Appendicitis","Femur Fracture",
    "Gastroenteritis","Urinary Tract Infection","Viral Fever","Dengue Fever",
    "COPD Exacerbation","Acute Asthma","Head Injury","Sepsis",
    "Acute Kidney Injury","Ischemic Stroke","Congestive Heart Failure",
    "Chest Pain – Evaluation","Iron Deficiency Anaemia","Hypothyroidism",
]
_COMPLAINTS = [
    "Chest pain","High fever","Difficulty breathing","Severe headache",
    "Abdominal pain","Vomiting","Leg injury","Back pain",
    "Unconscious / altered sensorium","Palpitations","Dizziness","Rash",
]
_TESTS = [
    ("Complete Blood Count (CBC)","Hematology","10–14 g/dL","g/dL"),
    ("Blood Glucose Fasting","Biochemistry","70–100 mg/dL","mg/dL"),
    ("Lipid Profile","Biochemistry","<200 mg/dL total cholesterol","mg/dL"),
    ("Liver Function Test (LFT)","Biochemistry","SGPT <40 U/L","U/L"),
    ("Kidney Function Test (KFT)","Biochemistry","Creatinine 0.6–1.2 mg/dL","mg/dL"),
    ("Thyroid Profile (T3/T4/TSH)","Endocrinology","TSH 0.4–4.0 mIU/L","mIU/L"),
    ("Urine Routine & Microscopy","Microbiology","Clear / No cells",""),
    ("Blood Culture & Sensitivity","Microbiology","No growth",""),
    ("HbA1c","Biochemistry","4.0–5.6%","%"),
    ("Serum Electrolytes","Biochemistry","Na 136–145 mEq/L","mEq/L"),
    ("Coagulation Profile (PT/APTT)","Hematology","PT 11–13.5 sec","sec"),
    ("CRP (C-Reactive Protein)","Biochemistry","<10 mg/L","mg/L"),
    ("Troponin I","Cardiology","<0.04 ng/mL","ng/mL"),
    ("ABG (Arterial Blood Gas)","Respiratory","pH 7.35–7.45",""),
    ("Dengue NS1 Antigen","Serology","Negative",""),
]
_SCANS = [
    ("Chest X-Ray PA View","X-Ray","Chest"),
    ("CT Head Non-Contrast","CT","Head"),
    ("Abdominal Ultrasound","Ultrasound","Abdomen"),
    ("MRI Brain with Contrast","MRI","Brain"),
    ("CT Chest High Resolution","CT","Chest"),
    ("Echocardiogram 2D","Ultrasound","Heart"),
    ("CT Abdomen & Pelvis","CT","Abdomen"),
    ("Bone Density Scan (DEXA)","DEXA","Spine/Hip"),
]
_DRUGS = [
    ("Paracetamol 500mg Tab","500mg","TDS",5),
    ("Amoxicillin 500mg Cap","500mg","TDS",7),
    ("Metformin 500mg Tab","500mg","BD",30),
    ("Atorvastatin 10mg Tab","10mg","OD",30),
    ("Amlodipine 5mg Tab","5mg","OD",30),
    ("Pantoprazole 40mg Tab","40mg","OD",14),
    ("Ceftriaxone 1g IV","1g","BD",7),
    ("Furosemide 40mg Tab","40mg","OD",14),
    ("Insulin Regular 10U SC","10U","TDS",30),
    ("Aspirin 75mg Tab","75mg","OD",30),
    ("Ondansetron 4mg Tab","4mg","TDS",5),
    ("Metronidazole 400mg Tab","400mg","TDS",7),
    ("Omeprazole 20mg Cap","20mg","BD",14),
    ("IV Fluids NS 500ml","500ml","Q6H",3),
]
_ROLES  = ["Doctor","Nurse","Technician","Admin","Pharmacist","Radiologist","Paramedic"]
_SHIFTS = ["Morning","Evening","Night"]
_DEPTS  = ["Emergency","ICU","Ward","Radiology","Pharmacy","Cardiology"]

BED_CONFIG = {"Emergency": 10, "ICU": 8, "Ward": 14, "Cardiology": 8}

# ── Connection helper ────────────────────────────────────────────────────────

def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.execute("PRAGMA journal_mode=WAL")
    return c

# ── Schema ───────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id   TEXT PRIMARY KEY,
    mrn          TEXT UNIQUE NOT NULL,
    full_name    TEXT NOT NULL,
    dob          TEXT,
    age          INTEGER NOT NULL,
    gender       TEXT NOT NULL,
    blood_group  TEXT,
    contact      TEXT,
    address      TEXT,
    triage_level TEXT NOT NULL DEFAULT 'medium',
    status       TEXT NOT NULL DEFAULT 'active',
    admission_type TEXT DEFAULT 'outpatient',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admissions (
    admission_id      TEXT PRIMARY KEY,
    patient_id        TEXT NOT NULL,
    department        TEXT NOT NULL,
    bed_id            TEXT,
    admit_date        TEXT NOT NULL,
    discharge_date    TEXT,
    diagnosis         TEXT,
    attending_doctor  TEXT,
    status            TEXT NOT NULL DEFAULT 'admitted',
    notes             TEXT
);

CREATE TABLE IF NOT EXISTS beds (
    bed_id       TEXT PRIMARY KEY,
    department   TEXT NOT NULL,
    ward         TEXT NOT NULL,
    bed_number   TEXT NOT NULL,
    bed_type     TEXT NOT NULL DEFAULT 'general',
    status       TEXT NOT NULL DEFAULT 'available',
    patient_id   TEXT,
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triage_queue (
    queue_id        TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL,
    patient_name    TEXT NOT NULL,
    age             INTEGER,
    gender          TEXT,
    arrival_time    TEXT NOT NULL,
    triage_level    TEXT NOT NULL,
    chief_complaint TEXT NOT NULL,
    assigned_to     TEXT,
    status          TEXT NOT NULL DEFAULT 'waiting'
);

CREATE TABLE IF NOT EXISTS consultations (
    consult_id     TEXT PRIMARY KEY,
    patient_id     TEXT NOT NULL,
    appointment_id TEXT,
    doctor_id      TEXT NOT NULL,
    doctor_name    TEXT NOT NULL,
    department     TEXT NOT NULL,
    diagnosis      TEXT,
    notes          TEXT,
    follow_up_date TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lab_orders (
    order_id        TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL,
    patient_name    TEXT NOT NULL,
    test_name       TEXT NOT NULL,
    test_category   TEXT NOT NULL,
    ordered_by      TEXT NOT NULL,
    ordered_at      TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'routine',
    status          TEXT NOT NULL DEFAULT 'ordered',
    result_value    TEXT,
    result_unit     TEXT,
    reference_range TEXT,
    result_flag     TEXT,
    completed_at    TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS radiology_orders (
    order_id      TEXT PRIMARY KEY,
    patient_id    TEXT NOT NULL,
    patient_name  TEXT NOT NULL,
    scan_type     TEXT NOT NULL,
    modality      TEXT NOT NULL,
    body_part     TEXT NOT NULL,
    ordered_by    TEXT NOT NULL,
    ordered_at    TEXT NOT NULL,
    priority      TEXT NOT NULL DEFAULT 'routine',
    status        TEXT NOT NULL DEFAULT 'ordered',
    radiologist   TEXT,
    findings      TEXT,
    impression    TEXT,
    completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS pharmacy_orders (
    order_id      TEXT PRIMARY KEY,
    patient_id    TEXT NOT NULL,
    patient_name  TEXT NOT NULL,
    drug_name     TEXT NOT NULL,
    dosage        TEXT NOT NULL,
    frequency     TEXT NOT NULL,
    duration_days INTEGER NOT NULL DEFAULT 5,
    prescribed_by TEXT NOT NULL,
    prescribed_at TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'prescribed',
    dispensed_at  TEXT,
    dispensed_by  TEXT,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS iot_devices (
    device_id        TEXT PRIMARY KEY,
    device_type      TEXT NOT NULL,
    department       TEXT NOT NULL,
    criticality      TEXT NOT NULL DEFAULT 'medium',
    ip_address       TEXT,
    firmware_version TEXT DEFAULT 'v3.1.2',
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

CREATE TABLE IF NOT EXISTS employees (
    employee_id  TEXT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    role         TEXT NOT NULL,
    department   TEXT NOT NULL,
    shift        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    email        TEXT,
    phone        TEXT
);

CREATE TABLE IF NOT EXISTS patients_manual (
    patient_id   TEXT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    age          INTEGER NOT NULL,
    gender       TEXT NOT NULL,
    contact      TEXT,
    triage_level TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id TEXT PRIMARY KEY,
    patient_id     TEXT NOT NULL,
    department     TEXT NOT NULL,
    clinician_id   TEXT,
    slot_time      TEXT NOT NULL,
    status         TEXT NOT NULL,
    source         TEXT NOT NULL DEFAULT 'manual',
    appointment_type TEXT DEFAULT 'consultation',
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS billing_entries (
    bill_id        TEXT PRIMARY KEY,
    patient_id     TEXT NOT NULL,
    category       TEXT NOT NULL,
    amount_inr     REAL NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'pending',
    created_at     TEXT NOT NULL,
    source         TEXT NOT NULL DEFAULT 'system',
    description    TEXT
);
"""


def init_db(base_dir: str) -> str:
    db_path = str(Path(base_dir) / DB_NAME)
    with _conn(db_path) as conn:
        conn.executescript(_DDL)
        conn.commit()
    return db_path


# ── Seed helpers ─────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rng(seed: int = 7) -> np.random.Generator:
    return np.random.default_rng(seed)


def _name(rng: np.random.Generator, gender: str) -> str:
    pool = _MALE if gender == "Male" else _FEMALE
    return f"{rng.choice(pool)} {rng.choice(_LAST)}"


def _phone(rng: np.random.Generator) -> str:
    return f"9{int(rng.integers(100000000, 999999999))}"


def _mrn(idx: int) -> str:
    return f"MRN{datetime.now().strftime('%y')}{idx:04d}"


def _ts(days_ago: float = 0, hours_ago: float = 0) -> str:
    t = _now() - timedelta(days=days_ago, hours=hours_ago)
    return t.isoformat()


def _today_slot(hour: int, minute: int = 0) -> str:
    t = _now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return t.isoformat()


# ── Master seed function ──────────────────────────────────────────────────────

def seed_all(db_path: str) -> None:
    """Seed all tables with realistic hospital data. Idempotent."""
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    if n == 0:
        rng = _rng(42)
        _seed_patients(db_path, rng)
        _seed_beds(db_path, rng)
        _seed_admissions(db_path, rng)
        _seed_triage(db_path, rng)
        _seed_appointments(db_path, rng)
        _seed_lab_orders(db_path, rng)
        _seed_radiology_orders(db_path, rng)
        _seed_pharmacy_orders(db_path, rng)
        _seed_iot_devices(db_path)
        seed_employees(db_path)
    # Always ensure new device types exist (safe to run on existing DBs)
    _seed_extra_iot_devices(db_path)


def _seed_patients(db_path: str, rng: np.random.Generator) -> None:
    statuses = (
        ["admitted"] * 20 + ["emergency"] * 5 + ["observation"] * 5
        + ["active"] * 15 + ["discharged"] * 15
    )
    admission_types = {
        "admitted": "inpatient", "emergency": "emergency",
        "observation": "observation", "active": "outpatient",
        "discharged": "outpatient",
    }
    rows = []
    for i, status in enumerate(statuses, start=1):
        gender = "Male" if i % 2 == 0 else "Female"
        age = int(rng.integers(8, 82))
        yr = datetime.now().year - age
        triage = rng.choice(["critical","high","medium","low"], p=[0.10,0.20,0.47,0.23])
        days_ago = float(rng.integers(0, 25))
        rows.append((
            f"pat_{i:04d}", _mrn(i), _name(rng, gender),
            f"{yr}-{int(rng.integers(1,13)):02d}-{int(rng.integers(1,28)):02d}",
            age, gender, str(rng.choice(_BLOOD)),
            _phone(rng), str(rng.choice(_CITIES)),
            str(triage), status, admission_types[status],
            _ts(days_ago),
        ))
    with _conn(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO patients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )


def _seed_beds(db_path: str, rng: np.random.Generator) -> None:
    bed_types = {"Emergency": "resus", "ICU": "icu", "Ward": "general", "Cardiology": "cardiac"}
    rows = []
    bid = 1
    for dept, count in BED_CONFIG.items():
        for num in range(1, count + 1):
            status = "available"
            rows.append((
                f"bed_{bid:04d}", dept, f"{dept} Wing",
                f"{dept[0]}{num:02d}", bed_types[dept],
                status, None, _ts(0),
            ))
            bid += 1
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO beds VALUES (?,?,?,?,?,?,?,?)", rows)


def _seed_admissions(db_path: str, rng: np.random.Generator) -> None:
    admitted_patients = [f"pat_{i:04d}" for i in range(1, 26)]
    depts_pool = ["Emergency","ICU","Ward","Cardiology"]
    doctors = [f"Dr. {_name(rng, 'Male')}" for _ in range(8)]
    rows = []

    # Assign beds
    with _conn(db_path) as conn:
        beds_df = pd.read_sql_query(
            "SELECT bed_id, department FROM beds WHERE status='available'", conn
        )

    bed_iter = iter(beds_df.itertuples())
    bed_assignments: Dict[str, str] = {}

    for i, pid in enumerate(admitted_patients[:20], start=1):
        dept = str(rng.choice(depts_pool))
        admit_days = float(rng.integers(1, 8))
        doctor = str(rng.choice(doctors))
        diag = str(rng.choice(_DIAGS))

        # Try to assign a bed in the same dept
        available_beds = beds_df[beds_df["department"] == dept]["bed_id"].tolist()
        bed_id = str(rng.choice(available_beds)) if available_beds else None
        if bed_id and bed_id not in bed_assignments:
            bed_assignments[bed_id] = pid

        rows.append((
            f"adm_{i:04d}", pid, dept, bed_id,
            _ts(admit_days), None, diag, doctor, "admitted", "",
        ))

    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO admissions VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        # Mark beds as occupied
        for bed_id, pid in bed_assignments.items():
            conn.execute(
                "UPDATE beds SET status='occupied', patient_id=?, last_updated=? WHERE bed_id=?",
                (pid, _ts(0), bed_id),
            )


def _seed_triage(db_path: str, rng: np.random.Generator) -> None:
    names_genders = [(_name(rng, "Male"), "Male"), (_name(rng, "Female"), "Female")]
    all_names = [(f"TriageWalk_{i}", "Male" if i%2==0 else "Female") for i in range(1,9)]
    rows = []
    statuses = ["waiting","waiting","waiting","in_progress","in_progress","admitted","discharged","discharged"]
    triages  = ["critical","high","high","medium","medium","medium","low","low"]
    for i in range(8):
        pid = f"triage_temp_{i+1:03d}"
        nm, gnd = all_names[i]
        rows.append((
            f"tq_{i+1:04d}", pid, nm, int(rng.integers(18, 75)), gnd,
            _ts(hours_ago=float(rng.integers(0, 6))),
            triages[i], str(rng.choice(_COMPLAINTS)),
            f"Dr. {rng.choice(_MALE)}" if statuses[i] != "waiting" else None,
            statuses[i],
        ))
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO triage_queue VALUES (?,?,?,?,?,?,?,?,?,?)", rows)


def _seed_appointments(db_path: str, rng: np.random.Generator) -> None:
    rows = []
    patients = [f"pat_{i:04d}" for i in range(1, 61)]
    depts = _DEPTS[:4] + ["Cardiology"]
    # 15 today, 20 upcoming, 15 past
    schedule: List[Tuple[str, str]] = []
    for h in [9, 9, 10, 10, 11, 11, 12, 14, 14, 15, 15, 16, 16, 17, 17]:
        schedule.append((_today_slot(h), "today"))
    for d in range(1, 8):
        for _ in range(3):
            schedule.append((_ts(-d), "upcoming"))
    for d in range(1, 8):
        for _ in range(2):
            schedule.append((_ts(d), "past"))

    today_statuses  = ["scheduled","scheduled","scheduled","checked_in","checked_in",
                       "in_progress","in_progress","completed","completed","completed",
                       "completed","completed","scheduled","scheduled","no_show"]
    upcom_statuses  = ["scheduled"] * 20
    past_statuses   = ["completed","completed","completed","cancelled","completed"] * 3

    all_slots    = schedule[:15]
    all_statuses = today_statuses
    all_slots   += schedule[15:35]
    all_statuses += upcom_statuses
    all_slots   += schedule[35:50]
    all_statuses += past_statuses[:15]

    types = ["consultation","follow_up","procedure","consultation","follow_up"]
    for i, ((slot_time, _), status) in enumerate(zip(all_slots, all_statuses), start=1):
        pid = str(rng.choice(patients))
        dept = str(rng.choice(depts))
        rows.append((
            f"apt_{i:05d}", pid, dept,
            f"Dr. {_name(rng, 'Male')}", slot_time, status, "system",
            str(rng.choice(types)), "",
        ))
    with _conn(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO appointments VALUES (?,?,?,?,?,?,?,?,?)", rows
        )


def _seed_lab_orders(db_path: str, rng: np.random.Generator) -> None:
    rows = []
    patients = [f"pat_{i:04d}" for i in range(1, 61)]
    # 25 completed, 15 pending
    statuses  = ["completed"] * 25 + ["ordered"] * 8 + ["sample_collected"] * 7
    priorities= ["routine","routine","routine","urgent","stat"]
    result_values = {
        "Complete Blood Count (CBC)": ("11.8 g/dL","g/dL","HIGH"),
        "Blood Glucose Fasting": ("128 mg/dL","mg/dL","HIGH"),
        "Lipid Profile": ("215 mg/dL","mg/dL","HIGH"),
        "Liver Function Test (LFT)": ("45 U/L","U/L","HIGH"),
        "Kidney Function Test (KFT)": ("1.4 mg/dL","mg/dL","HIGH"),
        "Thyroid Profile (T3/T4/TSH)": ("6.2 mIU/L","mIU/L","HIGH"),
        "Urine Routine & Microscopy": ("Clear","","NORMAL"),
        "Blood Culture & Sensitivity": ("No growth","","NORMAL"),
        "HbA1c": ("7.8%","%","HIGH"),
        "Serum Electrolytes": ("Na 138 mEq/L","mEq/L","NORMAL"),
        "Coagulation Profile (PT/APTT)": ("13.2 sec","sec","NORMAL"),
        "CRP (C-Reactive Protein)": ("42 mg/L","mg/L","HIGH"),
        "Troponin I": ("0.08 ng/mL","ng/mL","HIGH"),
        "ABG (Arterial Blood Gas)": ("pH 7.38","","NORMAL"),
        "Dengue NS1 Antigen": ("Positive","","ABNORMAL"),
    }

    for i, status in enumerate(statuses, start=1):
        pid = str(rng.choice(patients))
        test = _TESTS[i % len(_TESTS)]
        test_name, category, ref, unit = test
        ordered_days_ago = float(rng.integers(0, 5))
        rv, ru, flag = result_values.get(test_name, ("—", unit, "NORMAL"))
        completed_at = _ts(ordered_days_ago - 0.1) if status == "completed" else None
        rows.append((
            f"lab_{i:05d}", pid, _get_patient_name(db_path, pid),
            test_name, category,
            f"Dr. {rng.choice(_MALE)}",
            _ts(ordered_days_ago), str(rng.choice(priorities)),
            status,
            rv if status == "completed" else None,
            ru if status == "completed" else None,
            ref,
            flag if status == "completed" else None,
            completed_at,
            "",
        ))
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO lab_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def _seed_radiology_orders(db_path: str, rng: np.random.Generator) -> None:
    rows = []
    patients = [f"pat_{i:04d}" for i in range(1, 61)]
    statuses = ["completed"] * 15 + ["ordered"] * 6 + ["scheduled"] * 4
    findings_map = {
        "Chest X-Ray PA View": "Bilateral infiltrates noted. No pneumothorax. Cardiomegaly borderline.",
        "CT Head Non-Contrast": "No acute intracranial bleed. Mild cerebral atrophy.",
        "Abdominal Ultrasound": "Liver echogenicity mildly increased. Gallbladder normal.",
        "MRI Brain with Contrast": "Small periventricular white matter changes noted.",
        "CT Chest High Resolution": "Ground glass opacities in lower lobes bilaterally.",
        "Echocardiogram 2D": "EF 45%. Mild LV dysfunction. No pericardial effusion.",
        "CT Abdomen & Pelvis": "No free fluid. Appendix normal. Mild colitis.",
        "Bone Density Scan (DEXA)": "T-score -2.3. Osteopenia noted.",
    }
    for i, status in enumerate(statuses, start=1):
        pid = str(rng.choice(patients))
        scan = _SCANS[i % len(_SCANS)]
        scan_type, modality, body_part = scan
        ordered_days_ago = float(rng.integers(0, 7))
        findings = findings_map.get(scan_type, "No significant findings.") if status == "completed" else None
        impression = "See report." if status == "completed" else None
        rows.append((
            f"rad_{i:05d}", pid, _get_patient_name(db_path, pid),
            scan_type, modality, body_part,
            f"Dr. {rng.choice(_MALE)}",
            _ts(ordered_days_ago), "routine",
            status,
            f"Dr. {rng.choice(_MALE)}" if status == "completed" else None,
            findings, impression,
            _ts(ordered_days_ago - 0.2) if status == "completed" else None,
        ))
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO radiology_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def _seed_pharmacy_orders(db_path: str, rng: np.random.Generator) -> None:
    rows = []
    patients = [f"pat_{i:04d}" for i in range(1, 61)]
    statuses  = ["dispensed"] * 23 + ["prescribed"] * 12
    for i, status in enumerate(statuses, start=1):
        pid = str(rng.choice(patients))
        drug = _DRUGS[i % len(_DRUGS)]
        drug_name, dosage, freq, dur = drug
        prescribed_days_ago = float(rng.integers(0, 5))
        dispensed_at = _ts(prescribed_days_ago - 0.05) if status == "dispensed" else None
        dispensed_by = f"Pharm. {rng.choice(_FEMALE)}" if status == "dispensed" else None
        rows.append((
            f"rx_{i:05d}", pid, _get_patient_name(db_path, pid),
            drug_name, dosage, freq, int(dur),
            f"Dr. {rng.choice(_MALE)}",
            _ts(prescribed_days_ago),
            status, dispensed_at, dispensed_by, "",
        ))
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO pharmacy_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def _seed_iot_devices(db_path: str) -> None:
    rng = _rng(99)
    depts = list(BED_CONFIG.keys()) + ["Radiology", "Pharmacy"]
    types = ["wearable_monitor","infusion_pump","ventilator","bedside_sensor","imaging_gateway"]
    crit  = ["high","high","high","medium","low"]
    rows = []
    for i in range(1, 141):
        dept = str(rng.choice(depts))
        t_idx = int(rng.integers(0, len(types)))
        status = "online" if rng.random() < 0.87 else ("maintenance" if rng.random() < 0.5 else "offline")
        last_seen = _ts(0 if status == "online" else float(rng.integers(1, 48)) / 24)
        rows.append((
            f"dev_{i:04d}", types[t_idx], dept, crit[t_idx],
            f"192.168.{int(rng.integers(1,5))}.{int(rng.integers(10,254))}",
            f"v{int(rng.integers(2,5))}.{int(rng.integers(0,9))}.{int(rng.integers(0,9))}",
            status, last_seen,
        ))
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM iot_devices").fetchone()[0]
        if n == 0:
            conn.executemany("INSERT OR IGNORE INTO iot_devices VALUES (?,?,?,?,?,?,?,?)", rows)


def _seed_extra_iot_devices(db_path: str) -> None:
    """Add 10 new device types (CGM, ECG monitor, pulse oximeter, etc.). Idempotent."""
    NEW_TYPES: list[tuple[str, str, int]] = [
        # (device_type, criticality, count)
        ("cgm_sensor",       "high",     4),
        ("ecg_monitor",      "high",     4),
        ("pulse_oximeter",   "medium",   3),
        ("nibp_monitor",     "medium",   3),
        ("temperature_probe","low",      3),
        ("capnograph",       "high",     3),
        ("smart_iv_pump",    "high",     3),
        ("defibrillator",    "critical", 2),
        ("fetal_monitor",    "high",     2),
        ("dialysis_machine", "high",     2),
        ("bipap_machine",    "high",     2),
    ]
    with _conn(db_path) as conn:
        existing_types = {r[0] for r in conn.execute("SELECT DISTINCT device_type FROM iot_devices").fetchall()}
        max_id = conn.execute("SELECT COUNT(*) FROM iot_devices").fetchone()[0]

    to_add = [(t, c, n) for t, c, n in NEW_TYPES if t not in existing_types]
    if not to_add:
        return

    rng = _rng(77)
    depts = list(BED_CONFIG.keys()) + ["Radiology", "Pharmacy", "Maternity", "Nephrology"]
    rows = []
    counter = max_id + 1
    for dtype, crit, count in to_add:
        for _ in range(count):
            dept = str(rng.choice(depts))
            status = "online" if rng.random() < 0.92 else "maintenance"
            last_seen = _ts(0 if status == "online" else float(rng.integers(1, 12)) / 24)
            rows.append((
                f"dev_{counter:04d}", dtype, dept, crit,
                f"192.168.{int(rng.integers(1,5))}.{int(rng.integers(10,254))}",
                f"v{int(rng.integers(2,5))}.{int(rng.integers(0,9))}.{int(rng.integers(0,9))}",
                status, last_seen,
            ))
            counter += 1

    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO iot_devices VALUES (?,?,?,?,?,?,?,?)", rows)


def _get_patient_name(db_path: str, patient_id: str) -> str:
    try:
        with _conn(db_path) as conn:
            row = conn.execute(
                "SELECT full_name FROM patients WHERE patient_id=?", (patient_id,)
            ).fetchone()
            return row[0] if row else patient_id
    except Exception:
        return patient_id


# ── Legacy seed (backward compat) ────────────────────────────────────────────

def seed_employees(db_path: str) -> None:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if n > 0:
            return
    rng = _rng(1)
    rows = []
    idx = 1
    for dept in _DEPTS:
        for role in _ROLES:
            for shift in _SHIFTS:
                gender = "Male" if idx % 3 != 0 else "Female"
                nm = _name(rng, gender)
                rows.append((
                    f"emp_{idx:04d}", nm, role, dept, shift, "active",
                    f"{nm.split()[0].lower()}{idx}@medicore.in", _phone(rng),
                ))
                idx += 1
    with _conn(db_path) as conn:
        conn.executemany("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?)", rows)


# ── CRUD: Patients ────────────────────────────────────────────────────────────

def add_patient(
    db_path: str, patient_id: str, full_name: str, age: int, gender: str,
    contact: str, triage_level: str, status: str, created_at: str,
) -> None:
    """Legacy add_patient (patients_manual table, backward compat)."""
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO patients_manual VALUES (?,?,?,?,?,?,?,?)",
            (patient_id, full_name, int(age), gender, contact, triage_level, status, created_at),
        )


def add_patient_full(
    db_path: str, full_name: str, age: int, gender: str, blood_group: str,
    contact: str, address: str, triage_level: str, dob: str = "",
) -> str:
    """Add patient to the main patients table. Returns new patient_id."""
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        pid = f"pat_{n+1:04d}_m"
        mrn = f"MRN{datetime.now().strftime('%y')}{n+1:04d}"
        conn.execute(
            "INSERT OR IGNORE INTO patients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, mrn, full_name, dob, int(age), gender, blood_group, contact, address,
             triage_level, "active", "outpatient", _ts(0)),
        )
    return pid


def get_patients(db_path: str, search: str = "", status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM patients"
    params: list = []
    if search or status != "all":
        clauses = []
        if search:
            clauses.append("(full_name LIKE ? OR mrn LIKE ? OR patient_id LIKE ?)")
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        if status != "all":
            clauses.append("status = ?")
            params.append(status)
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY created_at DESC, patient_id ASC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_patient_by_id(db_path: str, patient_id: str) -> Optional[dict]:
    with _conn(db_path) as conn:
        row = conn.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in conn.execute("SELECT * FROM patients LIMIT 0").description]
        return dict(zip(cols, row))


def update_patient_status(db_path: str, patient_id: str, status: str) -> None:
    with _conn(db_path) as conn:
        conn.execute("UPDATE patients SET status=? WHERE patient_id=?", (status, patient_id))


# ── CRUD: Triage ──────────────────────────────────────────────────────────────

def add_triage_patient(
    db_path: str, patient_name: str, age: int, gender: str,
    triage_level: str, chief_complaint: str,
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM triage_queue").fetchone()[0]
        qid = f"tq_{n+1:04d}"
        pid = f"triage_temp_{n+1:04d}"
        conn.execute(
            "INSERT INTO triage_queue VALUES (?,?,?,?,?,?,?,?,?,?)",
            (qid, pid, patient_name, int(age), gender, _ts(0),
             triage_level, chief_complaint, None, "waiting"),
        )
    return qid


def get_triage_queue(db_path: str, status: str = "active") -> pd.DataFrame:
    if status == "active":
        q = "SELECT * FROM triage_queue WHERE status IN ('waiting','in_progress') ORDER BY arrival_time"
    else:
        q = "SELECT * FROM triage_queue ORDER BY arrival_time DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def update_triage_status(db_path: str, queue_id: str, new_status: str) -> None:
    with _conn(db_path) as conn:
        conn.execute("UPDATE triage_queue SET status=? WHERE queue_id=?", (new_status, queue_id))


# ── CRUD: Appointments ────────────────────────────────────────────────────────

def add_appointment(
    db_path: str, appointment_id: str, patient_id: str, department: str,
    clinician_id: Optional[str], slot_time: str, status: str,
    source: str = "manual", appointment_type: str = "consultation", notes: str = "",
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO appointments VALUES (?,?,?,?,?,?,?,?,?)",
            (appointment_id, patient_id, department, clinician_id, slot_time,
             status, source, appointment_type, notes),
        )


def get_appointments(db_path: str, date_filter: str = "today") -> pd.DataFrame:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if date_filter == "today":
        q = f"SELECT * FROM appointments WHERE slot_time LIKE '{today}%' ORDER BY slot_time"
    elif date_filter == "upcoming":
        q = f"SELECT * FROM appointments WHERE slot_time > '{today}T23:59:59' ORDER BY slot_time LIMIT 50"
    else:
        q = "SELECT * FROM appointments ORDER BY slot_time DESC LIMIT 100"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def update_appointment_status(db_path: str, appt_id: str, status: str) -> None:
    with _conn(db_path) as conn:
        conn.execute("UPDATE appointments SET status=? WHERE appointment_id=?", (status, appt_id))


# ── CRUD: Beds / Admissions ───────────────────────────────────────────────────

def get_beds(db_path: str, department: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM beds"
    if department != "all":
        q += f" WHERE department='{department}'"
    q += " ORDER BY department, bed_number"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def get_available_beds(db_path: str, department: str) -> pd.DataFrame:
    with _conn(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM beds WHERE department=? AND status='available'", conn,
            params=(department,),
        )


def get_admissions(db_path: str, status: str = "admitted") -> pd.DataFrame:
    q = "SELECT a.*, p.full_name, p.age, p.gender FROM admissions a LEFT JOIN patients p ON a.patient_id=p.patient_id"
    if status != "all":
        q += f" WHERE a.status='{status}'"
    q += " ORDER BY a.admit_date DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def admit_patient(
    db_path: str, patient_id: str, department: str, bed_id: str,
    diagnosis: str, attending_doctor: str,
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM admissions").fetchone()[0]
        adm_id = f"adm_{n+1:04d}"
        conn.execute(
            "INSERT INTO admissions VALUES (?,?,?,?,?,?,?,?,?,?)",
            (adm_id, patient_id, department, bed_id, _ts(0),
             None, diagnosis, attending_doctor, "admitted", ""),
        )
        conn.execute(
            "UPDATE beds SET status='occupied', patient_id=?, last_updated=? WHERE bed_id=?",
            (patient_id, _ts(0), bed_id),
        )
        conn.execute("UPDATE patients SET status='admitted' WHERE patient_id=?", (patient_id,))
    return adm_id


def discharge_patient(db_path: str, admission_id: str) -> None:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT patient_id, bed_id FROM admissions WHERE admission_id=?", (admission_id,)
        ).fetchone()
        if row:
            pid, bed_id = row
            conn.execute(
                "UPDATE admissions SET status='discharged', discharge_date=? WHERE admission_id=?",
                (_ts(0), admission_id),
            )
            if bed_id:
                conn.execute(
                    "UPDATE beds SET status='available', patient_id=NULL, last_updated=? WHERE bed_id=?",
                    (_ts(0), bed_id),
                )
            conn.execute(
                "UPDATE patients SET status='discharged' WHERE patient_id=?", (pid,)
            )


# ── CRUD: Lab Orders ──────────────────────────────────────────────────────────

def add_lab_order(
    db_path: str, patient_id: str, patient_name: str, test_name: str,
    test_category: str, ordered_by: str, priority: str = "routine",
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM lab_orders").fetchone()[0]
        oid = f"lab_{n+1:05d}"
        ref = next((t[2] for t in _TESTS if t[0] == test_name), "See reference")
        unit = next((t[3] for t in _TESTS if t[0] == test_name), "")
        conn.execute(
            "INSERT INTO lab_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, patient_id, patient_name, test_name, test_category,
             ordered_by, _ts(0), priority, "ordered",
             None, None, ref, None, None, ""),
        )
    return oid


def get_lab_orders(db_path: str, status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM lab_orders"
    if status != "all":
        q += f" WHERE status='{status}'"
    q += " ORDER BY ordered_at DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def update_lab_result(
    db_path: str, order_id: str, result_value: str,
    result_unit: str, result_flag: str,
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE lab_orders SET result_value=?, result_unit=?, result_flag=?, "
            "status='completed', completed_at=? WHERE order_id=?",
            (result_value, result_unit, result_flag, _ts(0), order_id),
        )


# ── CRUD: Radiology Orders ────────────────────────────────────────────────────

def add_radiology_order(
    db_path: str, patient_id: str, patient_name: str, scan_type: str,
    modality: str, body_part: str, ordered_by: str, priority: str = "routine",
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM radiology_orders").fetchone()[0]
        oid = f"rad_{n+1:05d}"
        conn.execute(
            "INSERT INTO radiology_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, patient_id, patient_name, scan_type, modality, body_part,
             ordered_by, _ts(0), priority, "ordered",
             None, None, None, None),
        )
    return oid


def get_radiology_orders(db_path: str, status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM radiology_orders"
    if status != "all":
        q += f" WHERE status='{status}'"
    q += " ORDER BY ordered_at DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def update_radiology_findings(
    db_path: str, order_id: str, radiologist: str, findings: str, impression: str,
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE radiology_orders SET radiologist=?, findings=?, impression=?, "
            "status='completed', completed_at=? WHERE order_id=?",
            (radiologist, findings, impression, _ts(0), order_id),
        )


# ── CRUD: Pharmacy ────────────────────────────────────────────────────────────

def add_pharmacy_order(
    db_path: str, patient_id: str, patient_name: str, drug_name: str,
    dosage: str, frequency: str, duration_days: int, prescribed_by: str,
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM pharmacy_orders").fetchone()[0]
        oid = f"rx_{n+1:05d}"
        conn.execute(
            "INSERT INTO pharmacy_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (oid, patient_id, patient_name, drug_name, dosage, frequency,
             int(duration_days), prescribed_by, _ts(0), "prescribed",
             None, None, ""),
        )
    return oid


def get_pharmacy_orders(db_path: str, status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM pharmacy_orders"
    if status != "all":
        q += f" WHERE status='{status}'"
    q += " ORDER BY prescribed_at DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def dispense_pharmacy_order(db_path: str, order_id: str, dispensed_by: str) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE pharmacy_orders SET status='dispensed', dispensed_at=?, "
            "dispensed_by=? WHERE order_id=?",
            (_ts(0), dispensed_by, order_id),
        )


# ── CRUD: Billing ─────────────────────────────────────────────────────────────

def add_billing_entry(
    db_path: str, bill_id: str, patient_id: str, category: str,
    amount_inr: float, payment_status: str, created_at: str,
    source: str = "manual", description: str = "",
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO billing_entries VALUES (?,?,?,?,?,?,?,?)",
            (bill_id, patient_id, category, float(amount_inr),
             payment_status, created_at, source, description),
        )


def get_billing(db_path: str, patient_id: str = "") -> pd.DataFrame:
    q = "SELECT * FROM billing_entries"
    if patient_id:
        q += f" WHERE patient_id='{patient_id}'"
    q += " ORDER BY created_at DESC"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn)


def update_payment_status(db_path: str, bill_id: str, status: str) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE billing_entries SET payment_status=? WHERE bill_id=?", (status, bill_id)
        )


# ── CRUD: Staff ───────────────────────────────────────────────────────────────

def add_employee(
    db_path: str, full_name: str, role: str, department: str,
    shift: str, email: str = "", phone: str = "",
) -> str:
    with _conn(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        eid = f"emp_{n+1:04d}"
        conn.execute(
            "INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?)",
            (eid, full_name, role, department, shift, "active", email, phone),
        )
    return eid


def get_employees(db_path: str, department: str = "all", role: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM employees"
    clauses = []
    params: list = []
    if department != "all":
        clauses.append("department=?"); params.append(department)
    if role != "all":
        clauses.append("role=?"); params.append(role)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY department, role, employee_id"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)


# ── CRUD: IoMT Devices ────────────────────────────────────────────────────────

def get_devices(db_path: str, department: str = "all", status: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM iot_devices"
    clauses, params = [], []
    if department != "all":
        clauses.append("department=?"); params.append(department)
    if status != "all":
        clauses.append("status=?"); params.append(status)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY department, device_type"
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)


def generate_virtual_iomt_vitals(
    db_path: str,
    samples_per_device: int = 1,
    seed: Optional[int] = None,
    prev_states: Optional[dict] = None,
) -> tuple:
    """
    Generate realistic IoMT telemetry.

    When `prev_states` is supplied (dict keyed by device_id), values drift
    smoothly from the previous reading (mean-reverting random walk).
    When `prev_states` is None, stable baseline values are generated.

    Returns (DataFrame of new rows, new_states dict).
    """
    rng = _rng(seed if seed is not None else int(datetime.now(timezone.utc).timestamp()) % 100000)

    # Ensure table exists (backward-compatible).
    with _conn(db_path) as conn:
        conn.execute(
            """
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
            )
            """
        )
        conn.commit()

    devices = get_devices(db_path, "all", "all")
    if devices.empty:
        return pd.DataFrame(), {}

    with _conn(db_path) as conn:
        admitted = pd.read_sql_query(
            "SELECT patient_id FROM patients WHERE status IN ('admitted','emergency','observation')",
            conn,
        )["patient_id"].tolist()

    # ── Per-device normal targets (realistic hospital population) ─────────────
    # Each device keeps its own "patient" whose vitals drift around these targets.
    _TARGETS = {
        "heart_rate":       75.0,
        "spo2":             98.0,
        "systolic_bp":     118.0,
        "diastolic_bp":     78.0,
        "respiration_rate": 15.0,
        "temperature_c":    36.8,
        "glucose_mg_dl":   100.0,
    }
    # Drift σ per second (small = smooth, realistic second-by-second change)
    _SIGMA = {
        "heart_rate":        0.6,   # ±0.6 bpm/s
        "spo2":              0.08,  # ±0.08 %/s
        "systolic_bp":       0.7,   # ±0.7 mmHg/s
        "diastolic_bp":      0.5,
        "respiration_rate":  0.15,
        "temperature_c":     0.01,  # temp changes very slowly
        "glucose_mg_dl":     0.8,
    }
    _LIMITS = {
        "heart_rate":       (45,  160),
        "spo2":             (88,  100),
        "systolic_bp":      (90,  180),
        "diastolic_bp":     (55,  120),
        "respiration_rate": ( 8,   35),
        "temperature_c":    (35.5, 40.5),
        "glucose_mg_dl":    (55,  350),
    }

    def _drift(prev_val: float, key: str) -> float:
        """Drift from prev_val with mean reversion toward target."""
        target = _TARGETS[key]
        sigma  = _SIGMA[key]
        lo, hi = _LIMITS[key]
        # Mean-reverting random walk: pull 3 % toward target each step
        new = prev_val + float(rng.normal(0, sigma)) + 0.03 * (target - prev_val)
        return float(np.clip(new, lo, hi))

    def _baseline(key: str) -> float:
        lo, hi = _LIMITS[key]
        t = _TARGETS[key]
        return float(np.clip(rng.normal(t, _SIGMA[key] * 5), lo, hi))

    rows = []
    new_states: dict = {}
    ts_now = _ts(0)  # single timestamp for this batch so all rows sort together

    # Keep patient assignment stable per device across calls
    # (patient_id stored in prev_states if available)
    for _, d in devices.iterrows():
        dtype  = str(d["device_type"])
        dev_id = str(d["device_id"])
        prev   = (prev_states or {}).get(dev_id, {})

        for _s in range(max(1, int(samples_per_device))):
            # Patient assignment: reuse prev assignment if available
            if prev.get("patient_id"):
                patient_id = prev["patient_id"]
            elif admitted:
                patient_id = str(rng.choice(admitted)) if rng.random() < 0.8 else None
            else:
                patient_id = None

            if dtype == "imaging_gateway":
                # Infrastructure devices: no direct patient vitals
                hr = spo2 = sys_bp = dia_bp = rr = temp = glu = np.nan
                rhythm = "N/A"
            else:
                if prev:
                    hr     = _drift(prev.get("heart_rate",       _TARGETS["heart_rate"]),       "heart_rate")
                    spo2   = _drift(prev.get("spo2",             _TARGETS["spo2"]),              "spo2")
                    sys_bp = _drift(prev.get("systolic_bp",      _TARGETS["systolic_bp"]),       "systolic_bp")
                    dia_bp = _drift(prev.get("diastolic_bp",     _TARGETS["diastolic_bp"]),      "diastolic_bp")
                    rr     = _drift(prev.get("respiration_rate", _TARGETS["respiration_rate"]),  "respiration_rate")
                    temp   = _drift(prev.get("temperature_c",    _TARGETS["temperature_c"]),     "temperature_c")
                    glu    = _drift(prev.get("glucose_mg_dl",    _TARGETS["glucose_mg_dl"]),     "glucose_mg_dl")
                else:
                    hr, spo2, sys_bp, dia_bp = (
                        _baseline("heart_rate"), _baseline("spo2"),
                        _baseline("systolic_bp"), _baseline("diastolic_bp"),
                    )
                    rr, temp, glu = (
                        _baseline("respiration_rate"),
                        _baseline("temperature_c"),
                        _baseline("glucose_mg_dl"),
                    )

                # Device-type adjustments — set primary metrics and null irrelevant ones
                _NO_RHYTHM = {
                    "infusion_pump", "smart_iv_pump", "pulse_oximeter", "nibp_monitor",
                    "temperature_probe", "capnograph", "dialysis_machine", "bipap_machine",
                    "cgm_sensor",
                }

                if dtype == "ventilator":
                    rr   = float(np.clip(rr, 10, 30))
                    spo2 = float(np.clip(spo2 - 1.5, 88, 100))
                elif dtype in ("infusion_pump", "smart_iv_pump"):
                    rhythm = "N/A"
                elif dtype == "cgm_sensor":
                    # CGM: primary metric is glucose (diabetic patient profile 90–280)
                    glu = float(np.clip(
                        _drift(prev.get("glucose_mg_dl", 145), "glucose_mg_dl") if prev else float(rng.uniform(90, 200)),
                        70, 350,
                    ))
                    hr = spo2 = sys_bp = dia_bp = rr = temp = np.nan
                elif dtype == "ecg_monitor":
                    # ECG: HR + rhythm only
                    spo2 = sys_bp = dia_bp = rr = temp = glu = np.nan
                elif dtype == "pulse_oximeter":
                    spo2 = float(np.clip(spo2, 90, 100))
                    hr   = float(np.clip(hr, 50, 140))
                    sys_bp = dia_bp = rr = temp = glu = np.nan
                elif dtype == "nibp_monitor":
                    sys_bp = float(np.clip(sys_bp, 90, 185))
                    dia_bp = float(np.clip(dia_bp, 55, 120))
                    hr = spo2 = rr = temp = glu = np.nan
                elif dtype == "temperature_probe":
                    temp = float(np.clip(temp, 35.5, 40.5))
                    hr = spo2 = sys_bp = dia_bp = rr = glu = np.nan
                elif dtype == "capnograph":
                    rr   = float(np.clip(rr, 10, 40))   # ETCO2 proxy
                    spo2 = float(np.clip(spo2, 88, 100))
                    hr = sys_bp = dia_bp = temp = glu = np.nan
                elif dtype == "defibrillator":
                    # Occasionally shows arrhythmia (test/standby mode)
                    if rng.random() < 0.06:
                        hr = float(rng.choice([float(rng.uniform(30, 48)), float(rng.uniform(160, 210))]))
                    spo2 = sys_bp = dia_bp = rr = temp = glu = np.nan
                elif dtype == "fetal_monitor":
                    # Fetal HR: 120–160 bpm; map to heart_rate field
                    fhr_target = prev.get("heart_rate", 140) if prev else 140.0
                    hr = float(np.clip(fhr_target + float(rng.normal(0, 1.5)), 100, 175))
                    spo2 = sys_bp = dia_bp = rr = temp = glu = np.nan
                elif dtype == "dialysis_machine":
                    sys_bp = float(np.clip(sys_bp, 100, 180))
                    dia_bp = float(np.clip(dia_bp, 60, 110))
                    temp   = float(np.clip(temp,   36.0, 38.5))
                    hr = spo2 = rr = glu = np.nan
                elif dtype == "bipap_machine":
                    rr   = float(np.clip(rr, 10, 30))
                    spo2 = float(np.clip(spo2 - 0.8, 88, 100))
                    hr = sys_bp = dia_bp = temp = glu = np.nan

                # ECG rhythm assignment
                if dtype in _NO_RHYTHM:
                    rhythm = "N/A"
                elif dtype == "fetal_monitor":
                    rhythm = "FHR"
                elif dtype == "defibrillator":
                    if not np.isnan(hr):
                        rhythm = "V-Fib" if hr > 150 else ("Bradycardia" if hr < 50 else "NSR")
                    else:
                        rhythm = "Standby"
                elif prev.get("ecg_rhythm") and rng.random() > 0.05:
                    rhythm = prev["ecg_rhythm"]
                else:
                    if not np.isnan(hr):
                        if hr > 100:
                            rhythm = "Sinus Tachycardia"
                        elif hr < 60:
                            rhythm = "Sinus Bradycardia"
                        else:
                            rhythm = str(rng.choice(["NSR", "NSR", "NSR", "AF"], p=[0.92, 0.04, 0.02, 0.02]))
                    else:
                        rhythm = "N/A"

            risk_flag = int(
                (not np.isnan(hr)     and (hr > 130 or hr < 50))
                or (not np.isnan(spo2)   and spo2 < 92)
                or (not np.isnan(sys_bp) and (sys_bp > 160 or sys_bp < 90))
                or (not np.isnan(temp)   and temp > 38.5)
                or (not np.isnan(glu)    and (glu > 250 or glu < 65))
            )

            new_states[dev_id] = {
                "device_type":       dtype,
                "department":        str(d["department"]),
                "patient_id":        patient_id,
                "heart_rate":        hr,
                "spo2":              spo2,
                "systolic_bp":       sys_bp,
                "diastolic_bp":      dia_bp,
                "respiration_rate":  rr,
                "temperature_c":     temp,
                "glucose_mg_dl":     glu,
                "ecg_rhythm":        rhythm if dtype != "imaging_gateway" else "N/A",
                "risk_flag":         risk_flag,
            }

            rows.append((
                ts_now, dev_id, dtype, str(d["department"]), patient_id,
                hr, spo2, sys_bp, dia_bp, rr, temp, glu,
                rhythm if dtype != "imaging_gateway" else "N/A",
                risk_flag,
            ))

    with _conn(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO iot_live_vitals(
                timestamp, device_id, device_type, department, patient_id,
                heart_rate, spo2, systolic_bp, diastolic_bp, respiration_rate,
                temperature_c, glucose_mg_dl, ecg_rhythm, risk_flag
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()

    return get_iot_live_vitals(db_path, limit=len(rows)), new_states


def get_iot_live_vitals(db_path: str, limit: int = 500, device_id: str = "all") -> pd.DataFrame:
    q = "SELECT * FROM iot_live_vitals"
    params = []
    if device_id != "all":
        q += " WHERE device_id=?"
        params.append(device_id)
    q += " ORDER BY timestamp DESC, record_id DESC LIMIT ?"
    params.append(int(limit))
    with _conn(db_path) as conn:
        return pd.read_sql_query(q, conn, params=params)


# ── Analytics / census ────────────────────────────────────────────────────────

def get_census(db_path: str) -> dict:
    with _conn(db_path) as conn:
        total_patients = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        admitted       = conn.execute("SELECT COUNT(*) FROM patients WHERE status='admitted'").fetchone()[0]
        emergency      = conn.execute("SELECT COUNT(*) FROM patients WHERE status='emergency'").fetchone()[0]
        total_beds     = conn.execute("SELECT COUNT(*) FROM beds").fetchone()[0]
        occupied_beds  = conn.execute("SELECT COUNT(*) FROM beds WHERE status='occupied'").fetchone()[0]
        triage_waiting = conn.execute("SELECT COUNT(*) FROM triage_queue WHERE status='waiting'").fetchone()[0]
        staff_on_duty  = conn.execute("SELECT COUNT(*) FROM employees WHERE shift='Morning' AND status='active'").fetchone()[0]
        pending_labs   = conn.execute("SELECT COUNT(*) FROM lab_orders WHERE status IN ('ordered','sample_collected')").fetchone()[0]
        pending_rx     = conn.execute("SELECT COUNT(*) FROM pharmacy_orders WHERE status='prescribed'").fetchone()[0]
    return {
        "total_patients": int(total_patients),
        "admitted":        int(admitted),
        "emergency":       int(emergency),
        "total_beds":      int(total_beds),
        "occupied_beds":   int(occupied_beds),
        "available_beds":  int(total_beds - occupied_beds),
        "bed_occupancy_pct": round(occupied_beds / max(total_beds, 1) * 100, 1),
        "triage_waiting":  int(triage_waiting),
        "staff_on_duty":   int(staff_on_duty),
        "pending_labs":    int(pending_labs),
        "pending_rx":      int(pending_rx),
    }


def get_bed_summary(db_path: str) -> pd.DataFrame:
    with _conn(db_path) as conn:
        return pd.read_sql_query(
            """SELECT department,
               COUNT(*) AS total,
               SUM(CASE WHEN status='occupied' THEN 1 ELSE 0 END) AS occupied,
               SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) AS available,
               ROUND(SUM(CASE WHEN status='occupied' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS occupancy_pct
               FROM beds GROUP BY department ORDER BY department""",
            conn,
        )


def get_revenue_summary(db_path: str) -> pd.DataFrame:
    with _conn(db_path) as conn:
        return pd.read_sql_query(
            """SELECT category,
               COUNT(*) AS bills,
               ROUND(SUM(amount_inr),0) AS revenue_inr,
               ROUND(SUM(CASE WHEN payment_status='paid' THEN amount_inr ELSE 0 END),0) AS collected_inr,
               ROUND(SUM(CASE WHEN payment_status='pending' THEN amount_inr ELSE 0 END),0) AS pending_inr
               FROM billing_entries GROUP BY category ORDER BY revenue_inr DESC""",
            conn,
        )


def read_table(db_path: str, table_name: str) -> pd.DataFrame:
    with _conn(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
