# Hospital Workflow System (Expanded)

This is a fuller hospital operations project with two data streams:
- Machine workflow simulation (IoMT + subsystem events)
- Manual management database (employees, patients, appointments, billing)

## Main Features
- Multi-subsystem workflow simulation
- KPI engine (operations, finance, patient flow, security)
- Local SQLite database (`outputs/hospital.db`)
- Dashboard with live data-entry forms for hospital admin workflows
- External attack-plan ingestion from sibling project `../iomt_attack_lab`

## Run
```powershell
cd "c:/Users/ADMIN/Desktop/Binu - IoMT/hospital_workflow_system"
python -m pip install -r requirements.txt
python run_system.py
python -m streamlit run dashboard.py --server.port 8502
```

## Outputs
- `outputs/hospital_workflow_events.csv`
- `outputs/hospital_kpi_report.json`
- `outputs/patient_journey_summary.csv`
- `outputs/hospital.db`

## External Attack Project
Attack scenarios are maintained outside this project:
`c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab`

The hospital workflow reads:
`c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab/generated/attack_plan.json`
