"""
MediCore Hospital Management System
Full-stack Streamlit dashboard — single entry point.
Run: streamlit run dashboard.py
"""
from __future__ import annotations

import io
import json
import sys
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import styles
from config import SystemConfig
from hospital_db import (
    BED_CONFIG, DB_NAME,
    _DEPTS, _ROLES, _SHIFTS, _TESTS, _SCANS, _DRUGS,
    add_appointment, add_billing_entry, add_employee,
    add_lab_order, add_patient, add_patient_full,
    add_pharmacy_order, add_radiology_order, add_triage_patient,
    admit_patient, discharge_patient,
    dispense_pharmacy_order,
    get_admissions, get_appointments, get_bed_summary, get_beds,
    get_available_beds, get_billing, get_census, get_devices,
    generate_virtual_iomt_vitals, get_iot_live_vitals,
    get_employees, get_lab_orders, get_patients, get_pharmacy_orders,
    get_radiology_orders, get_revenue_summary, get_triage_queue,
    init_db, read_table, seed_all,
    update_appointment_status, update_lab_result,
    update_payment_status, update_radiology_findings,
    update_triage_status,
)
from workflow_system import run_system

ROOT = Path(__file__).resolve().parent
OUT  = ROOT / "outputs"
DB_PATH = str(OUT / DB_NAME)
EVENTS_CSV = OUT / "hospital_workflow_events.csv"
ATTACK_IMPACT_JSON = OUT / "attack_impact_report.json"
IDS_RESULTS_JSON   = OUT / "ids_detection_results.json"
IDS_HISTORY_JSON   = OUT / "ids_attack_history.json"   # persistent log of every attack session

# ── Med-IoMT AI-IDS integration (file-based — no inference here) ─────────────
# MedGuard-IDS model dashboard writes ids_detection_results.json
# This dashboard reads it. No model loading or inference in this process.
_MED_IOMT = ROOT.parent / "Med-IoMT"
BEFORE_ATTACK_EVENTS_CSV = OUT / "hospital_workflow_events_before_attack.csv"
ATTACK_LAB_ROOT = ROOT.parent / "iomt_attack_lab"

PAGES = [
    "IoMT Devices",
    "Attack Impact",
]

TRIAGE_COLORS = {
    "critical": "#dc2626",
    "high":     "#ea580c",
    "medium":   "#d97706",
    "low":      "#16a34a",
}


# ── Startup ───────────────────────────────────────────────────────────────────

def _bootstrap() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    init_db(str(OUT))
    seed_all(DB_PATH)
    # Generate workflow CSV and seed billing if either is missing
    billing_empty = len(get_billing(DB_PATH)) == 0
    if not EVENTS_CSV.exists() or billing_empty:
        run_system(output_dir=str(OUT), cfg=SystemConfig())


# ── Shared helpers ────────────────────────────────────────────────────────────

def _triage_badge(level: str) -> str:
    color = TRIAGE_COLORS.get(level.lower(), "#64748b")
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:20px;font-size:0.72rem;font-weight:700;'
        f'text-transform:uppercase">{level}</span>'
    )


def _status_color(status: str) -> str:
    m = {
        "waiting": "#fbbf24", "in_progress": "#3b82f6", "admitted": "#1d4ed8",
        "discharged": "#64748b", "completed": "#15803d", "dispensed": "#15803d",
        "prescribed": "#d97706", "ordered": "#6366f1", "scheduled": "#0891b2",
        "checked_in": "#16a34a", "online": "#15803d", "offline": "#dc2626",
        "maintenance": "#d97706", "available": "#15803d", "occupied": "#dc2626",
        "active": "#1d4ed8",
    }
    return m.get(status.lower(), "#64748b")


def _fmt_inr(v: float) -> str:
    return f"₹{v:,.0f}"


def _load_events() -> pd.DataFrame:
    if EVENTS_CSV.exists():
        return pd.read_csv(EVENTS_CSV)
    return pd.DataFrame()


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _to_dt(values):
    # Handle mixed ISO8601 strings (with/without fractional seconds/timezone) safely.
    try:
        return pd.to_datetime(values, format="mixed", utc=True, errors="coerce")
    except Exception:
        return pd.to_datetime(values, utc=True, errors="coerce")


def _fmt_dt(values, fmt: str):
    parsed = _to_dt(values)
    if isinstance(parsed, pd.Series):
        return parsed.dt.strftime(fmt).fillna("-")
    if pd.isna(parsed):
        return "-"
    return parsed.strftime(fmt)


# ── Page 1: Overview ──────────────────────────────────────────────────────────

