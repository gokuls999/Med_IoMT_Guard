# IoMT Research Project — Master Memory File
> Always read this file first when resuming work in this repository.
> Last updated: 2026-07-01

---

## 1. Repository Identity

**Repo:** `c:\Users\ADMIN\Desktop\Binu - IoMT`
**GitHub:** https://github.com/gokuls999/Med_IoMT_Guard
**Git user:** Gokul Sanil
**Branch:** main

This repository contains **two independent but complementary PhD research threads**:

| Thread | Researcher | Paper Title | Focus | Port | Status |
|--------|-----------|-------------|-------|------|--------|
| **MedGuard-IDS** | Gokul | Enhancing Security in IoMT Using Blockchain & Differential Privacy | Network intrusion detection, blockchain tamper-proof logs, trust engine, RF+XGB+GRU stacking | 8501 | **Built & running** |
| **Quantum IoMT Diagnostics** | Binu | Quantum-Enhanced IoMT Diagnostic Framework | Diagnostic accuracy via ANUKF → Q-Flex ViT → BMOCO → HQAN → RBWKA → VQC → Adaptive SHARP | 8504 | **Built & running** |

> **Key distinction (confirmed 2026-07-01):**
> - Port 8501 = Gokul's security/blockchain research — ALREADY BUILT
> - Port 8504 = Binu's quantum enhancement research — BEING BUILT
> - They are compared side-by-side in Binu's Grok analysis to show complementary contributions
> - Do NOT confuse the two — they are separate PhD papers with different objectives

---

## 2. What Is Currently Running (Verified 2026-06-18)

Four Streamlit apps are built and functional:

| App | Port | Folder | Entry Point |
|-----|------|--------|-------------|
| MedGuard-IDS (AI Attack Prediction) | 8501 | `Med-IoMT/` | `demo_app.py` |
| MediCore Hospital Dashboard | 8502 | `hospital_workflow_system/` | `dashboard.py` |
| IoMT Attack Lab | 8503 | `iomt_attack_lab/` | `app.py` |
| **Quantum IoMT Diagnostics** | **8504** | **`quantum_diagnostic/`** | **`app.py`** |

**To launch all three:**
```bat
start_all.bat
```
Or individually:
```powershell
cd "Med-IoMT"
python -m streamlit run demo_app.py --server.port 8501

cd "hospital_workflow_system"
python -m streamlit run dashboard.py --server.port 8502

cd "iomt_attack_lab"
python -m streamlit run app.py --server.port 8503
```

**Environment:** Python 3.14.0, streamlit 1.54, plotly 6.6, pandas 2.3, numpy 2.4

---

## 3. MedGuard-IDS — Existing Architecture (Cybersecurity IDS)

### Purpose
Detect network-layer intrusions targeting IoMT devices in a hospital environment.

### ML Pipeline
- **Stacking Ensemble**: RF (250 trees) + GRU (PyTorch) + XGB (300 trees) → Logistic Regression meta-learner
- **Datasets**: UNSW-NB15 (network intrusion) + NF-ToN-IoT-v2 (IoT traffic)
- **Adaptive Trust Engine**: Per-device trust score ∈ [0,1], init=0.8; asymmetric α/β update
- **Dual Blockchain (DLCA-BC)**:
  - Chain A: Prediction ledger (SHA-256 linked)
  - Chain B: Trust transition ledger
  - Cross-anchoring every K=50 blocks via Merkle root

### 4 Novel PhD Contributions (MedGuard)
| Contribution | Name | Description |
|---|---|---|
| CC-WFF | Clinical Criticality-Weighted Feature Fusion | Augments network features with device criticality tier |
| 3T-HATF | 3-Tier Hierarchical Adaptive Trust Federation | Device (T1) → Gateway (T2) → Zone (T3) trust hierarchy |
| DLCA-BC | Dual-Ledger Cross-Anchored Blockchain | Bi-directional tamper detection across two chains |
| TBDW | Temporal Burst Detection Window | Sliding W=30 window for coordinated attack detection |

