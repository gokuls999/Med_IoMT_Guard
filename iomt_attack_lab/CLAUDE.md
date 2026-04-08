# IoMT Attack Lab — Project Memory

## Purpose
Standalone hacker-console cyber range for launching controlled IoMT attacks against
the MediCore hospital workflow system. Completely independent from `hospital_workflow_system`
and `Med-IoMT`.

## File Structure
```
iomt_attack_lab/
├── app.py               — Streamlit hacker-terminal UI (2 pages)
├── attack_profiles.py   — Attack metadata and defaults (ATTACK_LIBRARY)
├── attack_simulator.py  — build_plan / save_attack_plan / apply_attack_plan
├── hospital_bridge.py   — launch_attack_in_hospital + load_attack_impact
├── generated/
│   ├── attack_plan.json      — Active attack plan (consumed by hospital workflow)
│   └── attack_history.jsonl  — Persistent log of all launched attacks (append-only)
├── requirements.txt
├── README.md
└── CLAUDE.md
```

## UI Design (hacker terminal aesthetic)
- **Theme**: black `#080808` bg, matrix green `#00ff41`, `Share Tech Mono` monospace font
- **Sidebar**: dark `#050505`, green nav labels, `⚡ ATTACK LAB` branding
- **2 Pages**: `💀 Attack Console` and `📡 Attack Log`

### Page 1 — Attack Console
1. **Live status bar**: shows current hospital state (SLA breach delta, latency delta, injected count, active attack types)
2. **Quick Presets** (4 buttons): `💥 ALL-OUT ATTACK`, `🕵️ STEALTH COMBO`, `💀 RANSOMWARE ONLY`, `🔄 RESET TO NORMAL`
3. **Individual attack cards** (5 cards — 3+2 grid layout):
   - Each card: icon, name, description, attack type badge
   - Per-card intensity slider (0.1 → 1.0)
   - `LAUNCH <TYPE>` primary button (red, glows on hover)
4. **Impact panel**: 4 KPI mini-cards showing last attack outcome (events compromised, SLA Δ, latency Δ, flag Δ)

### Page 2 — Attack Log
1. 4 summary KPI cards (attacks launched, resets, total events hit, worst SLA breach)
2. Grouped bar chart — Before vs After for last attack (4 metrics)
3. Timeline chart — SLA + Latency Δ across all attacks in history (only shown if >1 entry)
4. Full JSONL log table (newest first, 380px height)
5. Clear Log button

## Attack Types
| Key        | Label             | Color    | Default Intensity |
|------------|-------------------|----------|-------------------|
| dos        | DoS Flood         | #ef4444  | 0.75              |
| spoof      | Device Spoofing   | #f59e0b  | 0.65              |
| tamper     | Data Tampering    | #a78bfa  | 0.70              |
| replay     | Replay Attack     | #06b6d4  | 0.60              |
| ransomware | Ransomware Burst  | #dc2626  | 0.90              |

## Integration Flow
```
app.py (LAUNCH click)
  → build_plan()              # builds attack plan dict
  → save_attack_plan()        # writes generated/attack_plan.json
  → launch_attack_in_hospital()   # hospital_bridge.py
      → generate_hospital_workflow(cfg_base)   # baseline
      → run_system(cfg_attack)                 # with attack plan
      → writes outputs/attack_impact_report.json
  → _append_history()         # appends to generated/attack_history.jsonl
  → st.rerun()
```

## Hospital Integration Contract
`hospital_bridge.py` adds `hospital_workflow_system/` to `sys.path` and imports:
- `config.SystemConfig`
- `workflow_system.generate_hospital_workflow`, `compute_kpis`, `run_system`

Outputs written to `hospital_workflow_system/outputs/`:
- `hospital_workflow_events.csv` — attacked event stream
- `hospital_workflow_events_before_attack.csv` — baseline
- `attack_impact_report.json` — compare dict (before/after/delta)

`hospital_workflow_system/dashboard.py` reads `attack_impact_report.json` on the
`⚔️ Attack Impact` page to display before/after KPIs, grouped bar chart,
attack breakdown progress bars, and departments affected.

## Run
```bash
cd "c:/Users/ADMIN/Desktop/Binu - IoMT/iomt_attack_lab"
streamlit run app.py --server.port 8503
```

## Current Status (2026-03-05)
- Hacker terminal UI fully rewritten (v2)
- All 5 attack types launchable individually + 3 presets
- Persistent attack history in generated/attack_history.jsonl
- Hospital impact visible in hospital_workflow_system dashboard (⚔️ Attack Impact page)
- attack_impact_report.json persists between sessions