def page_overview() -> None:
    st.markdown(styles.page_header("🏥 MediCore Hospital", "Live Operations Overview"), unsafe_allow_html=True)

    census = get_census(DB_PATH)

    c = st.columns(6)
    kpis = [
        (census["total_patients"],  "Total Patients",   "blue"),
        (census["admitted"],         "Admitted (IPD)",   "blue"),
        (f"{census['occupied_beds']}/{census['total_beds']}",
         "Beds Occupied",
         "orange" if census["bed_occupancy_pct"] > 80 else "green"),
        (census["triage_waiting"],  "ER Waiting",
         "red" if census["triage_waiting"] > 3 else "green"),
        (census["pending_labs"],    "Pending Labs",      "orange"),
        (census["pending_rx"],      "Pending Rx",        "teal"),
    ]
    for col, (val, label, color) in zip(c, kpis):
        col.markdown(styles.kpi_card(val, label, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])

    with col1:
        bed_df = get_bed_summary(DB_PATH)
        if not bed_df.empty:
            fig = go.Figure()
            fig.add_bar(name="Occupied",  x=bed_df["department"], y=bed_df["occupied"],  marker_color="#b91c1c")
            fig.add_bar(name="Available", x=bed_df["department"], y=bed_df["available"], marker_color="#16a34a")
            fig.update_layout(
                barmode="stack", title="Bed Occupancy by Department",
                template="plotly_white", height=340,
                margin=dict(t=48, b=70, l=10, r=10),
                legend=dict(
                    orientation="h", xanchor="center", x=0.5,
                    yanchor="top", y=-0.18,
                ),
                xaxis=dict(tickangle=-20),
                yaxis_title="Beds",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🚨 Active Triage Queue</div>', unsafe_allow_html=True)
        tq = get_triage_queue(DB_PATH, "active")
        if tq.empty:
            st.success("No active patients in triage.")
        else:
            for _, row in tq.iterrows():
                color = TRIAGE_COLORS.get(str(row["triage_level"]), "#64748b")
                st.markdown(
                    f'<div style="border-left:4px solid {color};background:white;'
                    f'padding:8px 12px;border-radius:0 8px 8px 0;margin:4px 0;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.07)">'
                    f'<b>{row["patient_name"]}</b> &nbsp;'
                    + _triage_badge(str(row["triage_level"]))
                    + f'<br><small style="color:#475569">{row["chief_complaint"]} · {row["status"]}</small>'
                    + '</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<br>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="section-title">📅 Today\'s Appointments</div>', unsafe_allow_html=True)
        appts = get_appointments(DB_PATH, "today")
        if appts.empty:
            st.info("No appointments today.")
        else:
            disp = appts[["appointment_id","patient_id","department","clinician_id","slot_time","status"]].head(8).copy()
            disp["slot_time"] = _to_dt(disp["slot_time"]).dt.strftime("%H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)

    with col4:
        st.markdown('<div class="section-title">🛏️ Recent Admissions</div>', unsafe_allow_html=True)
        adm = get_admissions(DB_PATH, "admitted")
        if adm.empty:
            st.info("No current admissions.")
        else:
            disp = adm[["admission_id","full_name","department","diagnosis","admit_date"]].head(8).copy()
            disp["admit_date"] = _to_dt(disp["admit_date"]).dt.strftime("%d %b %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)


# ── Page 2: Patient Registry ──────────────────────────────────────────────────

def page_patients() -> None:
    st.markdown(styles.page_header("👥 Patient Registry", "Register, search, and manage patient records"), unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    search = col1.text_input("🔍 Search by name, MRN, or patient ID", placeholder="e.g. Arjun or MRN26001")
    status_filter = col2.selectbox("Filter by status", ["all","active","admitted","emergency","observation","discharged"])

    patients_df = get_patients(DB_PATH, search, status_filter)
    st.markdown(f"**{len(patients_df)} patients found**")
    if not patients_df.empty:
        disp = patients_df[["patient_id","mrn","full_name","age","gender","blood_group","triage_level","status","created_at"]].copy()
        disp["created_at"] = _to_dt(disp["created_at"]).dt.strftime("%d %b %Y")
        st.dataframe(disp, use_container_width=True, hide_index=True, height=320)

    with st.expander("➕ Register New Patient", expanded=False):
        with st.form("reg_patient_form"):
            r1, r2 = st.columns(2)
            full_name   = r1.text_input("Full Name *")
            age         = r2.number_input("Age *", 0, 120, 35)
            r3, r4 = st.columns(2)
            gender      = r3.selectbox("Gender", ["Male","Female","Other"])
            blood_group = r4.selectbox("Blood Group", ["A+","A-","B+","B-","AB+","AB-","O+","O-","Unknown"])
            r5, r6 = st.columns(2)
            contact     = r5.text_input("Contact Number")
            triage      = r6.selectbox("Triage Level", ["medium","low","high","critical"])
            r7, r8 = st.columns(2)
            address     = r7.text_input("Address / City")
            dob         = r8.text_input("Date of Birth (YYYY-MM-DD)", placeholder="1990-01-01")
            if st.form_submit_button("Save Patient", type="primary"):
                if full_name.strip():
                    pid = add_patient_full(DB_PATH, full_name.strip(), int(age), gender,
                                           blood_group, contact, address, triage, dob)
                    st.success(f"Patient registered. ID: {pid}")
                    st.rerun()
                else:
                    st.error("Full Name is required.")

    with st.expander("🔎 View Patient Profile", expanded=False):
        pid_input = st.text_input("Enter Patient ID", placeholder="pat_0001")
        if pid_input:
            from hospital_db import get_patient_by_id
            p = get_patient_by_id(DB_PATH, pid_input.strip())
            if p:
                c1, c2, c3 = st.columns(3)
                c1.metric("Name",         p["full_name"])
                c2.metric("MRN",          p["mrn"])
                c3.metric("Status",       p["status"].upper())
                c1.metric("Age / Gender", f"{p['age']} / {p['gender']}")
                c2.metric("Blood Group",  p["blood_group"] or "—")
                c3.metric("Triage",       p["triage_level"].upper())
                ptabs = st.tabs(["Labs","Radiology","Pharmacy","Billing","Appointments"])
                with ptabs[0]:
                    ldf = get_lab_orders(DB_PATH)
                    st.dataframe(ldf[ldf["patient_id"]==pid_input][
                        ["order_id","test_name","status","result_value","result_flag","ordered_at"]
                    ], use_container_width=True, hide_index=True)
                with ptabs[1]:
                    rdf = get_radiology_orders(DB_PATH)
                    st.dataframe(rdf[rdf["patient_id"]==pid_input][
                        ["order_id","scan_type","modality","status","findings","ordered_at"]
                    ], use_container_width=True, hide_index=True)
                with ptabs[2]:
                    rxdf = get_pharmacy_orders(DB_PATH)
                    st.dataframe(rxdf[rxdf["patient_id"]==pid_input][
                        ["order_id","drug_name","dosage","frequency","status","prescribed_at"]
                    ], use_container_width=True, hide_index=True)
                with ptabs[3]:
                    st.dataframe(get_billing(DB_PATH, pid_input)[
                        ["bill_id","category","amount_inr","payment_status","created_at"]
                    ], use_container_width=True, hide_index=True)
                with ptabs[4]:
                    adf = get_appointments(DB_PATH, "all")
                    st.dataframe(adf[adf["patient_id"]==pid_input][
                        ["appointment_id","department","clinician_id","slot_time","status"]
                    ], use_container_width=True, hide_index=True)
            else:
                st.warning("Patient not found.")


# ── Page 3: OPD / Appointments ────────────────────────────────────────────────

def page_opd() -> None:
    st.markdown(styles.page_header("📅 OPD / Appointments", "Outpatient scheduling, queue management, and consultations"), unsafe_allow_html=True)

    tabs = st.tabs(["Today's Queue", "Upcoming", "All History", "Book Appointment"])

    with tabs[0]:
        df = get_appointments(DB_PATH, "today")
        if df.empty:
            st.info("No appointments scheduled for today.")
        else:
            df["slot_time_fmt"] = _to_dt(df["slot_time"]).dt.strftime("%H:%M")
            st.dataframe(
                df[["slot_time_fmt","patient_id","department","clinician_id","appointment_type","status"]].rename(
                    columns={"slot_time_fmt":"Time"}
                ),
                use_container_width=True, hide_index=True,
            )
            st.markdown("#### Quick Status Update")
            c1, c2, c3 = st.columns(3)
            sel_appt  = c1.selectbox("Appointment ID", df["appointment_id"].tolist())
            new_status = c2.selectbox("New Status", ["checked_in","in_progress","completed","no_show","cancelled"])
            c3.markdown("<br>", unsafe_allow_html=True)
            if c3.button("Update Status", use_container_width=True):
                update_appointment_status(DB_PATH, sel_appt, new_status)
                st.success(f"{sel_appt} → {new_status}")
                st.rerun()

    with tabs[1]:
        df = get_appointments(DB_PATH, "upcoming")
        if df.empty:
            st.info("No upcoming appointments.")
        else:
            df["slot_time"] = _to_dt(df["slot_time"]).dt.strftime("%d %b %Y %H:%M")
            st.dataframe(df[["appointment_id","patient_id","department","clinician_id","slot_time","status"]],
                         use_container_width=True, hide_index=True)

    with tabs[2]:
        df = get_appointments(DB_PATH, "all")
        df["slot_time"] = _to_dt(df["slot_time"]).dt.strftime("%d %b %Y %H:%M")
        st.dataframe(df[["appointment_id","patient_id","department","clinician_id","slot_time","status","source"]],
                     use_container_width=True, hide_index=True, height=400)

    with tabs[3]:
        with st.form("book_appt_form"):
            st.markdown("#### Book New Appointment")
            a1, a2 = st.columns(2)
            pat_id    = a1.text_input("Patient ID *", placeholder="pat_0001")
            dept      = a2.selectbox("Department", _DEPTS)
            a3, a4 = st.columns(2)
            doctor    = a3.text_input("Clinician Name", placeholder="Dr. Sharma")
            appt_type = a4.selectbox("Type", ["consultation","follow_up","procedure","vaccination","review"])
            a5, a6 = st.columns(2)
            slot_date = a5.date_input("Date", value=datetime.now().date())
            slot_time = a6.time_input("Time", value=datetime.now().replace(hour=10, minute=0).time())
            notes = st.text_area("Notes", height=60)
            if st.form_submit_button("Book Appointment", type="primary"):
                if pat_id.strip():
                    import uuid
                    slot = datetime.combine(slot_date, slot_time, tzinfo=timezone.utc).isoformat()
                    aid = f"apt_m_{uuid.uuid4().hex[:6]}"
                    add_appointment(DB_PATH, aid, pat_id.strip(), dept, doctor or None,
                                    slot, "scheduled", "manual", appt_type, notes)
                    st.success(f"Appointment booked: {aid}")
                    st.rerun()
                else:
                    st.error("Patient ID is required.")


# ── Page 4: Emergency ─────────────────────────────────────────────────────────

def page_emergency() -> None:
    st.markdown(styles.page_header("🚨 Emergency Department", "Triage queue, priority management, and ED workflow"), unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### Active Triage Queue")
        tq = get_triage_queue(DB_PATH, "active")
        if tq.empty:
            st.success("Emergency department is clear.")
        else:
            for _, row in tq.iterrows():
                color   = TRIAGE_COLORS.get(str(row["triage_level"]), "#64748b")
                arrival = _fmt_dt(row["arrival_time"], "%H:%M")
                st.markdown(
                    f'<div style="background:white;border-left:5px solid {color};border-radius:0 10px 10px 0;'
                    f'padding:12px 16px;margin:6px 0;box-shadow:0 1px 4px rgba(0,0,0,0.08)">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><b style="font-size:1rem">{row["patient_name"]}</b> &nbsp;'
                    + _triage_badge(str(row["triage_level"]))
                    + f'<br><span style="color:#475569;font-size:0.85rem">Complaint: {row["chief_complaint"]}</span></div>'
                    + f'<div style="text-align:right"><span style="font-size:0.82rem;color:#64748b">Arrived {arrival}</span>'
                    + f'<br><b style="color:{_status_color(str(row["status"]))};font-size:0.8rem">{str(row["status"]).upper()}</b></div>'
                    + '</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("#### Update Triage Status")
        all_tq = get_triage_queue(DB_PATH, "all")
        if not all_tq.empty:
            c1, c2, c3 = st.columns(3)
            qid   = c1.selectbox("Queue ID", all_tq["queue_id"].tolist())
            new_s = c2.selectbox("Status", ["waiting","in_progress","admitted","discharged","deceased"])
            c3.markdown("<br>", unsafe_allow_html=True)
            if c3.button("Update", use_container_width=True):
                update_triage_status(DB_PATH, qid, new_s)
                st.success("Updated.")
                st.rerun()

    with col_right:
        all_tq = get_triage_queue(DB_PATH, "all")
        if not all_tq.empty:
            triage_counts = all_tq["triage_level"].value_counts().reset_index()
            triage_counts.columns = ["level","count"]
            fig = px.pie(triage_counts, names="level", values="count",
                         title="Triage Distribution",
                         color="level", color_discrete_map=TRIAGE_COLORS,
                         template="plotly_white", height=240)
            fig.update_layout(margin=dict(t=40,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("🆕 Register ED Patient", expanded=True):
            with st.form("ed_register_form"):
                name    = st.text_input("Patient Name *")
                c1, c2 = st.columns(2)
                age     = c1.number_input("Age", 0, 120, 40)
                gender  = c2.selectbox("Gender", ["Male","Female","Other"])
                triage  = st.selectbox("Triage Level", ["critical","high","medium","low"])
                complaint = st.text_area("Chief Complaint *", height=70)
                if st.form_submit_button("Register & Queue", type="primary"):
                    if name.strip() and complaint.strip():
                        qid = add_triage_patient(DB_PATH, name.strip(), int(age), gender, triage, complaint.strip())
                        st.success(f"Queued: {qid}")
                        st.rerun()
                    else:
                        st.error("Name and complaint required.")


# ── Page 5: IPD / Wards ───────────────────────────────────────────────────────

def page_ipd() -> None:
    st.markdown(styles.page_header("🛏️ IPD / Wards", "Bed management, admissions, and inpatient tracking"), unsafe_allow_html=True)

    tabs = st.tabs(["Bed Map", "Active Admissions", "Admit Patient", "Discharge Patient"])

    with tabs[0]:
        bed_sum = get_bed_summary(DB_PATH)
        if not bed_sum.empty:
            cards_per_row = 3
            for start in range(0, len(bed_sum), cards_per_row):
                chunk = bed_sum.iloc[start:start + cards_per_row]
                cols = st.columns(cards_per_row)
                for col, (_, row) in zip(cols, chunk.iterrows()):
                    occ_pct = float(row["occupancy_pct"])
                    color = "#dc2626" if occ_pct > 85 else "#d97706" if occ_pct > 65 else "#15803d"
                    col.markdown(
                        f'<div style="background:white;border-radius:10px;padding:16px;'
                        f'border-top:4px solid {color};text-align:center;min-height:140px;'
                        f'box-shadow:0 1px 4px rgba(0,0,0,0.07);margin:4px">'
                        f'<b style="font-size:0.9rem;color:#0f172a">{row["department"]}</b><br>'
                        f'<span style="font-size:2rem;font-weight:700;color:{color}">{occ_pct:.0f}%</span><br>'
                        f'<span style="font-size:0.85rem;color:#475569">{row["occupied"]}/{row["total"]} beds</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<br>**Bed Detail by Department**")
        for dept in BED_CONFIG:
            beds_df = get_beds(DB_PATH, dept)
            if beds_df.empty:
                continue
            st.markdown(f"**{dept}**")
            n_cols = min(10, len(beds_df))
            cols = st.columns(n_cols)
            for i, (_, bed) in enumerate(beds_df.iterrows()):
                css_cls = (
                    "bed-occupied"    if bed["status"] == "occupied"    else
                    "bed-maintenance" if bed["status"] == "maintenance" else
                    "bed-available"
                )
                cols[i % n_cols].markdown(
                    f'<div class="{css_cls}">{bed["bed_number"]}</div>', unsafe_allow_html=True
                )
            st.markdown("")

    with tabs[1]:
        adm_df = get_admissions(DB_PATH, "admitted")
        if adm_df.empty:
            st.info("No current inpatients.")
        else:
            disp = adm_df[["admission_id","full_name","age","gender","department","bed_id","diagnosis","attending_doctor","admit_date"]].copy()
            disp["admit_date"] = _to_dt(disp["admit_date"]).dt.strftime("%d %b %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

    with tabs[2]:
        with st.form("admit_form"):
            st.markdown("#### Admit Patient to Ward")
            a1, a2 = st.columns(2)
            pid       = a1.text_input("Patient ID *", placeholder="pat_0001")
            dept      = a2.selectbox("Department", list(BED_CONFIG.keys()))
            a3, a4 = st.columns(2)
            diagnosis = a3.text_input("Diagnosis *")
            doctor    = a4.text_input("Attending Doctor *", placeholder="Dr. Kumar")
            if st.form_submit_button("Admit Patient", type="primary"):
                if pid.strip() and diagnosis.strip() and doctor.strip():
                    available = get_available_beds(DB_PATH, dept)
                    if available.empty:
                        st.error(f"No available beds in {dept}.")
                    else:
                        bed_id = available.iloc[0]["bed_id"]
                        adm_id = admit_patient(DB_PATH, pid.strip(), dept, bed_id, diagnosis, doctor)
                        st.success(f"Admitted. Admission ID: {adm_id} | Bed: {bed_id}")
                        st.rerun()
                else:
                    st.error("All fields required.")

    with tabs[3]:
        adm_df = get_admissions(DB_PATH, "admitted")
        if adm_df.empty:
            st.info("No current admissions.")
        else:
            c1, c2 = st.columns(2)
            sel = c1.selectbox("Admission ID", adm_df["admission_id"].tolist())
            c2.markdown("<br>", unsafe_allow_html=True)
            if c2.button("Discharge Patient", type="primary", use_container_width=True):
                discharge_patient(DB_PATH, sel)
                st.success(f"Discharged: {sel}")
                st.rerun()


# ── Page 6: Laboratory ────────────────────────────────────────────────────────

def page_lab() -> None:
    st.markdown(styles.page_header("🧪 Laboratory", "Test ordering, sample tracking, and result management"), unsafe_allow_html=True)

    tabs = st.tabs(["Pending Tests", "Enter Results", "All Orders", "Order Test"])

    with tabs[0]:
        df_o  = get_lab_orders(DB_PATH, "ordered")
        df_sc = get_lab_orders(DB_PATH, "sample_collected")
        pending = pd.concat([df_o, df_sc])
        if pending.empty:
            st.success("No pending lab tests.")
        else:
            disp = pending[["order_id","patient_name","test_name","test_category","priority","ordered_by","ordered_at","status"]].copy()
            disp["ordered_at"] = _to_dt(disp["ordered_at"]).dt.strftime("%d %b %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)

    with tabs[1]:
        pending_ids = (
            get_lab_orders(DB_PATH, "ordered")["order_id"].tolist()
            + get_lab_orders(DB_PATH, "sample_collected")["order_id"].tolist()
        )
        if not pending_ids:
            st.info("No pending orders to update.")
        else:
            with st.form("lab_result_form"):
                c1, c2 = st.columns(2)
                oid  = c1.selectbox("Order ID", pending_ids)
                flag = c2.selectbox("Result Flag", ["NORMAL","HIGH","LOW","ABNORMAL","CRITICAL"])
                v1, v2 = st.columns(2)
                result_val  = v1.text_input("Result Value", placeholder="e.g. 12.4")
                result_unit = v2.text_input("Unit", placeholder="g/dL")
                if st.form_submit_button("Submit Result", type="primary"):
                    update_lab_result(DB_PATH, oid, result_val, result_unit, flag)
                    st.success(f"Result recorded for {oid}")
                    st.rerun()

    with tabs[2]:
        df = get_lab_orders(DB_PATH)
        df["ordered_at"] = _to_dt(df["ordered_at"]).dt.strftime("%d %b %H:%M")
        st.dataframe(df[["order_id","patient_name","test_name","status","result_value","result_flag","ordered_at"]],
                     use_container_width=True, hide_index=True, height=400)

    with tabs[3]:
        with st.form("lab_order_form"):
            st.markdown("#### Order New Test")
            c1, c2 = st.columns(2)
            pid_lab = c1.text_input("Patient ID *", placeholder="pat_0001")
            pname   = c2.text_input("Patient Name *")
            test_options = [t[0] for t in _TESTS]
            test_name = st.selectbox("Test", test_options)
            test_cat  = next((t[1] for t in _TESTS if t[0] == test_name), "")
            c3, c4 = st.columns(2)
            ordered_by = c3.text_input("Ordered By *", placeholder="Dr. Sharma")
            priority   = c4.selectbox("Priority", ["routine","urgent","stat"])
            if st.form_submit_button("Place Order", type="primary"):
                if pid_lab.strip() and pname.strip() and ordered_by.strip():
                    oid = add_lab_order(DB_PATH, pid_lab, pname, test_name, test_cat, ordered_by, priority)
                    st.success(f"Test ordered: {oid}")
                    st.rerun()
                else:
                    st.error("Patient ID, Name, and Doctor required.")


# ── Page 7: Radiology ─────────────────────────────────────────────────────────

def page_radiology() -> None:
    st.markdown(styles.page_header("📡 Radiology", "Scan ordering, scheduling, and report management"), unsafe_allow_html=True)

    tabs = st.tabs(["Pending Scans", "Enter Findings", "All Orders", "Order Scan"])

    with tabs[0]:
        df_o  = get_radiology_orders(DB_PATH, "ordered")
        df_sc = get_radiology_orders(DB_PATH, "scheduled")
        pending = pd.concat([df_o, df_sc])
        if pending.empty:
            st.success("No pending radiology scans.")
        else:
            disp = pending[["order_id","patient_name","scan_type","modality","body_part","priority","ordered_by","ordered_at","status"]].copy()
            disp["ordered_at"] = _to_dt(disp["ordered_at"]).dt.strftime("%d %b %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)

    with tabs[1]:
        pending_ids = (
            get_radiology_orders(DB_PATH, "ordered")["order_id"].tolist()
            + get_radiology_orders(DB_PATH, "scheduled")["order_id"].tolist()
        )
        if not pending_ids:
            st.info("No pending scans to report.")
        else:
            with st.form("rad_findings_form"):
                oid         = st.selectbox("Order ID", pending_ids)
                radiologist = st.text_input("Radiologist Name *", placeholder="Dr. Iyer")
                findings    = st.text_area("Findings *", height=100)
                impression  = st.text_area("Impression", height=70)
                if st.form_submit_button("Submit Report", type="primary"):
                    update_radiology_findings(DB_PATH, oid, radiologist, findings, impression)
                    st.success(f"Report submitted for {oid}")
                    st.rerun()

    with tabs[2]:
        df = get_radiology_orders(DB_PATH)
        df["ordered_at"] = _to_dt(df["ordered_at"]).dt.strftime("%d %b %H:%M")
        st.dataframe(df[["order_id","patient_name","scan_type","modality","status","radiologist","impression","ordered_at"]],
                     use_container_width=True, hide_index=True, height=400)

    with tabs[3]:
        with st.form("rad_order_form"):
            st.markdown("#### Order New Scan")
            c1, c2 = st.columns(2)
            pid_rad   = c1.text_input("Patient ID *", placeholder="pat_0001")
            pname_rad = c2.text_input("Patient Name *")
            scan_options = [s[0] for s in _SCANS]
            scan_name = st.selectbox("Scan Type", scan_options)
            selected_scan = next((s for s in _SCANS if s[0] == scan_name), _SCANS[0])
            c3, c4 = st.columns(2)
            modality  = c3.text_input("Modality",  value=selected_scan[1])
            body_part = c4.text_input("Body Part", value=selected_scan[2])
            c5, c6 = st.columns(2)
            ordered_by_rad = c5.text_input("Ordered By *", placeholder="Dr. Sharma")
            priority_rad   = c6.selectbox("Priority", ["routine","urgent","stat"])
            if st.form_submit_button("Order Scan", type="primary"):
                if pid_rad.strip() and pname_rad.strip() and ordered_by_rad.strip():
                    oid = add_radiology_order(DB_PATH, pid_rad, pname_rad, scan_name,
                                              modality, body_part, ordered_by_rad, priority_rad)
                    st.success(f"Scan ordered: {oid}")
                    st.rerun()
                else:
                    st.error("Patient ID, Name, and Doctor required.")


# ── Page 8: Pharmacy ──────────────────────────────────────────────────────────

def page_pharmacy() -> None:
    st.markdown(styles.page_header("💊 Pharmacy", "Prescription management and drug dispensing"), unsafe_allow_html=True)

    tabs = st.tabs(["Dispensing Queue", "Dispense Drug", "History", "Prescribe"])

    with tabs[0]:
        df = get_pharmacy_orders(DB_PATH, "prescribed")
        if df.empty:
            st.success("Dispensing queue is empty.")
        else:
            disp = df[["order_id","patient_name","drug_name","dosage","frequency","duration_days","prescribed_by","prescribed_at"]].copy()
            disp["prescribed_at"] = _to_dt(disp["prescribed_at"]).dt.strftime("%d %b %H:%M")
            st.dataframe(disp, use_container_width=True, hide_index=True)
            st.metric("Pending Dispensing", len(df))

    with tabs[1]:
        pending_ids = get_pharmacy_orders(DB_PATH, "prescribed")["order_id"].tolist()
        if not pending_ids:
            st.info("No prescriptions pending dispensing.")
        else:
            with st.form("dispense_form"):
                c1, c2 = st.columns(2)
                oid        = c1.selectbox("Order ID", pending_ids)
                pharmacist = c2.text_input("Dispensed By *", placeholder="Pharm. Nair")
                if st.form_submit_button("Mark as Dispensed", type="primary"):
                    if pharmacist.strip():
                        dispense_pharmacy_order(DB_PATH, oid, pharmacist)
                        st.success(f"Dispensed: {oid}")
                        st.rerun()
                    else:
                        st.error("Pharmacist name required.")

    with tabs[2]:
        df = get_pharmacy_orders(DB_PATH)
        df["prescribed_at"] = _to_dt(df["prescribed_at"]).dt.strftime("%d %b %H:%M")
        st.dataframe(df[["order_id","patient_name","drug_name","dosage","frequency","status","dispensed_by","prescribed_at"]],
                     use_container_width=True, hide_index=True, height=400)

    with tabs[3]:
        with st.form("prescribe_form"):
            st.markdown("#### New Prescription")
            c1, c2 = st.columns(2)
            pid_rx   = c1.text_input("Patient ID *", placeholder="pat_0001")
            pname_rx = c2.text_input("Patient Name *")
            drug_options = [d[0] for d in _DRUGS]
            drug = st.selectbox("Drug", drug_options)
            selected_drug = next((d for d in _DRUGS if d[0] == drug), _DRUGS[0])
            c3, c4, c5 = st.columns(3)
            dosage   = c3.text_input("Dosage",    value=selected_drug[1])
            freq     = c4.selectbox("Frequency",  ["OD","BD","TDS","QDS","Q6H","Q8H","PRN","SOS"])
            duration = c5.number_input("Duration (days)", 1, 90, int(selected_drug[3]))
            doctor_rx = st.text_input("Prescribed By *", placeholder="Dr. Kumar")
            if st.form_submit_button("Save Prescription", type="primary"):
                if pid_rx.strip() and pname_rx.strip() and doctor_rx.strip():
                    oid = add_pharmacy_order(DB_PATH, pid_rx, pname_rx, drug, dosage, freq, int(duration), doctor_rx)
                    st.success(f"Prescription saved: {oid}")
                    st.rerun()
                else:
                    st.error("Patient ID, Name, and Doctor required.")


# ── Page 9: Billing & Finance ─────────────────────────────────────────────────

def page_billing() -> None:
    st.markdown(styles.page_header("💰 Billing & Finance", "Patient billing, payments, and revenue analytics"), unsafe_allow_html=True)

    bill_df = get_billing(DB_PATH)
    rev_df  = get_revenue_summary(DB_PATH)

    if not bill_df.empty:
        total_rev = bill_df["amount_inr"].sum()
        collected = bill_df[bill_df["payment_status"]=="paid"]["amount_inr"].sum()
        pending   = bill_df[bill_df["payment_status"]=="pending"]["amount_inr"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Billed",  _fmt_inr(total_rev))
        c2.metric("Collected",     _fmt_inr(collected))
        c3.metric("Outstanding",   _fmt_inr(pending))
        c4.metric("Total Bills",   len(bill_df))
        st.markdown("<br>", unsafe_allow_html=True)

    tabs = st.tabs(["Revenue Analysis", "Patient Bills", "Generate Bill", "Payment Update"])

    with tabs[0]:
        if not rev_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(rev_df, x="category", y="revenue_inr",
                             title="Revenue by Category",
                             color_discrete_sequence=["#16a34a"], template="plotly_white")
                fig.update_layout(height=320, margin=dict(t=40,b=20))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.pie(rev_df, names="category", values="revenue_inr",
                              title="Revenue Share", template="plotly_white",
                              color_discrete_sequence=["#15803d","#16a34a","#22c55e","#1d4ed8","#2563eb","#3b82f6","#b91c1c"])
                fig2.update_layout(height=320, margin=dict(t=40,b=10))
                st.plotly_chart(fig2, use_container_width=True)
            if not bill_df.empty:
                status_counts = bill_df["payment_status"].value_counts().reset_index()
                status_counts.columns = ["status","count"]
                fig3 = px.bar(status_counts, x="status", y="count",
                              title="Bills by Payment Status",
                              color="status",
                              color_discrete_map={"paid":"#15803d","pending":"#b91c1c","partial":"#1d4ed8"},
                              template="plotly_white")
                fig3.update_layout(height=260, margin=dict(t=40,b=20))
                st.plotly_chart(fig3, use_container_width=True)

    with tabs[1]:
        c1, _ = st.columns([3,1])
        pid_bill = c1.text_input("Search by Patient ID", placeholder="pat_0001")
        searched = get_billing(DB_PATH, pid_bill) if pid_bill else bill_df
        if not searched.empty:
            disp = searched[["bill_id","patient_id","category","amount_inr","payment_status","created_at"]].copy()
            disp["amount_inr"] = disp["amount_inr"].apply(_fmt_inr)
            disp["created_at"] = _to_dt(disp["created_at"]).dt.strftime("%d %b %Y")
            st.dataframe(disp, use_container_width=True, hide_index=True, height=400)

    with tabs[2]:
        with st.form("gen_bill_form"):
            st.markdown("#### Generate New Bill")
            b1, b2 = st.columns(2)
            pid_new = b1.text_input("Patient ID *", placeholder="pat_0001")
            cat     = b2.selectbox("Category", ["consultation","lab_test","radiology_scan","pharmacy","bed_admission","procedure","emergency"])
            b3, b4 = st.columns(2)
            amount  = b3.number_input("Amount (INR) *", min_value=0.0, value=500.0, step=100.0)
            pay_st  = b4.selectbox("Payment Status", ["pending","paid","partial"])
            desc    = st.text_input("Description / Notes")
            if st.form_submit_button("Generate Bill", type="primary"):
                if pid_new.strip():
                    import uuid
                    bid = f"bill_m_{uuid.uuid4().hex[:6]}"
                    add_billing_entry(DB_PATH, bid, pid_new, cat, float(amount), pay_st,
                                      datetime.now(timezone.utc).isoformat(), "manual", desc)
                    st.success(f"Bill created: {bid}")
                    st.rerun()
                else:
                    st.error("Patient ID required.")

    with tabs[3]:
        if not bill_df.empty:
            with st.form("pay_update_form"):
                c1, c2, c3 = st.columns(3)
                bid_upd = c1.selectbox("Bill ID", bill_df["bill_id"].tolist())
                pay_new = c2.selectbox("New Status", ["paid","pending","partial","waived"])
                c3.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("Update Payment", type="primary"):
                    update_payment_status(DB_PATH, bid_upd, pay_new)
                    st.success(f"Updated: {bid_upd}")
                    st.rerun()


# ── Page 10: Staff & HR ───────────────────────────────────────────────────────

def page_staff() -> None:
    st.markdown(styles.page_header("👷 Staff & HR", "Workforce directory, shift management, and staffing overview"), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    dept_filter = c1.selectbox("Department", ["all"] + _DEPTS)
    role_filter = c2.selectbox("Role",       ["all"] + _ROLES)
    emp_df = get_employees(DB_PATH, dept_filter, role_filter)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Staff", len(emp_df))
    m2.metric("Active",      len(emp_df[emp_df["status"]=="active"]) if not emp_df.empty else 0)
    m3.metric("Departments", emp_df["department"].nunique() if not emp_df.empty else 0)

    tabs = st.tabs(["Directory", "Shift Overview", "Add Employee"])

    with tabs[0]:
        if emp_df.empty:
            st.info("No staff records.")
        else:
            st.dataframe(
                emp_df[["employee_id","full_name","role","department","shift","status","email"]],
                use_container_width=True, hide_index=True, height=450,
            )

    with tabs[1]:
        if not emp_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                shift_counts = emp_df.groupby(["department","shift"]).size().reset_index(name="count")
                fig = px.bar(shift_counts, x="department", y="count", color="shift",
                             title="Staff by Department & Shift", barmode="group",
                             color_discrete_sequence=["#15803d","#1d4ed8","#b91c1c"],
                             template="plotly_white")
                fig.update_layout(height=320, margin=dict(t=40,b=20))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                role_counts = emp_df["role"].value_counts().reset_index()
                role_counts.columns = ["role","count"]
                fig2 = px.pie(role_counts, names="role", values="count",
                              title="Staff by Role", template="plotly_white",
                              color_discrete_sequence=["#15803d","#1d4ed8","#b91c1c","#16a34a","#2563eb","#ea580c","#0e7490"])
                fig2.update_layout(height=320, margin=dict(t=40,b=10))
                st.plotly_chart(fig2, use_container_width=True)

    with tabs[2]:
        with st.form("add_emp_form"):
            st.markdown("#### Add New Employee")
            e1, e2 = st.columns(2)
            emp_name  = e1.text_input("Full Name *")
            emp_role  = e2.selectbox("Role", _ROLES)
            e3, e4 = st.columns(2)
            emp_dept  = e3.selectbox("Department", _DEPTS)
            emp_shift = e4.selectbox("Shift", _SHIFTS)
            e5, e6 = st.columns(2)
            emp_email = e5.text_input("Email")
            emp_phone = e6.text_input("Phone")
            if st.form_submit_button("Add Employee", type="primary"):
                if emp_name.strip():
                    eid = add_employee(DB_PATH, emp_name, emp_role, emp_dept, emp_shift, emp_email, emp_phone)
                    st.success(f"Employee added: {eid}")
                    st.rerun()
                else:
                    st.error("Name required.")


# ── AI-IDS: helpers ──────────────────────────────────────────────────────────

def _save_to_history(results: dict) -> None:
    """Append a completed attack session to the persistent history JSON."""
    if not results or not results.get("log"):
        return
    try:
        history: list = []
        if IDS_HISTORY_JSON.exists():
            history = json.loads(IDS_HISTORY_JSON.read_text(encoding="utf-8"))
        history.append({
            "session_num":      len(history) + 1,
            "attack_label":     results.get("attack_label", "UNKNOWN"),
            "anomaly_count":    results.get("anomaly_count", 0),
            "detected_at":      results.get("timestamp", ""),
            "blockchain_blocks":results.get("blockchain_blocks", 0),
            "log":              results.get("log", []),
        })
        IDS_HISTORY_JSON.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception:
        pass


def _excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


# ── AI-IDS: blinking siren banner (CSS animation) ────────────────────────────

_SIREN_CSS = """
<style>
@keyframes siren-pulse {
    0%   { background:rgba(220,38,38,0.10); border-color:#dc2626; box-shadow:0 0 0 0 rgba(220,38,38,0.3); }
    50%  { background:rgba(220,38,38,0.28); border-color:#fca5a5; box-shadow:0 0 20px 6px rgba(220,38,38,0.3); }
    100% { background:rgba(220,38,38,0.10); border-color:#dc2626; box-shadow:0 0 0 0 rgba(220,38,38,0.3); }
}
.siren-banner {
    animation: siren-pulse 0.85s ease-in-out infinite;
    border: 2px solid #dc2626; border-radius: 10px;
    padding: 13px 20px; margin: 0 0 16px 0;
    display: flex; align-items: center; gap: 18px;
}
.siren-icon { font-size: 1.6rem; flex-shrink: 0; }
.siren-main { font-size: 1rem; font-weight: 800; color: #fca5a5; letter-spacing: 0.03em; }
.siren-sub  { font-size: 0.78rem; color: #fda4a4; margin-top: 4px; opacity: 0.9; }
</style>
"""


def _render_siren_banner() -> None:
    """Render blinking siren banner on every page when IDS detects active threats."""
    results = st.session_state.get("_ids_results", {})
    if not results:
        return
    active        = results.get("active_attacks", [])
    anomaly_count = results.get("anomaly_count", 0)
    if not active or anomaly_count == 0:
        return
    attack_label = results.get("attack_label", "UNKNOWN")
    ts           = results.get("timestamp", "")
    blocks       = results.get("blockchain_blocks", 0)
    st.markdown(_SIREN_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="siren-banner">'
        f'  <span class="siren-icon">!</span>'
        f'  <div>'
        f'    <div class="siren-main">AI-IDS INTRUSION ALERT -- ATTACK DETECTED</div>'
        f'    <div class="siren-sub">'
        f'      Attack: <b>{attack_label}</b>'
        f'      &nbsp;|&nbsp; {anomaly_count} device(s) flagged'
        f'      &nbsp;|&nbsp; Detected: {ts}'
        f'      &nbsp;|&nbsp; Blockchain blocks: {blocks}'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── AI-IDS: popup alert dialog ────────────────────────────────────────────────

@st.dialog("AI-IDS Alert -- Intrusion Detected", width="large")
def _ids_alert_dialog() -> None:
    results = st.session_state.get("_ids_results", {})
    log     = results.get("log", [])
    n_alert = results.get("anomaly_count", 0)
    attack  = results.get("attack_label", "")
    ts      = results.get("timestamp", "")
    blocks  = results.get("blockchain_blocks", 0)

    st.markdown(
        f'<div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 18px;'
        f'border-radius:0 8px 8px 0;margin-bottom:14px">'
        f'<b style="color:#b91c1c;font-size:1rem">{n_alert} device(s) flagged as ATTACK</b>'
        f'<span style="color:#7f1d1d;font-size:0.84rem;margin-left:14px">Type: {attack}</span>'
        f'<br><span style="color:#9f1239;font-size:0.82rem">'
        f'Detected: {ts} &nbsp;|&nbsp; Blockchain blocks written: {blocks}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if log:
        df   = pd.DataFrame(log)
        cols = ["timestamp", "device_id", "attack_type", "packet_rate", "latency_ms",
                "anomaly_score", "final_score", "threshold", "prediction",
                "trust_before", "trust_after", "response", "block_hash"]
        st.dataframe(
            df[[c for c in cols if c in df.columns]],
            use_container_width=True, hide_index=True,
        )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Dismiss", type="primary", use_container_width=True):
            st.session_state.pop("_ids_alert_pending", None)
            st.rerun()
    with c2:
        if st.button("Go to Attack Impact →", use_container_width=True):
            st.session_state.pop("_ids_alert_pending", None)
            st.session_state["nav"] = "Attack Impact"
            st.rerun()


# ── AI-IDS: file watcher — reads results written by MedGuard-IDS dashboard ───

@st.fragment(run_every=3)
def _ids_file_watcher() -> None:
    """
    Reads ids_detection_results.json (written by MedGuard-IDS model dashboard
    when connected). Triggers popup alert and siren banner when new attack detected.
    No model inference runs here — the model dashboard owns all inference.
    """
    if not IDS_RESULTS_JSON.exists():
        # Model disconnected — clear any existing alert state and rerun once
        if st.session_state.get("_ids_results"):
            st.session_state.pop("_ids_results", None)
            st.session_state.pop("_ids_prev_attack", None)
            st.session_state.pop("_ids_prev_anomaly", None)
            st.session_state.pop("_ids_alert_pending", None)
            st.rerun()
        return

    try:
        results = json.loads(IDS_RESULTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return

    anomaly_count  = results.get("anomaly_count", 0)
    active_attacks = results.get("active_attacks", [])
    attack_label   = results.get("attack_label", "None")

    st.session_state["_ids_results"] = results

    prev_attack  = st.session_state.get("_ids_prev_attack",  "__init__")
    prev_anomaly = st.session_state.get("_ids_prev_anomaly", -1)

    state_changed = (attack_label != prev_attack) or (anomaly_count != prev_anomaly)
    if not state_changed:
        return

    st.session_state["_ids_prev_attack"]  = attack_label
    st.session_state["_ids_prev_anomaly"] = anomaly_count

    was_attack = prev_anomaly > 0
    is_attack  = anomaly_count > 0 and bool(active_attacks)

    if was_attack and not is_attack:
        # Attack just ended — save session to history
        _save_to_history(st.session_state.get("_ids_results", {}))

    st.rerun()


# ── Attack-awareness: watch DB mtime and auto-rerun when Attack Lab writes ────

@st.fragment(run_every=2)
def _db_change_watcher() -> None:
    """
    Polls hospital.db modification time every 2 seconds.
    When the Attack Lab writes to the DB (tamper, spoof, replay, restore),
    the mtime changes and this fragment triggers a full page rerun so all
    MediCore tables refresh and show the attack / recovery instantly.
    A minimum 4-second gap between reruns prevents form-input disruption.
    """
    db = Path(DB_PATH)
    if not db.exists():
        return
    mtime = db.stat().st_mtime
    prev_mtime  = st.session_state.get("_db_mtime_watch", 0)
    last_rerun  = st.session_state.get("_db_last_rerun",  0)
    if mtime != prev_mtime:
        st.session_state["_db_mtime_watch"] = mtime
        if (_time.time() - last_rerun) > 4:
            st.session_state["_db_last_rerun"] = _time.time()
            st.rerun()


# ── IoMT live fragments (module-level so they persist across page rerenders) ──

@st.fragment(run_every=1)
def _iomt_vitals_fragment() -> None:
    """Generates one new reading per second and refreshes device cards + table."""
    is_live = st.session_state.get("iomt_live", False)
    if is_live:
        prev = st.session_state.get("device_states", {})
        _, new_states = generate_virtual_iomt_vitals(DB_PATH, samples_per_device=1, prev_states=prev)
        if new_states:
            st.session_state["device_states"] = new_states

    states = st.session_state.get("device_states", {})
    if not states:
        st.info("Press ▶ Start Stream to begin live IoMT monitoring.")
        return

    # ── Primary-metric helper per device type ───────────────────────────────
    import math as _math
    _NAN = float("nan")

    def _primary(s: dict) -> str:
        """Return the most important reading for this device type as a display string."""
        dt = s.get("device_type", "")
        def _v(k): return s.get(k)
        def _f(v, fmt): return fmt % v if v is not None and not (isinstance(v, float) and _math.isnan(v)) else None

        if dt == "cgm_sensor":
            g = _f(_v("glucose_mg_dl"), "%.0f mg/dL")
            return f"GLU {g}" if g else "GLU —"
        if dt in ("ecg_monitor", "defibrillator"):
            h = _f(_v("heart_rate"), "%.0f bpm")
            return f"HR {h}" if h else "HR —"
        if dt == "pulse_oximeter":
            sp = _f(_v("spo2"), "%.1f%%")
            return f"SpO₂ {sp}" if sp else "SpO₂ —"
        if dt == "nibp_monitor":
            sb = _f(_v("systolic_bp"), "%.0f")
            db = _f(_v("diastolic_bp"), "%.0f")
            return f"BP {sb}/{db} mmHg" if sb else "BP —"
        if dt == "temperature_probe":
            t = _f(_v("temperature_c"), "%.1f°C")
            return f"T {t}" if t else "T —"
        if dt == "capnograph":
            r = _f(_v("respiration_rate"), "%.0f")
            return f"ETCO₂ {r} mmHg" if r else "ETCO₂ —"
        if dt == "fetal_monitor":
            fh = _f(_v("heart_rate"), "%.0f bpm")
            return f"FHR {fh}" if fh else "FHR —"
        if dt in ("dialysis_machine", "bipap_machine"):
            sp = _f(_v("spo2"), "%.1f%%")
            rr = _f(_v("respiration_rate"), "%.0f")
            return f"SpO₂ {sp} · RR {rr}" if sp or rr else "—"
        # Default: HR + SpO2
        h  = _f(_v("heart_rate"), "%.0f bpm")
        sp = _f(_v("spo2"), "%.1f%%")
        return f"HR {h}  SpO₂ {sp}" if h else "—"

    def _secondary(s: dict) -> str:
        dt = s.get("device_type", "")
        def _v(k): return s.get(k)
        def _f(v, fmt): return fmt % v if v is not None and not (isinstance(v, float) and _math.isnan(v)) else None
        if dt == "cgm_sensor":
            return f"Trend: {'HIGH' if (s.get('glucose_mg_dl') or 0) > 180 else 'Normal'}"
        if dt in ("ecg_monitor", "defibrillator"):
            return s.get("ecg_rhythm", "—")
        if dt == "fetal_monitor":
            return "Rhythm: FHR"
        sb = _f(_v("systolic_bp"), "%.0f")
        t  = _f(_v("temperature_c"), "%.1f°C")
        r  = _f(_v("respiration_rate"), "%.0f")
        parts = [f"BP {sb}" if sb else None, f"Temp {t}" if t else None, f"RR {r}" if r else None]
        return "  ·  ".join(p for p in parts if p) or s.get("ecg_rhythm", "—")

    # ── One card per device TYPE — 5 per row ────────────────────────────────
    type_rep: dict = {}
    for dev_id, s in sorted(states.items()):
        dt = s["device_type"]
        if dt != "imaging_gateway" and dt not in type_rep:
            type_rep[dt] = (dev_id, s)

    COLS_PER_ROW = 5
    items = list(type_rep.items())
    for row_start in range(0, len(items), COLS_PER_ROW):
        row_items = items[row_start:row_start + COLS_PER_ROW]
        row_cols  = st.columns(COLS_PER_ROW)
        for col, (dt, (dev_id, s)) in zip(row_cols, row_items):
            risk  = bool(s.get("risk_flag", 0))
            bg    = "#fef2f2" if risk else "#f0fdf4"
            bdr   = "#dc2626" if risk else "#16a34a"
            label = dt.replace("_", " ").upper()
            pri   = _primary(s)
            sec   = _secondary(s)
            alert = '<div style="color:#dc2626;font-weight:700;font-size:0.78rem;margin-top:3px">RISK</div>' if risk else ""
            col.markdown(
                f'<div style="background:{bg};border:2px solid {bdr};border-radius:10px;'
                f'padding:9px 6px;text-align:center;min-height:90px">'
                f'<div style="font-size:0.72rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.04em;margin-bottom:2px">{label}</div>'
                f'<div style="font-size:0.72rem;color:#64748b;margin-bottom:3px">{s["department"]}</div>'
                f'<div style="font-size:0.95rem;font-weight:800;color:#0f172a;line-height:1.3">{pri}</div>'
                f'<div style="font-size:0.78rem;color:#334155;margin-top:2px">{sec}</div>'
                f'{alert}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Summary metrics + readings table
    risk_total = sum(1 for s in states.values() if s.get("risk_flag"))
    r1, r2 = st.columns(2)
    r1.metric("Active Devices",  sum(1 for s in states.values() if s["device_type"] != "imaging_gateway"))
    r2.metric("Risk-Flagged", risk_total, delta=f"{risk_total}" if risk_total else None, delta_color="inverse")

    tbl_rows = []
    for dev_id, s in sorted(states.items()):
        if s["device_type"] == "imaging_gateway":
            continue
        hr_v   = s.get("heart_rate")
        spo2_v = s.get("spo2")
        sbp_v  = s.get("systolic_bp")
        dbp_v  = s.get("diastolic_bp")
        rr_v   = s.get("respiration_rate")
        t_v    = s.get("temperature_c")
        import math as _m
        def _fmt(v, fmt):
            return fmt % v if v is not None and not (isinstance(v, float) and _m.isnan(v)) else "—"
        glu_v  = s.get("glucose_mg_dl")
        tbl_rows.append({
            "Device ID":    dev_id,
            "Type":         s["device_type"],
            "Dept":         s["department"],
            "Patient":      s.get("patient_id") or "—",
            "HR (bpm)":     _fmt(hr_v,   "%.1f"),
            "SpO₂ (%)":    _fmt(spo2_v,  "%.1f"),
            "BP (mmHg)":   f"{sbp_v:.0f}/{dbp_v:.0f}" if sbp_v is not None and not _m.isnan(sbp_v) else "—",
            "Temp (°C)":   _fmt(t_v,    "%.1f"),
            "RR":           _fmt(rr_v,   "%.0f"),
            "Glucose":      _fmt(glu_v,  "%.0f"),
            "ECG":          s.get("ecg_rhythm", "—"),
            "Status":       "RISK" if s.get("risk_flag") else "Normal",
        })
    if tbl_rows:
        st.dataframe(pd.DataFrame(tbl_rows), use_container_width=True, hide_index=True, height=340)


@st.fragment(run_every=5)
def _iomt_charts_fragment() -> None:
    """Refreshes trend charts every 5 seconds — decoupled from the 1s card loop."""
    limit   = st.session_state.get("lv_limit", 200)
    live_df = get_iot_live_vitals(DB_PATH, limit=limit)
    if live_df.empty:
        st.caption("No trend data yet — start the stream to accumulate readings.")
        return

    for col_name in ["heart_rate", "spo2", "systolic_bp", "diastolic_bp", "temperature_c"]:
        live_df[col_name] = pd.to_numeric(live_df[col_name], errors="coerce")
    live_df["ts"] = pd.to_datetime(live_df["timestamp"], errors="coerce")
    chart_df = live_df[live_df["device_type"] != "imaging_gateway"].sort_values("ts")

    st.metric("Readings in DB", len(live_df))

    cc1, cc2 = st.columns(2)
    with cc1:
        hr_df = chart_df.dropna(subset=["heart_rate"])
        if not hr_df.empty:
            fig = px.line(hr_df, x="ts", y="heart_rate", color="device_type",
                          title="Heart Rate (bpm)", template="plotly_white",
                          color_discrete_sequence=["#dc2626","#ea580c","#1d4ed8","#0891b2","#16a34a"])
            fig.update_layout(height=230, margin=dict(t=36,b=8,l=8,r=8),
                              xaxis_title="", yaxis_title="bpm",
                              legend=dict(font_size=10, orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True)
    with cc2:
        spo2_df = chart_df.dropna(subset=["spo2"])
        if not spo2_df.empty:
            fig2 = px.line(spo2_df, x="ts", y="spo2", color="device_type",
                           title="SpO2 (%)", template="plotly_white",
                           color_discrete_sequence=["#0891b2","#1d4ed8","#16a34a","#dc2626","#ea580c"])
            fig2.add_hline(y=92, line_dash="dash", line_color="#dc2626",
                           annotation_text="SpO₂ < 92%", annotation_font_size=9)
            fig2.update_layout(height=230, margin=dict(t=36,b=8,l=8,r=8),
                               xaxis_title="", yaxis_title="%",
                               legend=dict(font_size=10, orientation="h", y=1.12))
            st.plotly_chart(fig2, use_container_width=True)

    cc3, cc4 = st.columns(2)
    with cc3:
        bp_df = chart_df.dropna(subset=["systolic_bp"])
        if not bp_df.empty:
            fig3 = go.Figure()
            palette = ["#1d4ed8","#0891b2","#16a34a","#d97706","#dc2626"]
            for i, dtype in enumerate(bp_df["device_type"].unique()):
                sub = bp_df[bp_df["device_type"] == dtype]
                c = palette[i % len(palette)]
                fig3.add_scatter(x=sub["ts"], y=sub["systolic_bp"],
                                 mode="lines", name=f"{dtype} SBP", line=dict(color=c))
                fig3.add_scatter(x=sub["ts"], y=sub["diastolic_bp"],
                                 mode="lines", name=f"{dtype} DBP",
                                 line=dict(color=c, dash="dot"), opacity=0.55, showlegend=False)
            fig3.add_hline(y=140, line_dash="dash", line_color="#ea580c",
                           annotation_text="Hypertension", annotation_font_size=9)
            fig3.update_layout(title="Blood Pressure (mmHg)", template="plotly_white",
                               height=230, margin=dict(t=36,b=8,l=8,r=8),
                               xaxis_title="", yaxis_title="mmHg",
                               legend=dict(font_size=9, orientation="h", y=1.12))
            st.plotly_chart(fig3, use_container_width=True)
    with cc4:
        temp_df = chart_df.dropna(subset=["temperature_c"])
        if not temp_df.empty:
            fig4 = px.line(temp_df, x="ts", y="temperature_c", color="device_type",
                           title="Temperature (°C)", template="plotly_white",
                           color_discrete_sequence=["#d97706","#ea580c","#0891b2","#16a34a","#6366f1"])
            fig4.add_hline(y=38.5, line_dash="dash", line_color="#dc2626",
                           annotation_text="Fever", annotation_font_size=9)
            fig4.update_layout(height=230, margin=dict(t=36,b=8,l=8,r=8),
                               xaxis_title="", yaxis_title="°C",
                               legend=dict(font_size=10, orientation="h", y=1.12))
            st.plotly_chart(fig4, use_container_width=True)


# ── Page 11: IoMT Devices ─────────────────────────────────────────────────────

def page_devices() -> None:
    st.markdown(styles.page_header("IoMT Device Monitor", "Connected device fleet status, telemetry, and security signals"), unsafe_allow_html=True)

    devices_df = get_devices(DB_PATH)
    if not devices_df.empty:
        total   = len(devices_df)
        online  = len(devices_df[devices_df["status"]=="online"])
        offline = len(devices_df[devices_df["status"]=="offline"])
        maint   = len(devices_df[devices_df["status"]=="maintenance"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Devices", total)
        c2.metric("Online",        online,  delta=f"{online/total:.0%}")
        c3.metric("Offline",       offline, delta=f"-{offline}" if offline > 0 else "0", delta_color="inverse")
        c4.metric("Maintenance",   maint)

    tabs = st.tabs(["Device Fleet", "Telemetry", "Live Vitals", "Security Signals"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        dept_f = c1.selectbox("Filter by Department", ["all"] + _DEPTS)
        stat_f = c2.selectbox("Filter by Status",     ["all","online","offline","maintenance"])
        filtered = get_devices(DB_PATH, dept_f, stat_f)
        if not filtered.empty:
            disp = filtered.copy()
            disp["last_seen"] = _to_dt(disp["last_seen"]).dt.strftime("%d %b %H:%M")
            st.dataframe(
                disp[["device_id","device_type","department","criticality","ip_address","firmware_version","status","last_seen"]],
                use_container_width=True, hide_index=True, height=400,
            )

    with tabs[1]:
        events_df = _load_events()
        if events_df.empty:
            st.info("No telemetry data. Run workflow simulation first.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                dept_sel = st.selectbox("Department", ["All"] + _DEPTS, key="tel_dept")
                tel_df = events_df if dept_sel == "All" else events_df[events_df["department"]==dept_sel]
                fig = px.histogram(tel_df, x="latency_ms", nbins=40,
                                   title="Latency Distribution (ms)",
                                   color_discrete_sequence=["#15803d"], template="plotly_white")
                fig.update_layout(height=280, margin=dict(t=40,b=20))
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig2 = px.histogram(tel_df, x="cpu_pct", nbins=30,
                                    title="CPU Usage Distribution (%)",
                                    color_discrete_sequence=["#0891b2"], template="plotly_white")
                fig2.update_layout(height=280, margin=dict(t=40,b=20))
                st.plotly_chart(fig2, use_container_width=True)

            fleet = events_df.groupby("device_type").agg(
                events=("event_id","count"),
                avg_latency=("latency_ms","mean"),
                avg_cpu=("cpu_pct","mean"),
                sec_flags=("security_flag","sum"),
            ).reset_index()
            st.dataframe(fleet.round(2), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown("#### Virtual IoMT Live Medical Telemetry")

        # ── Stream controls ──────────────────────────────────────────────────
        ctrl1, ctrl2 = st.columns([1, 3])
        with ctrl1:
            btn_label = "⏹ Stop Stream" if st.session_state.get("iomt_live", False) else "▶ Start Stream"
            if st.button(btn_label, type="primary", use_container_width=True, key="iomt_toggle"):
                st.session_state["iomt_live"] = not st.session_state.get("iomt_live", False)
                st.rerun()
        with ctrl2:
            if st.session_state.get("iomt_live", False):
                st.markdown(
                    '<span style="color:#16a34a;font-weight:700;font-size:0.95rem;">'
                    'LIVE &nbsp;— values updating every second across all virtual devices</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="color:#475569;font-size:0.9rem;">'
                    '⏸ Stream paused — press ▶ Start Stream to begin live IoMT monitoring</span>',
                    unsafe_allow_html=True,
                )

        recent_limit = st.slider(
            "Recent readings shown in charts / table", 50, 500, 200, 50, key="lv_limit"
        )

        # ── Cards: fast 1-second fragment (module-level) ────────────────────
        _iomt_vitals_fragment()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Trend Charts — updated every 5 seconds")

        # ── Charts: slower 5-second fragment (module-level) ─────────────────
        _iomt_charts_fragment()

    with tabs[3]:
        events_df = _load_events()
        if not events_df.empty:
            flagged   = events_df[events_df["security_flag"]==1]
            high_risk = events_df[events_df["command_risk"]>0.7]
            auth_fail = events_df[events_df["auth_fail_count"]>=2]
            c1, c2, c3 = st.columns(3)
            c1.metric("Flagged Events",    len(flagged))
            c2.metric("High Command Risk", len(high_risk))
            c3.metric("Auth Fail Spikes",  len(auth_fail))

            c4, c5 = st.columns(2)
            with c4:
                risk_by_dept = events_df.groupby("department")["command_risk"].mean().reset_index()
                fig = px.bar(risk_by_dept, x="department", y="command_risk",
                             title="Avg Command Risk by Department",
                             color_discrete_sequence=["#dc2626"], template="plotly_white")
                fig.update_layout(height=280, margin=dict(t=40,b=20))
                st.plotly_chart(fig, use_container_width=True)
            with c5:
                flag_by_dev = events_df.groupby("device_type")["security_flag"].sum().reset_index()
                fig2 = px.bar(flag_by_dev, x="device_type", y="security_flag",
                              title="Security Flags by Device Type",
                              color_discrete_sequence=["#ea580c"], template="plotly_white")
                fig2.update_layout(height=280, margin=dict(t=40,b=20))
                st.plotly_chart(fig2, use_container_width=True)


# ── Page 12: Reports ──────────────────────────────────────────────────────────

def page_reports() -> None:
    st.markdown(styles.page_header("📋 Reports & Analytics", "Comprehensive operational, clinical, and financial reports"), unsafe_allow_html=True)

    census    = get_census(DB_PATH)
    bill_df   = get_billing(DB_PATH)
    rev_df    = get_revenue_summary(DB_PATH)
    lab_df    = get_lab_orders(DB_PATH)
    rad_df    = get_radiology_orders(DB_PATH)
    rx_df     = get_pharmacy_orders(DB_PATH)
    patients  = get_patients(DB_PATH)
    events_df = _load_events()

    tabs = st.tabs(["Clinical Summary", "Operational Metrics", "Financial Report", "Export"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            if not patients.empty:
                sc = patients["status"].value_counts().reset_index()
                sc.columns = ["status","count"]
                fig = px.pie(sc, names="status", values="count",
                             title="Patient Status Distribution",
                             template="plotly_white",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if not patients.empty:
                tc = patients["triage_level"].value_counts().reset_index()
                tc.columns = ["level","count"]
                fig2 = px.bar(tc, x="level", y="count", color="level",
                              color_discrete_map=TRIAGE_COLORS,
                              title="Patients by Triage Level", template="plotly_white")
                st.plotly_chart(fig2, use_container_width=True)

        c3, c4, c5 = st.columns(3)
        c3.metric("Patients Registered",      census["total_patients"])
        c4.metric("Lab Orders (All Time)",     len(lab_df))
        c5.metric("Radiology Orders",          len(rad_df))
        c6, c7, c8 = st.columns(3)
        c6.metric("Pharmacy Orders",           len(rx_df))
        c7.metric("Available Beds",            census["available_beds"])
        c8.metric("Staff Count",               len(get_employees(DB_PATH)))

    with tabs[1]:
        if not events_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                dept_e = events_df["department"].value_counts().reset_index()
                dept_e.columns = ["department","events"]
                fig = px.bar(dept_e, x="department", y="events",
                             title="Events by Department",
                             color_discrete_sequence=["#15803d"], template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                sub_perf = events_df.groupby("subsystem").agg(
                    avg_wait=("wait_min","mean"),
                    sla_breach_rate=("sla_breached","mean"),
                ).reset_index().sort_values("sla_breach_rate", ascending=False)
                fig2 = px.bar(sub_perf, x="subsystem", y="sla_breach_rate",
                              title="SLA Breach Rate by Subsystem",
                              color_discrete_sequence=["#dc2626"], template="plotly_white")
                fig2.update_layout(xaxis_tickangle=30)
                st.plotly_chart(fig2, use_container_width=True)
            c1.metric("Overall SLA Breach Rate", f"{events_df['sla_breached'].mean():.2%}")
            c2.metric("Avg Latency (ms)",        f"{events_df['latency_ms'].mean():.1f}")

    with tabs[2]:
        if not bill_df.empty:
            total = bill_df["amount_inr"].sum()
            paid  = bill_df[bill_df["payment_status"]=="paid"]["amount_inr"].sum()
            pend  = bill_df[bill_df["payment_status"]=="pending"]["amount_inr"].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Revenue (INR)",    _fmt_inr(total))
            c2.metric("Collected",              _fmt_inr(paid))
            c3.metric("Pending Collection",     _fmt_inr(pend))
            if not rev_df.empty:
                st.dataframe(rev_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("#### Download Reports")
        c1, c2 = st.columns(2)
        if not patients.empty:
            c1.download_button("⬇ Patient Registry (CSV)", patients.to_csv(index=False).encode(), "patients_report.csv", "text/csv")
        if not bill_df.empty:
            c2.download_button("⬇ Billing Report (CSV)",   bill_df.to_csv(index=False).encode(), "billing_report.csv",  "text/csv")
        if not lab_df.empty:
            c1.download_button("⬇ Lab Orders (CSV)",       lab_df.to_csv(index=False).encode(),  "lab_orders.csv",      "text/csv")
        if not rx_df.empty:
            c2.download_button("⬇ Pharmacy Orders (CSV)",  rx_df.to_csv(index=False).encode(),   "pharmacy_orders.csv", "text/csv")
        if not events_df.empty:
            c1.download_button("⬇ Workflow Events (CSV)",  events_df.to_csv(index=False).encode(),"workflow_events.csv","text/csv")

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "census": census,
            "billing": {
                "total_bills":   int(len(bill_df)),
                "revenue_inr":   float(bill_df["amount_inr"].sum()) if not bill_df.empty else 0,
                "collected_inr": float(bill_df[bill_df["payment_status"]=="paid"]["amount_inr"].sum()) if not bill_df.empty else 0,
            },
            "clinical": {
                "lab_orders":       int(len(lab_df)),
                "radiology_orders": int(len(rad_df)),
                "pharmacy_orders":  int(len(rx_df)),
            },
        }
        c2.download_button("⬇ Summary Report (JSON)", json.dumps(summary, indent=2).encode(), "summary_report.json", "application/json")


# —— Page 13: Attack Impact ——––––––––––––––––––––––––––––––––––––––––––––––––––––––––

_ATTACK_COLORS = {
    "dos": "#dc2626", "spoof": "#f59e0b",
    "tamper": "#a78bfa", "replay": "#06b6d4", "ransomware": "#7f1d1d",
}
_ATTACK_LABELS = {
    "dos": "DoS Flood", "spoof": "Device Spoofing",
    "tamper": "Data Tampering", "replay": "Replay Attack",
    "ransomware": "Ransomware", "cpu": "CPU Stress",
}
_ATTACK_EXPLAIN = {
    "dos": {
        "what": "Denial of Service (DoS) Attack",
        "desc": "Attackers flooded hospital IoMT devices with excessive network traffic, "
                "making them unresponsive. Medical devices could not send or receive data.",
        "risk": "Patient monitoring devices stop reporting vitals. Clinical staff lose "
                "real-time visibility into patient conditions, potentially delaying critical care.",
    },
    "spoof": {
        "what": "Device Spoofing Attack",
        "desc": "Fake devices were injected into the hospital network pretending to be "
                "legitimate medical equipment, sending false data to the system.",
        "risk": "Clinicians may receive fabricated patient readings (e.g., false heart rate "
                "or blood pressure), leading to incorrect treatment decisions.",
    },
    "tamper": {
        "what": "Data Tampering Attack",
        "desc": "Attackers modified the data being sent by medical devices, altering "
                "readings such as vitals, dosage levels, or diagnostic results.",
        "risk": "Tampered readings could cause wrong medication dosages or missed diagnoses. "
                "Patient safety is directly compromised.",
    },
    "replay": {
        "what": "Replay Attack",
        "desc": "Previously captured legitimate device communications were re-sent to the "
                "hospital network, making the system process outdated information as current.",
        "risk": "Old patient data replayed as current could mask deteriorating conditions "
                "or trigger unnecessary medical interventions.",
    },
    "ransomware": {
        "what": "Ransomware Attack",
        "desc": "Malicious software encrypted medical device firmware and data, locking "
                "hospital staff out of critical IoMT equipment.",
        "risk": "Life-support and monitoring devices become completely unusable. Hospital "
                "operations may halt until devices are restored or replaced.",
    },
    "cpu": {
        "what": "CPU Stress Attack",
        "desc": "Attackers overloaded IoMT device processors with intensive computations, "
                "consuming all available CPU resources and degrading device performance.",
        "risk": "Medical devices become sluggish or unresponsive. Real-time monitoring "
                "and alerting may be delayed, risking missed critical patient events.",
    },
}


def _generate_hospital_attack_pdf(live_data: dict, device_df: pd.DataFrame) -> bytes:
    """Generate a simple, non-technical PDF report for hospital staff.

    Focuses on: what attack happened, where it hit, and how it impacted operations.
    """
    from fpdf import FPDF

    log = live_data.get("log", [])
    n = live_data.get("anomaly_count", 0)
    label = live_data.get("attack_label", "None")
    ts = live_data.get("timestamp", "")
    active = live_data.get("active_attacks", [])

    # Merge device info (department, device_type) from hospital DB
    dev_map = {}
    if not device_df.empty:
        for _, row in device_df.iterrows():
            dev_map[row.get("device_id", "")] = {
                "department": row.get("department", "Unknown"),
                "device_type": row.get("device_type", "Unknown"),
            }

    flagged = [r for r in log if r.get("prediction") == 1]
    clear_count = len(log) - len(flagged)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    W = 190  # usable width (210 - 2*10 margins)
    LM = 10  # left margin

    # ── Header ───────────────────────────────────────────────────────────
    pdf.set_fill_color(15, 80, 45)
    pdf.rect(0, 0, 210, 42, "F")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(10)
    pdf.cell(0, 10, "Hospital Cyber Attack Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 230, 210)
    pdf.cell(0, 7, "MediCore IoMT Security Incident Summary", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, ts[:19].replace("T", " ") + " UTC" if ts else "", ln=True, align="C")
    pdf.ln(8)

    # ── Incident Overview Box ────────────────────────────────────────────
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(220, 38, 38)
    box_y = pdf.get_y()
    pdf.rect(LM, box_y, W, 32, "DF")
    pdf.set_xy(LM + 6, box_y + 4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(185, 28, 28)
    status_text = f"SECURITY INCIDENT: {label}" if n > 0 else "NO INCIDENTS DETECTED"
    pdf.cell(W - 12, 8, status_text, ln=True)
    pdf.set_x(LM + 6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    n_flagged = len(flagged)
    n_clear = len(log) - n_flagged
    pdf.cell(60, 7, f"Devices Affected:  {n_flagged}", ln=False)
    pdf.cell(60, 7, f"Devices Safe:  {n_clear}", ln=False)
    pdf.cell(0, 7, f"Total Scanned:  {len(log)}", ln=True)
    pdf.set_y(box_y + 36)

    # ── What Happened ────────────────────────────────────────────────────
    if active:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 10, "What Happened", ln=True)
        pdf.set_draw_color(15, 80, 45)
        pdf.line(LM, pdf.get_y(), LM + 50, pdf.get_y())
        pdf.ln(4)

        for atk_type in active:
            info = _ATTACK_EXPLAIN.get(atk_type, {})
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(185, 28, 28)
            pdf.cell(0, 7, info.get("what", atk_type.upper()), ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(W, 6, info.get("desc", ""))
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(185, 28, 28)
            pdf.cell(24, 6, "Risk:  ", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(W - 24, 6, info.get("risk", ""))
            pdf.ln(4)

    # ── Where It Impacted (departments & device types) ───────────────────
    if flagged:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 10, "Where It Impacted", ln=True)
        pdf.set_draw_color(15, 80, 45)
        pdf.line(LM, pdf.get_y(), LM + 50, pdf.get_y())
        pdf.ln(4)

        # Group by department
        dept_devices: dict[str, list] = {}
        for r in flagged:
            did = r.get("device_id", "?")
            dm = dev_map.get(did, {"department": "Unknown", "device_type": "Unknown"})
            dept = dm["department"]
            if dept not in dept_devices:
                dept_devices[dept] = []
            dept_devices[dept].append({"device_id": did, "device_type": dm["device_type"]})

        for dept, devs in sorted(dept_devices.items()):
            # Department header row
            pdf.set_fill_color(240, 245, 240)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(15, 80, 45)
            pdf.cell(W, 8, f"  {dept}  ({len(devs)} device{'s' if len(devs) != 1 else ''} affected)",
                     ln=True, fill=True)

            # Device rows
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            # Table header
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(60, 6, "  Device ID", border="B", fill=True)
            pdf.cell(60, 6, "  Device Type", border="B", fill=True)
            pdf.cell(W - 120, 6, "  Status", border="B", fill=True, ln=True)

            pdf.set_font("Helvetica", "", 9)
            for d in devs[:20]:
                pdf.set_text_color(60, 60, 60)
                pdf.cell(60, 5.5, f"  {d['device_id']}")
                pdf.cell(60, 5.5, f"  {d['device_type']}")
                pdf.set_text_color(185, 28, 28)
                pdf.cell(W - 120, 5.5, "  Compromised", ln=True)
            if len(devs) > 20:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(120, 120, 120)
                pdf.cell(0, 5, f"  ... and {len(devs) - 20} more devices", ln=True)
            pdf.ln(3)

    # ── Impact Summary ───────────────────────────────────────────────────
    if flagged:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 10, "Impact Summary", ln=True)
        pdf.set_draw_color(15, 80, 45)
        pdf.line(LM, pdf.get_y(), LM + 50, pdf.get_y())
        pdf.ln(4)

        total_depts = len(dept_devices) if flagged else 0
        dev_types_hit = set()
        for r in flagged:
            did = r.get("device_id", "?")
            dm = dev_map.get(did, {})
            dev_types_hit.add(dm.get("device_type", "Unknown"))

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)

        pdf.set_fill_color(255, 248, 240)
        pdf.set_draw_color(200, 160, 60)
        box_y2 = pdf.get_y()
        box_h = 40
        pdf.rect(LM, box_y2, W, box_h, "DF")

        pdf.set_xy(LM + 6, box_y2 + 4)
        pdf.cell(0, 6, f"Departments affected:   {total_depts}  ({', '.join(sorted(dept_devices.keys()))})", ln=True)
        pdf.set_x(LM + 6)
        pdf.cell(0, 6, f"Device types affected:  {len(dev_types_hit)}  ({', '.join(sorted(dev_types_hit))})", ln=True)
        pdf.set_x(LM + 6)
        pdf.cell(0, 6, f"Devices compromised:    {len(flagged)} out of {len(log)} total", ln=True)
        pdf.set_x(LM + 6)
        pct = len(flagged) / len(log) * 100 if log else 0
        pdf.cell(0, 6, f"Compromise rate:        {pct:.1f}%", ln=True)
        pdf.set_y(box_y2 + box_h + 6)

    # ── Recommended Actions ──────────────────────────────────────────────
    if n > 0:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 10, "Recommended Actions", ln=True)
        pdf.set_draw_color(15, 80, 45)
        pdf.line(LM, pdf.get_y(), LM + 50, pdf.get_y())
        pdf.ln(4)

        actions = [
            "Isolate all affected devices from the hospital network immediately.",
            "Notify the cybersecurity response team and clinical engineering.",
            "Verify patient safety for all departments with compromised devices.",
            "Switch to manual monitoring for affected patient areas.",
            "Restore devices from verified backups once the threat is contained.",
            "Document the incident for compliance and regulatory reporting.",
        ]
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        for i, a in enumerate(actions, 1):
            pdf.cell(W, 7, f"  {i}.  {a}", ln=True)
        pdf.ln(4)

    # ── Footer ───────────────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 5, "MediCore Hospital Management System  |  AI-IDS Cyber Attack Report", ln=True, align="C")
    pdf.cell(0, 5, "This report is auto-generated. For questions contact the IT Security team.", ln=True, align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def page_attack_impact() -> None:
    st.markdown(
        styles.page_header("AI-IDS Detection Log", "Attack detection records from MedGuard-IDS model"),
        unsafe_allow_html=True,
    )

    _IDS_COLS = ["timestamp", "device_id", "attack_type", "packet_rate", "latency_ms",
                 "anomaly_score", "final_score", "threshold", "prediction",
                 "trust_before", "trust_after", "response", "block_hash"]

    # Read current live data from shared JSON (written by MedGuard-IDS model)
    live_data = None
    if IDS_RESULTS_JSON.exists():
        try:
            live_data = json.loads(IDS_RESULTS_JSON.read_text(encoding="utf-8"))
        except Exception:
            live_data = None

    # Action buttons
    hdr_c1, hdr_c2, hdr_c3 = st.columns([4, 1.4, 1])
    with hdr_c2:
        if st.button("Reset Devices", use_container_width=True,
                     help="Restore all compromised/offline devices to Online status"):
            import sqlite3 as _sql
            try:
                with _sql.connect(DB_PATH) as _conn:
                    _conn.execute(
                        "UPDATE iot_devices SET status='online', firmware_version='v2.1.0'"
                        " WHERE status IN ('offline','compromised','error','corrupted')"
                    )
                    _conn.commit()
                st.success("All devices restored to Online.")
                st.rerun()
            except Exception as _e:
                st.error(f"Reset failed: {_e}")
    with hdr_c3:
        if live_data and st.button("Clear Log", use_container_width=True):
            try:
                IDS_RESULTS_JSON.unlink(missing_ok=True)
                st.rerun()
            except Exception:
                pass

    if live_data and live_data.get("log"):
        n      = live_data.get("anomaly_count", 0)
        label  = live_data.get("attack_label", "None")
        ts     = live_data.get("timestamp", "")
        blocks = live_data.get("blockchain_blocks", 0)

        if n > 0:
            st.markdown(
                f'<div style="background:#fef2f2;border-left:4px solid #dc2626;padding:10px 16px;'
                f'border-radius:0 8px 8px 0;margin-bottom:8px">'
                f'<b style="color:#b91c1c">INTRUSION DETECTED -- {n} device(s) flagged</b>'
                f'<span style="color:#7f1d1d;font-size:0.82rem;margin-left:12px">'
                f'{label} &nbsp;·&nbsp; {ts[:19].replace("T", " ")} UTC'
                f' &nbsp;·&nbsp; Blocks: {blocks}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:10px 16px;'
                f'border-radius:0 8px 8px 0;margin-bottom:8px">'
                f'<b style="color:#15803d">All devices nominal</b>'
                f'<span style="color:#166534;font-size:0.82rem;margin-left:12px">'
                f'Last scan: {ts[:19].replace("T", " ")} UTC &nbsp;·&nbsp; Blocks: {blocks}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        df_live = pd.DataFrame(live_data["log"])
        st.dataframe(
            df_live[[c for c in _IDS_COLS if c in df_live.columns]],
            use_container_width=True, hide_index=True,
        )
        dl_c1, dl_c2, _ = st.columns([1, 1, 4])
        with dl_c1:
            st.download_button(
                label="Download as Excel",
                data=_excel_bytes(df_live[[c for c in _IDS_COLS if c in df_live.columns]]),
                file_name=f"ids_detection_{ts[:10]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with dl_c2:
            try:
                dev_df = get_devices(DB_PATH)
                pdf_bytes = _generate_hospital_attack_pdf(live_data, dev_df)
                ts_file = ts[:10] if ts else "report"
                st.download_button(
                    label="Download Attack Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"Hospital_Attack_Report_{ts_file}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception as _e:
                st.caption(f"PDF error: {_e}")
    else:
        st.info("No AI-IDS detection data yet. Connect MedGuard-IDS model dashboard and launch an attack.")


# ── Page router ───────────────────────────────────────────────────────────────

PAGE_FUNCS = {
    "IoMT Devices":       page_devices,
    "Attack Impact":      page_attack_impact,
}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="MediCore IoMT Monitor",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    styles.inject()
    _bootstrap()

    with st.sidebar:
        st.markdown(
            """
<div style="padding:16px 12px 8px 12px">
  <div style="font-size:1.3rem;font-weight:800;color:#f0fdf4;letter-spacing:0.01em">MediCore IoMT</div>
  <div style="font-size:0.78rem;color:#86efac;margin-top:2px">IoMT Device Monitor &middot; IDS Feed</div>
</div>
<div style="border-top:1px solid #143521;margin:4px 0 10px 0"></div>
""",
            unsafe_allow_html=True,
        )

        selected = st.radio("", PAGES, key="nav", label_visibility="collapsed")

        census = get_census(DB_PATH)
        st.markdown(
            f"""
<div style="border-top:1px solid #143521;margin-top:20px;padding:14px 12px 8px 12px">
  <div style="font-size:0.78rem;color:#86efac">
    <span style="display:inline-block;width:8px;height:8px;background:#22c55e;
    border-radius:50%;margin-right:6px;vertical-align:middle"></span>System Online
  </div>
  <div style="font-size:0.78rem;color:#86efac;margin-top:4px">
    Beds: {census['occupied_beds']}/{census['total_beds']} occupied
  </div>
  <div style="font-size:0.78rem;color:#86efac;margin-top:2px">
    ER Queue: {census['triage_waiting']} waiting
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    _db_change_watcher()
    _ids_file_watcher()   # updates session_state for siren banner

    # ── Popup: direct file read every render — no fragment timing dependency ──
    _ids_direct: dict = {}
    if IDS_RESULTS_JSON.exists():
        try:
            _ids_direct = json.loads(IDS_RESULTS_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    if _ids_direct:
        st.session_state["_ids_results"] = _ids_direct

    _anomaly_now = _ids_direct.get("anomaly_count", 0)
    _label_now   = _ids_direct.get("attack_label", "None")
    _last_popup  = st.session_state.get("_ids_last_popup_label", "")

    # Trigger popup when model detects significant anomalies (≥1 flagged device).
    # We do NOT check active_attacks because real attacks modify hospital.db
    # directly and do not update attack_plan.json, so active_attacks stays [].
    if _anomaly_now >= 1 and _label_now != _last_popup:
        st.session_state["_ids_last_popup_label"] = _label_now
        _ids_alert_dialog()
    elif _anomaly_now == 0 and _last_popup:
        # All clear — reset so next attack can trigger a fresh popup
        st.session_state.pop("_ids_last_popup_label", None)

    # ── Blinking siren banner (all pages, while attack active) ────────────────
    _render_siren_banner()

    PAGE_FUNCS[selected]()


if __name__ == "__main__":
    main()
