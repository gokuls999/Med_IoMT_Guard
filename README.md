# MedGuard-IDS: Clinically-Aware Hierarchical Trust Intrusion Detection System for IoMT

A comprehensive PhD research project implementing a novel Intrusion Detection System (IDS) for the Internet of Medical Things (IoMT), featuring a hospital digital twin and a cyber attack simulation lab.

## System Architecture

The project consists of three interconnected applications:

| App | Port | Description |
|-----|------|-------------|
| **MedGuard-IDS** | 8501 | AI-powered intrusion detection with RF+GRU+XGB stacking ensemble |
| **Hospital Dashboard** | 8502 | 13-page hospital management digital twin with 140 IoMT devices |
| **Attack Lab** | 8503 | Hacker terminal UI for simulating 5 types of IoMT cyber attacks |

### How They Connect

```
Attack Lab (8503)          Hospital Dashboard (8502)          MedGuard-IDS (8501)
    |                              |                               |
    |--- launches attack --------->|                               |
    |                              |--- IoMT device stream ------->|
    |                              |                               |--- detects anomalies
    |                              |<-- detection results ---------|
    |                              |--- shows attack impact        |--- generates PDF report
```

## Core Research Contributions

### 1. Stacking Ensemble IDS (RF + GRU + XGB)
- **Random Forest** (250 trees): Captures feature interactions
- **GRU Neural Network** (PyTorch): Learns temporal/sequential patterns
- **XGBoost** (300 trees): Handles imbalanced class distributions
- **Logistic Regression** meta-learner combines all three

### 2. Adaptive Trust Engine
- Per-device trust scores with asymmetric update rates
- Trust-weighted anomaly scoring reduces false positive rate from 10.4% to 2.0%
- Devices start at trust = 0.8 (initially trusted)

### 3. Blockchain Prediction Ledger
- SHA-256 linked chain logging every IDS prediction
- Tamper-evident audit trail for forensic analysis
- Hash chain verification for integrity checking

### 4. Novel PhD Contributions (Designed)
- **CC-WFF**: Clinical Criticality-Weighted Feature Fusion
- **3T-HATF**: 3-Tier Hierarchical Adaptive Trust Federation
- **DLCA-BC**: Dual-Ledger Cross-Anchored Blockchain
- **TBDW**: Temporal Burst Detection Window

## Project Structure

```
Binu - IoMT/
|
+-- Med-IoMT/                          # Core IDS Research Engine
|   +-- demo_app.py                    # IDS Dashboard entry point
|   +-- core/
|   |   +-- stacking_model.py          # RF + GRU + XGB stacking ensemble
|   |   +-- trust_engine.py            # Adaptive per-device trust scoring
|   |   +-- blockchain.py              # SHA-256 prediction ledger
|   |   +-- realtime_engine.py         # Real-time detection pipeline
|   |   +-- preprocess.py              # Feature preprocessing
|   |   +-- data_loader.py             # Dataset loading (UNSW-NB15 + ToN-IoT)
|   |   +-- evaluation.py              # Metrics computation
|   |   +-- experiments.py             # Research experiment runner
|   |   +-- main.py                    # CLI pipeline entry point
|   +-- ids/
|   |   +-- app.py                     # Standalone IDS detection dashboard
|   |   +-- bridge.py                  # Hospital-IDS communication bridge
|   +-- data/                          # Datasets (large files excluded from repo)
|   +-- research_outputs_quickcheck/   # Pre-computed experiment results
|
+-- hospital_workflow_system/          # Hospital Digital Twin
|   +-- dashboard.py                   # 13-page Streamlit hospital management app
|   +-- hospital_db.py                 # SQLite database (13 tables, full CRUD)
|   +-- workflow_system.py             # Event generation + KPI computation
|   +-- config.py                      # System configuration
|   +-- styles.py                      # Hospital green/blue/red CSS theme
|
+-- iomt_attack_lab/                   # Cyber Attack Simulation Lab
|   +-- app.py                         # Hacker terminal Streamlit UI
|   +-- attack_profiles.py             # Attack library definitions
|   +-- attack_simulator.py            # Attack plan builder + executor
|   +-- hospital_bridge.py             # Bridge to hospital system
|
+-- documents/                         # Reference papers and screenshots
```

## Datasets

- **UNSW-NB15**: Network intrusion dataset (training + testing sets)
- **NF-ToN-IoT-v2**: IoT network traffic dataset
- Sample CSVs (30k records each) included in repo; full datasets excluded due to size

## Hospital Dashboard Pages

1. Overview - System-wide KPIs and real-time metrics
2. Patient Registry - Patient records management
3. OPD/Appointments - Outpatient scheduling
4. Emergency Department - Triage and ED management
5. IPD/Wards - Inpatient department and bed management
6. Laboratory - Lab order tracking
7. Radiology - Imaging order management
8. Pharmacy - Medication dispensing
9. Billing - Financial records
10. Staff & HR - Employee management (126 staff)
11. IoMT Devices - 140 medical device monitoring
12. Attack Impact - Before/after KPI comparison during attacks
13. Reports - PDF report generation

## Attack Types Supported

| Attack | Method | IoMT Impact |
|--------|--------|-------------|
| **DoS Flood** | TCP/UDP socket flood | Device telemetry stops, monitors flatline |
| **Device Spoofing** | MAC/IP cloning | Fake vitals injected, wrong clinical decisions |
| **Data Tampering** | MITM packet modification | Altered patient readings (e.g., SpO2 88% -> 98%) |
| **Replay Attack** | Captured packet retransmission | Stale data masks patient deterioration |
| **Ransomware** | Firmware/data encryption | Ventilators and pumps become inoperable |

## Installation

```bash
pip install -r Med-IoMT/requirements.txt
```

## Running the System

```bash
# Terminal 1 - IDS Dashboard
cd Med-IoMT
streamlit run demo_app.py --server.port 8501

# Terminal 2 - Hospital Dashboard
cd hospital_workflow_system
streamlit run dashboard.py --server.port 8502

# Terminal 3 - Attack Lab
cd iomt_attack_lab
streamlit run app.py --server.port 8503
```

## Experiment Results (10k sample)

| Variant | Accuracy | Precision | Recall | F1 | FPR |
|---------|----------|-----------|--------|-----|-----|
| Baseline (static threshold) | 0.946 | 0.952 | 0.970 | 0.961 | 0.104 |
| Adaptive threshold | 0.946 | 0.951 | 0.970 | 0.960 | 0.106 |
| Adaptive + trust-weighted | 0.582 | **0.976** | 0.393 | 0.561 | **0.020** |

## Tech Stack

- **ML/AI**: Scikit-learn, XGBoost, PyTorch (GRU), Logistic Regression
- **UI**: Streamlit, Plotly, Custom CSS themes
- **Database**: SQLite (hospital data)
- **Security**: SHA-256 blockchain, FPDF report generation
- **Data**: Pandas, NumPy

## PDF Reports

The system generates three types of PDF reports:
1. **IDS Detection Report** - Technical report with per-device predictions and trust analysis
2. **Incident Report** - Attack incident summary with affected devices and recommended actions
3. **Hospital Attack Report** - Non-technical report for hospital staff in plain English

## Author

**Binu Gokul S** - PhD Research Project
