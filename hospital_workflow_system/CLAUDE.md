# MediCore Hospital Workflow System - Project Memory (Current State)

## Purpose
This file is the persistent memory for the `hospital_workflow_system` project.
Use it to recover context after chat/token reset.

## Project Scope
This system is a full-stack hospital operations platform built with Streamlit + SQLite.
It contains:
1. Core hospital workflow modules (OPD, IPD, ED, Lab, Radiology, Pharmacy, Billing, HR).
2. IoMT device fleet, telemetry monitoring, and live virtual vitals streaming.
3. Synthetic workflow event generation for telemetry and billing seed data.

## Folder Layout
- `dashboard.py`: Main Streamlit app (page router + all 12 UI pages).
- `hospital_db.py`: SQLite schema, seeders, CRUD, analytics queries.
- `workflow_system.py`: Synthetic workflow event + billing seed generation.
- `config.py`: SystemConfig dataclass (used by workflow_system & dashboard).
- `styles.py`: CSS theme (hospital green + blue + red).
- `CLAUDE.md`: Project memory file.
- `README.md`: Project overview.
- `requirements.txt`: Python dependencies.
- `outputs/`: Generated DB and CSVs.

## Key Data Artifacts
- `outputs/hospital.db` — main SQLite database
- `outputs/hospital_workflow_events.csv` — telemetry events (IoMT Devices page)
- `outputs/hospital_kpi_report.json` — KPI snapshot
- `outputs/patient_journey_summary.csv` — patient flow summary

## Completed Features
### Hospital Operations Platform (12 Pages)
- **Overview**: Census KPIs, bed occupancy chart, triage queue, today's appointments, recent admissions.
- **Patient Registry**: Search/filter, register patient, view full patient profile with encounter history.
- **OPD / Appointments**: Today's queue, upcoming, all history, book appointment, status update.
- **Emergency Dept**: Priority triage queue, register ED patient, triage status update, pie chart.
- **IPD / Wards**: Bed map with occupancy cards, active admissions, admit/discharge forms.
- **Laboratory**: Pending orders, order test, enter results, completed results with reference ranges.
- **Radiology**: Pending scans, order scan, enter findings, scan history.
- **Pharmacy**: Pending dispensing queue, prescribe, dispense, dispensing history.
- **Billing & Finance**: Revenue charts, patient bills, generate bill, payment update.
- **Staff & HR**: Directory, shift overview chart, add employee.
- **IoMT Devices**: Device fleet table, telemetry charts, live vitals auto-stream, security signals.
- **Reports**: Clinical summary, operational metrics, financial report, CSV/JSON export.

### Database (SQLite — `outputs/hospital.db`)
Tables: `patients`, `admissions`, `beds`, `triage_queue`, `consultations`, `lab_orders`,
`radiology_orders`, `pharmacy_orders`, `iot_devices`, `iot_live_vitals`,
`employees`, `appointments`, `billing_entries`.

## Recent Fixes (Important)
1. Fixed mixed ISO datetime parsing in appointments and other pages.
   - Root cause: mixed timestamp formats with and without fractional seconds.
   - Resolution: robust datetime parsing helper in `dashboard.py`.

2. Fixed bed occupancy UI alignment issue.
   - Improved chart layout and responsive occupancy cards.

3. Fixed scenario availability metric bias.
   - `blocked_by_ids` events are now counted as safely handled, not outages.

4. Added virtual IoMT live medical values.
   - New DB table: `iot_live_vitals`.
   - Added generators and fetch APIs in `hospital_db.py`:
     - `generate_virtual_iomt_vitals(...)`
     - `get_iot_live_vitals(...)`
   - Added `Live Vitals` tab in IoMT Devices page.

5. Fixed patient table row reordering (random ID jumping).
   - Root cause: patients seeded in same second share identical `created_at`; SQLite returns tied rows in arbitrary physical order.
   - Fix: added `patient_id ASC` tiebreaker → `ORDER BY created_at DESC, patient_id ASC`.
   - Same fix applied to `get_employees()` → `ORDER BY department, role, employee_id`.

6. Replaced button-triggered IoMT snapshot with `@st.fragment(run_every=1)` auto-stream.
   - Start/Stop toggle stored in `st.session_state["iomt_live"]`.
   - Device states kept in `st.session_state["device_states"]` (dict keyed by device_id).
   - Mean-reverting random walk for realistic drift: `new = prev + noise(σ) + 0.03×(target − prev)`.
   - Drift sigmas: HR=0.6 bpm/s, SpO₂=0.08 %/s, SBP=0.7 mmHg/s, Temp=0.01 °C/s.
   - `generate_virtual_iomt_vitals()` now accepts `prev_states` and returns `(DataFrame, new_states_dict)` tuple.
   - Stationary table built from `session_state` (not DB query) — rows never reorder.