### Experiment Results (10k sample)
| Variant | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| Baseline static threshold | 0.946 | 0.952 | 0.970 | 0.961 | 0.104 |
| Adaptive threshold | 0.946 | 0.951 | 0.970 | 0.960 | 0.106 |
| Adaptive + trust-weighted | 0.582 | **0.976** | 0.393 | 0.561 | **0.020** |

**Key finding:** Trust-weighted mode cuts FPR from 10.4% → 2.0% but collapses recall. Root fix: initialise trust at 0.8 (not 0.5).

### Dashboard Pages (IDS — port 8501)
- Architecture (CC-WFF, 3T-HATF, DLCA-BC formulas)
- Evaluation (Plotly metric charts, variant comparison)
- Attack Simulation (normal → burst → recovery theater)
- Blockchain Explorer (dual chain, cross-link verification)
- Live Detection (real-time stream, trust evolution, threat gauge)
- Research Notes (novelty summary, presenter guide)

---

## 4. Hospital Dashboard — MediCore HMS (port 8502)

### Purpose
Hospital digital twin with 140 IoMT devices, 13 management pages, SQLite backend.

### Pages
1. Overview — Census KPIs, bed occupancy, triage queue
2. Patient Registry — Search/filter/register, encounter history
3. OPD / Appointments — Queue, booking, status update
4. Emergency Dept — Priority triage, ED registration
5. IPD / Wards — Bed map, admissions, discharge
6. Laboratory — Orders, results, reference ranges
7. Radiology — Scans, findings, history
8. Pharmacy — Dispensing queue, prescriptions
9. Billing & Finance — Revenue charts, bills, payments
10. Staff & HR — Directory, shifts, add employee
11. IoMT Devices — Device fleet, live vitals stream (auto 1s refresh)
12. Attack Impact — Before/after KPI comparison (reads `attack_impact_report.json`)
13. Reports — Clinical/operational/financial export (CSV/JSON + PDF)

### Database
- `outputs/hospital.db` — SQLite, 13 tables
- Auto-bootstraps on first launch (10–15s)
- Live vitals: HR, SpO₂, BP, RR, Temp, Glucose, ECG rhythm, risk flag

---

## 5. IoMT Attack Lab — Cyber Range (port 8503)

### Purpose
Hacker-terminal UI for launching simulated IoMT cyberattacks against MediCore.

### Attack Types
| Key | Label | Default Intensity |
|---|---|---|
| dos | DoS Flood | 0.75 |
| spoof | Device Spoofing | 0.65 |
| tamper | Data Tampering | 0.70 |
| replay | Replay Attack | 0.60 |
| ransomware | Ransomware Burst | 0.90 |

### Integration
- LAUNCH → writes `iomt_attack_lab/generated/attack_plan.json`
- Hospital (8502) reads this on `⚔️ Attack Impact` page
- Also generates `outputs/attack_impact_report.json` with before/after KPI delta

---

## 6. Binu's New Research Direction — Quantum-Enhanced IoMT Diagnostics

> This is the new research layer introduced 2026-06-18. Implementation not yet started.

### Research Problem
Current IoMT systems suffer from:
- Noisy biosignals
- Feature redundancy
- High computational cost
- Poor diagnosis accuracy → ineffective clinical decisions

Existing research treats signal processing, optimization, and diagnosis **separately**. No work combines quantum learning + adaptive optimization + explainable AI in a single IoMT environment.

### Research Aim
Propose a **hierarchical IoMT architecture** using quantum computing principles to enhance:
- Diagnostic accuracy
- Computation efficiency
- Reliability of health monitoring

---

## 7. Binu's Quantum IoMT Pipeline (from Abstract + Architecture Diagram)

