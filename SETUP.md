# MediCore HMS + IoMT Attack Lab — Setup Guide

## What's Inside

| Folder | App | Port | Description |
|--------|-----|------|-------------|
| `hospital_workflow_system/` | MediCore HMS | 8502 | Full hospital management dashboard |
| `iomt_attack_lab/` | IoMT Attack Lab | 8503 | Hacker terminal / cyber range |

Both apps are connected — the Attack Lab can launch **real attacks** that visibly disrupt MediCore.

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11 / macOS 14 / Ubuntu 22.04 |
| **Python** | 3.10 | 3.11 or 3.12 |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 500 MB free | 1 GB free |
| **Ports** | 8502, 8503 free | — |
| **Internet** | Not required after install | — |

---

## Step 1 — Unzip the Archive

### Windows
Right-click the ZIP file → **Extract All** → choose a destination folder (e.g., `C:\Projects\MediCore`).

### macOS / Linux
```bash
unzip "MediCore-IoMT-System.zip" -d ~/Projects/MediCore
```

After extraction you should see:
```
MediCore-IoMT-System/
├── hospital_workflow_system/
├── iomt_attack_lab/
└── SETUP.md   ← this file
```

---

## Step 2 — Install Python

Download Python **3.10 or higher** from https://www.python.org/downloads/

**Windows:** During installation, tick **"Add Python to PATH"** before clicking Install.

Verify:
```bash
python --version
```
Should print `Python 3.10.x` or higher.

---

## Step 3 — Install Dependencies

Open a terminal in the project folder (the folder containing this SETUP.md).

### Option A — Install once for both apps (recommended)
```bash
pip install streamlit>=1.37.0 pandas>=2.0.0 numpy>=1.24.0 plotly>=5.22.0
```

### Option B — Install from requirements files
```bash
pip install -r hospital_workflow_system/requirements.txt
pip install -r iomt_attack_lab/requirements.txt
```

> **Tip (Windows):** If `pip` is not found, try `python -m pip install ...`

> **Tip (macOS/Linux):** If your system Python is Python 2, use `pip3` and `python3` throughout.

---

## Step 4 — Run MediCore HMS (Hospital Dashboard)

Open a terminal and run:

```bash
cd hospital_workflow_system
streamlit run dashboard.py --server.port 8502
```

The browser will open automatically at **http://localhost:8502**

If it doesn't open, navigate to that URL manually.

> **First launch:** The app generates a hospital database (`outputs/hospital.db`) and simulation data. This takes about 10–15 seconds. Subsequent launches are instant.

---

## Step 5 — Run IoMT Attack Lab (Cyber Range)

Open a **second terminal** (keep MediCore running) and run:

```bash
cd iomt_attack_lab
streamlit run app.py --server.port 8503
```

The browser will open at **http://localhost:8503**

---

## Running Both Together (Windows — one command each terminal)

**Terminal 1:**
```bash
streamlit run "hospital_workflow_system/dashboard.py" --server.port 8502
```

**Terminal 2:**
```bash
streamlit run "iomt_attack_lab/app.py" --server.port 8503
```

---

## How to Use

1. Open MediCore at **http://localhost:8502** — browse the 12 hospital pages
2. Open Attack Lab at **http://localhost:8503** — go to the **ATTACK CONSOLE** page
3. Scroll to **REAL ATTACK MODE** (red banner section)
4. Click any **LAUNCH** button to start a real attack
5. Switch to MediCore and watch pages degrade in real time
6. Return to Attack Lab and click **STOP** to restore the system
7. The **REAL ATTACK IMPACT** log below the buttons shows exactly what changed

### Attack Types
| Button | Effect on MediCore |
|--------|--------------------|
| DoS FLOOD | Dashboard pages hang / time out |
| CPU STRESS | All pages slow to render |
| TAMPER DB | IoMT devices go offline, patient records flagged |
| RANSOMWARE | CSV data replaced — charts show empty/errors |
| SPOOF DEVICES | 15 rogue devices appear in IoMT Devices page |
| REPLAY INJECT | Triage queue flooded with duplicate entries |

---

## Resetting to Clean State

If the system gets into a bad state after attacks:

**Delete the database and regenerate:**
```bash
# Windows
del hospital_workflow_system\outputs\hospital.db

# macOS / Linux
rm hospital_workflow_system/outputs/hospital.db
```

Then reload MediCore at http://localhost:8502 — it will regenerate fresh data.

**Reset Attack Lab generated files:**
```bash
# Windows
del /q iomt_attack_lab\generated\*

# macOS / Linux
rm -f iomt_attack_lab/generated/*
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'streamlit'` | Run `pip install streamlit pandas numpy plotly` |
| Port already in use | Change `--server.port 8502` to another port like `8510` |
| Browser doesn't open | Navigate manually to `http://localhost:8502` |
| MediCore shows blank charts on first load | Wait 15 seconds and press F5 (data is generating) |
| Attack Lab "LAUNCH" has no visible effect | Make sure MediCore is running on port 8502 first |
| Database locked error | Close all extra browser tabs, reload once |

---

## File Structure Reference

```
hospital_workflow_system/
├── dashboard.py        — Main Streamlit app (12 pages)
├── hospital_db.py      — SQLite database + all CRUD operations
├── workflow_system.py  — Hospital simulation engine
├── styles.py           — CSS theme
├── config.py           — System configuration
└── outputs/            — Generated files (hospital.db, CSVs) — auto-created

iomt_attack_lab/
├── app.py              — Attack Lab Streamlit UI
├── real_attack_engine.py — Real system attack functions
├── attack_profiles.py  — Attack scenario definitions
├── attack_simulator.py — Simulation-mode attack builder
├── hospital_bridge.py  — Bridge between attack lab and MediCore
└── generated/          — Attack plan JSON files — auto-created
```
