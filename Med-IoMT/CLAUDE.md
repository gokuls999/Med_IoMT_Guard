# Med-IoMT — Project Memory & Architecture Design
> Always read this file first when resuming work on this project.

---

## 1. Project Identity

**Name:** MedGuard-IDS — Clinically-Aware Hierarchical Trust IDS for IoMT
**Type:** PhD Research System (Novel Architecture)
**Stack:** Python · Scikit-learn · XGBoost · Streamlit · SQLite-free (file-based blockchain)
**Entry points:**
- `demo_app.py` → Streamlit dashboard (`streamlit run demo_app.py`)
- `main.py` → End-to-end pipeline CLI
- `experiments.py` → Research experiment runner

---

## 2. Current File Layout

```
Med-IoMT/
├── demo_app.py           ← Streamlit UI (professional dark security dashboard)
├── main.py               ← Pipeline entry point
├── experiments.py        ← Baseline vs adaptive experiment runner
├── stacking_model.py     ← RF + XGB + MLP → LR stacking ensemble
├── trust_engine.py       ← Per-device adaptive trust (α/β model)
├── blockchain.py         ← SHA-256 linked prediction ledger
├── realtime_engine.py    ← Record-by-record stream detection loop
├── preprocess.py         ← Feature normalisation + categorical encoding
├── data_loader.py        ← UNSW-NB15 + NF-ToN-IoT-v2 loader
├── evaluation.py         ← Accuracy / F1 / FPR / latency metrics
├── data/
│   ├── UNSW_NB15_training-set.parquet
│   ├── UNSW_NB15_testing-set.parquet
│   ├── UNSW_NB15_sample_30k.csv
│   ├── NF-ToN-IoT-V2.parquet
│   └── NF_ToN_IoT_V2_sample_30k.csv
├── research_outputs/     ← Full experiment outputs
├── research_outputs_quickcheck/  ← Pre-run sample outputs
├── trained_model.pkl     ← Serialised stacking bundle
├── trust_state.json      ← Per-device trust state
├── blockchain.json       ← Prediction ledger (single chain, existing)
├── requirements.txt
└── CLAUDE.md             ← This file
```

---

## 3. What Has Been Built (Current State)

### Core ML Pipeline
- **Stacking IDS**: RF (250 trees) + MLP (128→64 relu) + XGB (300 trees, depth 8) → Logistic Regression meta-learner
- **Preprocessor**: `StandardScaler` on numeric + `OneHotEncoder` on categoricals (bundled as `PreprocessBundle`)
- **Datasets**: UNSW-NB15 (network intrusion) + NF-ToN-IoT-v2 (IoT traffic) merged with unified binary label

### Adaptive Trust Engine
- Per-device trust score ∈ [0, 1], init = 0.5
- Update rule: `trust(t) = trust(t-1) - α·anomaly + β·normal`
- Adaptive threshold: `τ = base_threshold × (1 - trust)`
- Final score: `final_score = stacking_score × trust` (trust-weighted mode)

### Blockchain Ledger (Chain A only)
- SHA-256 linked blocks: `{index, timestamp, device_id, prediction, trust, prev_hash, hash}`
- `verify()` checks hash chain integrity

### Demo UI (demo_app.py — old)
- Basic Streamlit default theme (no custom CSS)
- Static PNG charts (matplotlib)
- Path text input widgets for model/CSV
- 5 sections: Overview, Evaluation, Blockchain, Real-Time Demo, Presenter Notes

### Experiment Results (quickcheck run, 10k sample)
| Variant | Accuracy | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|
| Baseline static | 0.946 | 0.952 | 0.970 | 0.961 | 0.104 |
| Adaptive threshold | 0.946 | 0.951 | 0.970 | 0.960 | 0.106 |
| Adaptive + trust-weighted | 0.582 | **0.976** | 0.393 | 0.561 | **0.020** |