7. Full UI theme redesign to Hospital Green + Blue + Red.
   - **styles.py** completely rewritten:
     - Sidebar: `#0f172a` (dark navy) → `#0a2416` (deep forest green), border `#143521`.
     - Page header gradient: blue-teal → `#15803d → #1d4ed8` (green to blue) with green shadow.
     - KPI cards: added colored top border per metric type (green/blue/red/orange/teal).
     - Primary button: blue `#2563eb` → green `#16a34a`, hover `#15803d`.
     - Section title underline: grey → `#16a34a` (green accent).
     - Nav hover background: `#1e293b` → `#1a3d24`.
   - **dashboard.py** chart palette updates:
     - Bed occupancy bars: Occupied = red `#b91c1c`, Available = green `#16a34a`.
     - Legend moved **below** chart (no more overlap with title).
     - Revenue, Staff, Reports charts: blue-primary swapped to green-primary.
     - Bill status: "pending" changed to red for urgency signal.

## Virtual IoMT Machine Types
Current virtual device categories:
- wearable_monitor
- infusion_pump
- ventilator
- bedside_sensor
- imaging_gateway

Live medical value fields generated:
- heart_rate
- spo2
- systolic_bp
- diastolic_bp
- respiration_rate
- temperature_c
- glucose_mg_dl
- ecg_rhythm
- risk_flag

## How to Run
### Run dashboard
```powershell
cd "c:/Users/ADMIN/Desktop/Binu - IoMT/hospital_workflow_system"
python -m streamlit run dashboard.py --server.port 8502
```
The app auto-bootstraps on first launch: initialises DB, seeds data, and generates workflow CSV.

## How to Demo Quickly
1. Open `Overview` — census KPIs and bed occupancy.
2. Open `OPD / Appointments` — book and update appointment status.
3. Open `IPD / Wards` — bed map and admissions.
4. Open `IoMT Devices → Live Vitals` — click `▶ Start Stream` for real-time monitoring.
5. Open `Reports → Export` — download patient/billing/lab CSV reports.

## Current Known Gaps / Next Enhancements
- Add explicit user roles and access control (admin, nurse, doctor, finance).
- Add audit log table for manual UI edits.
- ~~Add long-running stream mode for live vitals~~ — **Done** (auto-streaming via `@st.fragment(run_every=1)`).
- Improve defense calibration to increase prevention while preserving availability.
- Add report export page for scenario comparison charts.
- Add patient discharge summary PDF generation.
- Add shift scheduling calendar view for staff.

## PDF Reports
### Attack Impact PDF (hospital staff report)
- **Function**: `_generate_hospital_attack_pdf()` in `dashboard.py`
- **Button location**: Attack Impact page, next to "Download as Excel"
- **Audience**: Non-technical hospital staff (nurses, administrators, management)
- **Content**: What attack happened (plain English), where it impacted (departments, device types), impact summary (counts, percentages), recommended actions
- **Design**: White background, green header bar, red alert box, section dividers
- **NOT included**: Anomaly scores, trust values, model internals -- those are in the IDS PDF

## Notes for Future Sessions
- Always read this file first.
- Verify dashboard health by running Streamlit and checking all 12 pages load without errors.
- If datetime issues reappear, inspect `_to_dt()` helper in `dashboard.py`.
- Attack/defense files (`attack_engine.py`, `defense_engine.py`, `scenario_runner.py`, `run_system.py`) have been intentionally removed — this is now a pure HMS project.

## External Attack Integration (2026-03-05)
- Attack simulation is now moved to a separate sibling project:
  - `c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab`
- HMS does not contain attack scenario source files.
- HMS consumes an external JSON plan at:
  - `c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab/generated/attack_plan.json`

### Config toggles
- `SystemConfig.use_external_attack_plan` (default: `True`)
- `SystemConfig.external_attack_plan` (default: `iomt_attack_lab/generated/attack_plan.json`)

### Injection behavior
- During `workflow_system.run_system()`:
  - events are generated as usual
  - external plan is loaded and applied (if present)
  - attack columns are added to event stream:
    - `attack_active`
    - `attack_type`
    - `attack_intensity`
  - report includes `attack_injection` summary

### Verified result snapshot
- Test run (`total_events=1200`) loaded plan successfully.
- Output contained attack distribution:
  - `dos`: 241
  - `tamper`: 241
  - `ransomware`: 241
  - `none`: 477
