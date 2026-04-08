# IoMT Attack Lab

Standalone attack simulation project for hospital workflow testing.

This folder is intentionally separate from:
- `hospital_workflow_system`
- `Med-IoMT`

## What it does
- Builds configurable attack scenarios:
  - `dos`
  - `spoof`
  - `tamper`
  - `replay`
  - `ransomware`
- Exports attack plan JSON:
  - `generated/attack_plan.json`

Hospital workflow integration reads this exported file and injects attack effects into synthetic events.

## Run
```powershell
cd "c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab"
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8503
```

## Output
- `generated/attack_plan.json`