**Key finding**: Trust-weighted mode reduces FPR dramatically (10.4% → 2.0%) but collapses recall (97% → 39%). Root cause: trust starts neutral (0.5), so `final_score = score × 0.5` artificially halves all scores. This is the #1 problem to solve in the new architecture.

---

## 4. Unique PhD Architecture — MedGuard-IDS

### Core Novelty Statement
> Existing IoMT IDS papers use flat per-device trust or generic network features. MedGuard-IDS introduces three original contributions that no existing paper combines: (1) Clinical Criticality-Weighted Feature Fusion, (2) 3-Tier Hierarchical Adaptive Trust Federation, and (3) Dual-Ledger Cross-Anchored Blockchain.

### Contribution 1 — CC-WFF: Clinical Criticality-Weighted Feature Fusion
**Gap addressed:** Existing papers (HIDS-IoMT, stacking model papers) use only raw network flow features, ignoring that a packet from an ICU ventilator is fundamentally more critical than one from an admin workstation.

**Proposed mechanism:**
- Each device has a `criticality_tier` ∈ {Critical=1.0, High=0.7, Medium=0.4, Low=0.2}
- Device types → tiers: `ventilator/infusion_pump → Critical`, `bedside_sensor/wearable → High`, `imaging_gateway → Medium`, `admin_node → Low`
- Augmented feature vector: `[...network_features..., criticality_score, device_type_embedding, patient_dependency_flag]`
- The meta-learner (LR) learns to weight its base-learner outputs by device criticality
- **Novel outcome**: model assigns higher anomaly confidence to clinically-critical devices

### Contribution 2 — 3T-HATF: 3-Tier Hierarchical Adaptive Trust Federation
**Gap addressed:** All existing papers use flat per-device trust with uniform α/β for all device types. A ventilator exhibiting one anomaly should be penalized more heavily than a non-critical device.

**Architecture:**
```
Hospital Zone (T3)
    │  Zone trust = weighted avg of all gateway trusts
    │  Zone risk factor R_z = 1 + λ(1 - T3)
    │
  Edge Gateway (T2)
    │  Gateway trust = weighted avg of connected device trusts
    │  Propagation: T2 += 0.01*(mean_T1 - T2) per epoch
    │
  IoMT Device (T1)  [per-device, per-update]
      trust(t) = trust(t-1) - α_eff·anomaly + β·normal
      α_eff = α × criticality_multiplier
      criticality_multiplier: Critical=3.0, High=2.0, Medium=1.0, Low=0.5
```

**Adaptive threshold (upgraded):**
```
τ = base_threshold × (1 - T1_trust) × criticality_weight × R_z
where R_z = zone_risk_factor ∈ [1.0, 1.5]
```

**Trust initialization fix:** Instead of 0.5 (neutral), devices start at 0.8 (initially trusted) so the trust-weighted score doesn't artificially halve confidence. This directly fixes the recall collapse problem.

### Contribution 3 — DLCA-BC: Dual-Ledger Cross-Anchored Blockchain
**Gap addressed:** Existing blockchain papers (paper 4, 5) use a single chain for authentication or prediction events. No paper uses dual-chain cross-verification for IoMT IDS.

**Architecture:**
```
Chain A — Prediction Ledger (existing + extended)
  Block: {index, ts, device_id, prediction, anomaly_score, trust, tier_level, hash_A}

Chain B — Trust Transition Ledger (NEW)
  Block: {index, ts, device_id, tier, old_trust, new_trust, delta, trigger,
          criticality, zone_risk_factor, hash_B}

Cross-Anchoring (every K=50 blocks):
  - Merkle root of Chain A blocks [i..i+K] written into Chain B as an "anchor block"
  - Merkle root of Chain B blocks [i..i+K] written into Chain A as an "anchor block"
  - verify_integrity() checks: hash_A chain + hash_B chain + both cross-anchors consistent
```