```
┌─────────────────────────────────────────────────────────────────────────┐
│              Quantum-Enhanced IoMT Diagnostic Framework                 │
│                                                                         │
│  INPUT (Multimodal Physiological Data)                                  │
│  ──────────────────────────────────────                                 │
│  ECG monitor │ BP monitor │ Temperature sensor │ EEG device │ Pulse Ox  │
│                          │                                              │
│                          ▼                                              │
│  STAGE 1 — PREPROCESSING                                                │
│  ─────────────────────────                                              │
│  Adaptive Neural Unscented Kalman Filter (ANUKF)                        │
│  → Filters noisy/uncertain biosignal data                               │
│                          │                                              │
│                          ▼                                              │
│  STAGE 2 — FEATURE EXTRACTION                                           │
│  ────────────────────────────                                           │
│  Q-Flex ViT (Quantum Flexibility Vision Transformer)                    │
│  → Extracts features from multimodal physiological signals              │
│                          │                                              │
│                          ▼                                              │
│  STAGE 3 — FEATURE SELECTION                                            │
│  ────────────────────────────                                           │
│  BMOCO (Binary Multi-Objective Cheetah Optimization)                    │
│  → Selects most important, least redundant features                     │
│                          │                                              │
│                          ▼                                              │
│  STAGE 4 — ANALYSIS NETWORK                                             │
│  ──────────────────────────                                             │
│  HQAN (Hybrid Quantum Attention Network)                                │
│  → Quantum-enhanced attention over selected features                    │
│                     │         │                                         │
│                     ▼         ▼                                         │
│  STAGE 5 — DYNAMIC LAYER                                                │
│  ────────────────────────                                               │
│  DQA (Dynamic Quantum Attention Mechanism)                              │
│  DRA (Dynamic Resource Adaptation & Allocation)                         │
│                          │                                              │
│                          ▼                                              │
│  STAGE 6 — OPTIMIZATION                                                 │
│  ───────────────────────                                                │
│  RBWKA (Revamped Black-Winged Kite Algorithm)                           │
│  → Optimizes HQAN + VQC parameters (nature-inspired metaheuristic)     │
│                          │                                              │
│                          ▼                                              │
│  STAGE 7 — PREDICTION                                                   │
│  ─────────────────────                                                  │
│  VQC (Variational Quantum Circuits)                                     │
│  → Quantum-classical hybrid final diagnosis prediction                  │
│                          │                                              │
│                          ▼                                              │
│  STAGE 8 — EXPLAINABILITY & VISUALIZATION                               │
│  ────────────────────────────────────────                               │
│  Adaptive SHARP (Adaptive SHAP)                                         │
│  → Clinically interpretable explanations of predictions                 │
│                          │                                              │
│                          ▼                                              │
│  OUTPUT                                                                 │
│  ──────                                                                 │
│  Alerts & Monitoring (real-time clinical decision support)              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Novel Algorithm Reference Table (Exact Names)

| Acronym | Full Name | Stage | Role |
|---------|-----------|-------|------|
| ANUKF | Adaptive Neural Unscented Kalman Filter | Preprocessing | Biosignal denoising & uncertainty handling |
| Q-Flex ViT | Quantum Flexibility Vision Transformer | Feature Extraction | Multimodal feature extraction (quantum-hybrid ViT) |
| BMOCO | Binary Multi-Objective Cheetah Optimization | Feature Selection | Optimal feature subset selection |
| HQAN | Hybrid Quantum Attention Network | Analysis | Quantum-enhanced attention-based analysis |
| DQA | Dynamic Quantum Attention | Dynamic Layer | Adaptive quantum attention weighting |
| DRA | Dynamic Resource Adaptation/Allocation | Dynamic Layer | Runtime resource management |
| RBWKA | Revamped Black-Winged Kite Algorithm | Optimization | Nature-inspired hyperparameter optimization |
| VQC | Variational Quantum Circuits | Prediction | Quantum-classical hybrid prediction |
| Adaptive SHARP | Adaptive SHAP | Explainability | Context-aware XAI visualization |

---

## 9. Research Gap This Addresses

| Gap | How This Framework Addresses It |
|-----|--------------------------------|
| Noisy biosignals in IoMT | ANUKF adaptive non-linear filtering |
| Feature redundancy | BMOCO multi-objective selection |
| Computational cost | DRA dynamic resource allocation + quantum speedup |
| Poor diagnosis accuracy | VQC + HQAN quantum-enhanced inference |
| Lack of explainability | Adaptive SHARP clinical visualization |
| Isolated research silos | Single integrated pipeline (signal → feature → predict → explain) |

---

## 10. Differentiation from Existing Literature

| Existing Approach | Gap vs. This Work |
|---|---|
| Signal processing only | No optimization or prediction |
| Optimization only | No signal processing or XAI |
| Classical ML diagnosis | No quantum enhancement, no XAI |
| Quantum ML (general) | Not applied to multimodal IoMT biosignals |
| XAI in healthcare | No quantum component, no integrated pipeline |
| **This framework** | **First to combine ANUKF + quantum ViT + BMOCO + HQAN + VQC + Adaptive SHARP in one IoMT pipeline** |

---

## 11. Implementation Status

| Component | Status |
|-----------|--------|
| MedGuard-IDS (RF+GRU+XGB stacking) | Built, trained, running at 8501 |
| Hospital Digital Twin (MediCore) | Built, running at 8502 |
| Attack Lab (5 attack types) | Built, running at 8503 |
| ANUKF preprocessing | **Built** — `quantum_diagnostic/anukf.py` |
| Q-Flex ViT feature extraction | **Built** — `quantum_diagnostic/quantum_circuits.py` (quantum attention) |
| BMOCO feature selection | **Built** — `quantum_diagnostic/bmoco.py` |
| HQAN analysis network | **Built** — `quantum_diagnostic/quantum_circuits.py` (hqan_forward) |
| RBWKA optimization | **Built** — `quantum_diagnostic/rbwka.py` |
| VQC prediction | **Built** — `quantum_diagnostic/quantum_circuits.py` (PennyLane 0.45) |
| Adaptive SHARP visualization | **Built** — `quantum_diagnostic/pipeline.py` + `app.py` page 7 |
| DQA + DRA (Dynamic layers) | Represented in HQAN layer; dedicated module pending |

---

## 12. File Structure Reference

```
Binu - IoMT/
├── CLAUDE.md                          ← THIS FILE (master memory)
├── README.md                          ← Public overview
├── SETUP.md                           ← Deployment guide
├── start_all.bat                      ← One-click launcher (all 3 apps)
├── requirements.txt                   ← Unified dependencies
│
├── Med-IoMT/                          ← MedGuard-IDS engine
│   ├── demo_app.py                    ← IDS Dashboard (port 8501)
│   ├── core/                          ← stacking_model, trust_engine, blockchain, etc.
│   ├── data/                          ← UNSW-NB15 + NF-ToN-IoT-v2 datasets
│   ├── research_outputs_quickcheck/   ← Pre-run experiment results
│   └── CLAUDE.md                      ← IDS-specific memory
│
├── hospital_workflow_system/          ← MediCore Hospital Dashboard
│   ├── dashboard.py                   ← Hospital app (port 8502)
│   ├── hospital_db.py                 ← SQLite 13-table schema + CRUD
│   ├── workflow_system.py             ← Event generation + KPI engine
│   └── CLAUDE.md                      ← HMS-specific memory
│
├── iomt_attack_lab/                   ← Cyber Attack Lab
│   ├── app.py                         ← Attack terminal (port 8503)
│   ├── attack_profiles.py             ← 5 attack definitions
│   ├── hospital_bridge.py             ← Bridge to HMS
│   └── CLAUDE.md                      ← Attack lab memory
│
└── documents/                         ← Reference papers
    ├── ABSTRACT_BINU.pdf              ← Binu's quantum IoMT research abstract
    ├── Real-Time_Anomaly_Detection... ← Stacking IDS reference paper
    ├── HIDS-IoMT...                   ← Deep learning IDS reference
    ├── An_Efficient_Blockchain...     ← Blockchain auth reference
    └── [other reference PDFs]
```

---

## 13. Notes for Future Sessions

- The **3 existing dashboards are functional** and can be launched with `start_all.bat`
- **Binu's quantum research** is the new direction — implementation starts from scratch alongside the existing system
- All novel algorithm names in Section 8 must be used exactly as written (exact spelling matters for the paper)
- The quantum pipeline stages in Section 7 follow strict order — do not reorder
- The existing MedGuard-IDS cybersecurity system and Binu's quantum diagnostic system are **independent research threads** sharing one repository
- Trust init must be 0.8 (not 0.5) in IDS trust engine to prevent recall collapse
- Cross-chain anchoring period K=50 blocks; burst window W=30 events