**Novel outcome**: Tamper detection is bi-directional. Forging a prediction record in Chain A is detectable via Chain B's anchor, and vice versa.

### Contribution 4 — TBDW: Temporal Burst Detection Window
**Gap addressed:** Single-record trust updates are slow to respond to coordinated burst attacks (e.g., DDoS across 20 devices simultaneously).

**Mechanism:**
- Sliding window of last W=30 events per device stored in memory
- `burst_density = sum(anomalies_in_window) / W`
- If `burst_density > burst_threshold (0.6)`: enter "Elevated Alert Mode"
  - `α_eff *= burst_multiplier (1.5)` — faster trust degradation
  - `base_threshold *= 0.8` — stricter detection
- Zone-level burst: if ≥3 devices simultaneously in elevated mode → zone-wide alert

---

## 5. Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────┐
│                    MedGuard-IDS System                          │
│                                                                 │
│  Data Layer           Model Layer           Trust Layer         │
│  ──────────────       ────────────────      ────────────────    │
│  UNSW-NB15       →    CC-WFF Feature   →    3T-HATF             │
│  NF-ToN-IoT-v2        Fusion                Device Trust (T1)   │
│  + Device Meta         │                    Gateway Trust (T2)  │
│                        ▼                    Zone Trust (T3)     │
│                   Stacking IDS               │                  │
│                   RF + XGB + MLP →LR         ▼                  │
│                        │              Adaptive τ                │
│                        │            (T1 × criticality × R_z)   │
│                        ▼                    │                   │
│               ┌─ Anomaly Score ─────────────┘                   │
│               │  + Trust-Weighted Score                         │
│               │  + TBDW Burst Detection                         │
│               │                                                 │
│               ▼                                                 │
│        Prediction + Response                                    │
│        (ALERT / ISOLATE / SHUTDOWN)                             │
│               │                                                 │
│               ▼                                                 │
│  Blockchain Layer: DLCA-BC                                      │
│  ────────────────────────────────                               │
│  Chain A (Predictions) ←──Cross──→ Chain B (Trust Transitions)  │
│  Every K=50 blocks: Merkle anchor                               │
│                                                                 │
│  Explainability Layer (XAI)                                     │
│  ──────────────────────────                                     │
│  SHAP values (RF + XGB) → Top-3 clinical feature explanations   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Differentiation from Referenced Papers

| Paper | Core Method | Dataset | F1 | Key Gap vs. MedGuard |
|---|---|---|---|---|
| Stacking IoMT (Paper 1) | RF+XGB+LR stacking | CIC-IoMT / WUSTL-EHMS | ~98.9% | No clinical context, no trust, no blockchain |
| HIDS-IoMT (Paper 2) | CNN+LSTM host-based DL | N-BaIoT + CICIDS 2018 | ~98.8% | No cross-device correlation, no trust hierarchy |
| LMM IoMT (Paper 3) | GPT-4V multimodal | MIMIC-III + CIC-IoMT | ~96.2% | Edge-infeasible, privacy risk, no blockchain |
| Blockchain Auth (Paper 4) | ECC + smart contract dPKI | Formal proof only | N/A | Auth only, no IDS, no cross-chain |
| Hybrid BC+AI (Paper 5) | FL/DNN + Hyperledger | TON_IoT / UNSW-NB15 | ~97.9% | Single chain, flat trust, no clinical context |
| Advanced DL (Paper 6) | Transformer/BiLSTM/GNN | CIC-IoMT + Bot-IoT | ~99.3% | No blockchain, no trust model, no clinical weighting |
| **MedGuard-IDS (Ours)** | **Stacking + 3T-HATF + DLCA-BC** | UNSW-NB15 + NF-ToN-IoT-v2 | TBD | **Only system with clinical weighting + hierarchical trust + dual blockchain** |

### Three Most Publishable PhD Gaps (confirmed by literature review)
1. **Cross-chain blockchain verification** for IoMT trust portability (no 2022–2025 paper addresses this)
2. **Clinical context weighting** via HL7/FHIR stream fusion + network anomaly detection (no paper combines these)
3. **Role-differentiated structured explainability** for clinicians, analysts, and forensic audit (aligns with EU AI Act requirements for high-risk AI in healthcare)

**Target publication venues:** IEEE TIFS, IEEE TNSM, Journal of Biomedical Informatics, IEEE JBHI, Computers in Biology and Medicine

---

## 7. Demo UI Architecture (demo_app.py — new)

### Theme
- Background: `#0d1117` (GitHub dark)
- Sidebar: `#0a1628` (deep navy)
- Primary accent: `#06b6d4` (cyan — IoMT/tech)
- Threat: `#ef4444` (red)
- Safe: `#22c55e` (green)
- Warning: `#f59e0b` (amber)
- Cards: `#161b22` (dark card) with colored top border

### Pages (6)
```
🛡️  Architecture     — system design, novelty explanations, formulas
📊  Evaluation       — plotly metrics charts, variant comparison, cross-dataset
⚔️   Attack Sim      — scenario theater (normal → burst → recovery)
⛓️   Blockchain      — dual chain explorer, cross-link verification
🔴  Live Detection   — real-time stream with threat gauge + trust evolution
📋  Research Notes   — novelty summary, contribution table, presenter guide
```

---

## 8. PDF Reports

### IDS Standalone PDF (`ids/app.py` - `_generate_pdf()`)
- **Audience**: Technical / cybersecurity analysts
- **Design**: Dark theme (matches IDS UI), cyan header bar, centered table, label-value pairs
- **Content**: Detection summary, attack types reference with IoMT impact, per-device prediction table (60 rows max), prediction statistics
- **Download**: "Download IDS Report (PDF)" button below detection log

### Unified App Incident PDF (`app.py` - `_generate_attack_pdf()`)
- **Audience**: Technical / incident response team
- **Design**: White background, red header bar, clean section dividers, centered table
- **Content**: Attack summary box, affected devices table (40 rows max), clear device count, trust analysis, recommended actions
- **Download**: "Download Incident Report (PDF)" button when intrusion detected

### Hospital Attack Report PDF (`hospital_workflow_system/dashboard.py`)
- **Audience**: Non-technical hospital staff
- **Design**: White background, green header, plain English
- **Content**: What happened (attack description), where (departments/devices), impact summary, recommended actions
- **Note**: This PDF is in the hospital project, NOT in Med-IoMT

---

## 9. Known Issues & Next Steps

### Current bugs in architecture
1. **Recall collapse** (trust-weighted mode, recall=39%): Fix by initializing trust at 0.8 (not 0.5) and tuning α. Implemented in 3T-HATF contribution.
2. **Cross-dataset generalization weak**: Feature intersection is too small between UNSW and ToN-IoT due to NF-v2 column naming differences. Fix: standardized feature mapping in `data_loader.py`.
3. **No clinical metadata in data**: IoMT devices in UNSW/ToN-IoT don't have real device type labels — simulate via CC-WFF with synthetic device-type assignment.

### Next implementation steps (priority order)
1. Implement `hierarchical_trust.py` — 3T-HATF engine with criticality-scaled α
2. Implement `dual_blockchain.py` — Chain B + Merkle cross-anchoring
3. Implement `feature_fusion.py` — CC-WFF with device metadata injection
4. Implement `burst_detector.py` — TBDW sliding window
5. Implement `xai_engine.py` — SHAP TreeExplainer wrapper
6. Rebuild `demo_app.py` — professional dark security UI (done: see current file)

### Files to keep unchanged (stable)
- `stacking_model.py` — model architecture is solid
- `preprocess.py` — preprocessing pipeline works
- `data_loader.py` — loaders work (minor fix needed for NF-v2 columns)
- `evaluation.py` — metrics are correct

---

## 10. Research Output Files

```
research_outputs_quickcheck/
├── experiment_results.json   ← 3-variant comparison (10k sample)
├── metrics_comparison.png    ← bar chart (matplotlib, to replace with plotly in UI)
├── trust_evolution.png       ← trust/score/threshold evolution
└── adaptive_outputs_sample.json  ← 300 per-record outputs
```

---

## 11. How to Run

### Run demo UI
```bash
cd "c:/Users/ADMIN/Desktop/Binu - IoMT/Med-IoMT"
streamlit run demo_app.py
```

### Run full pipeline
```bash
python main.py \
  --unsw_csv data/UNSW_NB15_sample_30k.csv \
  --ton_csv data/NF_ToN_IoT_V2_sample_30k.csv
```

### Run experiments
```bash
python experiments.py \
  --unsw_csv data/UNSW_NB15_sample_30k.csv \
  --ton_csv data/NF_ToN_IoT_V2_sample_30k.csv \
  --sample_size 30000
```

---

## 12. Notes for Future Sessions

- The 3 PhD novel contributions are: CC-WFF, 3T-HATF, DLCA-BC
- Trust initialization must be 0.8 (not 0.5) to prevent recall collapse
- Clinical criticality multipliers: Critical=3.0, High=2.0, Medium=1.0, Low=0.5
- Cross-anchoring period K=50 blocks
- Burst detection window W=30 events, density threshold=0.6
- demo_app.py uses professional dark cyan/red/green theme (see CSS in file)
- Do NOT collaborate with hospital_workflow_system — these are independent projects

---

## 13. Verification Log - 2026-03-04

### User-reported issue
- Attack Simulation page threw:
  `TypeError: Figure.update_layout() got multiple values for keyword argument 'yaxis'`

### Current status
- Checked `demo_app.py`:
  - `_plotly_dark()` now returns only base theme keys (`template`, `paper_bgcolor`, `plot_bgcolor`, `font`).
  - `_plotly_dark()` does NOT include `xaxis` or `yaxis`.
- Direct smoke test passed:
  - `fig.update_layout(yaxis=..., **_plotly_dark())` works without TypeError.
- Full Med-IoMT health checks passed:
  - AST parse for all `.py` files: PASS
  - Module imports (`data_loader`, `preprocess`, `stacking_model`, `trust_engine`, `blockchain`, `realtime_engine`, `evaluation`, `experiments`, `main`, `demo_app`): PASS
  - End-to-end run: `python main.py --unsw_csv data/UNSW_NB15_sample_30k.csv --ton_csv data/NF_ToN_IoT_V2_sample_30k.csv --demo_records 80`: PASS
- Streamlit app restarted to avoid stale cache/process:
  - Running on `http://localhost:8501`
  - PID: `24436`

### Conclusion
- The specific `yaxis` duplicate-keyword crash is not present in the current code/process.
- If the same traceback appears again, it indicates an old Streamlit process/browser cache was serving older code. Restarting Streamlit resolves that.

### Additional fix (same day)
- New Evaluation-page error reported:
  `ValueError: Invalid value ... fillcolor ... '#06b6d41a'` from `go.Scatterpolar`.
- Root cause:
  - Plotly in current environment rejects 8-digit hex alpha format used via string concat (`#RRGGBB` + `1a`).
- Fix applied in `demo_app.py`:
  - Added helper `_hex_to_rgba(hex_color, alpha)` that converts theme colors to Plotly-safe `rgba(r,g,b,a)`.
  - Replaced radar `fillcolor` construction with `_hex_to_rgba(base_color, 0.1)`.
- Verification:
  - `demo_app.py` AST/import check: PASS
  - direct `go.Scatterpolar(..., fillcolor=...)` smoke test: PASS
  - Streamlit restarted and listening on `http://localhost:8501` (PID at verification: `23432`)
