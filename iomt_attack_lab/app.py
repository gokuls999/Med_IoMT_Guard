"""
IoMT Attack Lab — Hacker Console
Launches controlled cyberattacks against the hospital workflow system.
Run: streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from attack_profiles import ATTACK_LIBRARY, DEFAULT_DEPARTMENTS, DEFAULT_DEVICE_TYPES
from attack_simulator import build_plan, save_attack_plan
from hospital_bridge import launch_attack_in_hospital, load_attack_impact, undo_last_attack
import real_attack_engine as _real_eng

ROOT      = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "generated" / "attack_plan.json"
HIST_PATH = ROOT / "generated" / "attack_history.jsonl"
GEN_DIR   = ROOT / "generated"
GEN_DIR.mkdir(parents=True, exist_ok=True)

# Hospital outputs path (for live event stream)
EVENTS_CSV = ROOT.parent / "hospital_workflow_system" / "outputs" / "hospital_workflow_events.csv"

# ── Attack metadata ────────────────────────────────────────────────────────────
ATTACKS = {
    "dos": {
        "icon": "[DOS]", "label": "DoS Flood",
        "desc": "Floods the network. Spikes latency, delays all hospital events.",
        "color": "#ef4444", "default_intensity": 0.75,
        "start_pct": 0.10, "end_pct": 0.85,
    },
    "spoof": {
        "icon": "[SPF]", "label": "Device Spoofing",
        "desc": "Impersonates trusted IoMT devices. Raises auth failures and command risk.",
        "color": "#f59e0b", "default_intensity": 0.65,
        "start_pct": 0.20, "end_pct": 0.70,
    },
    "tamper": {
        "icon": "[TMP]", "label": "Data Tampering",
        "desc": "Manipulates telemetry and clinical data fields in the event stream.",
        "color": "#a78bfa", "default_intensity": 0.70,
        "start_pct": 0.30, "end_pct": 0.75,
    },
    "replay": {
        "icon": "[RPL]", "label": "Replay Attack",
        "desc": "Replays stale valid packets to confuse device authentication.",
        "color": "#06b6d4", "default_intensity": 0.60,
        "start_pct": 0.25, "end_pct": 0.65,
    },
    "ransomware": {
        "icon": "[RNS]", "label": "Ransomware Burst",
        "desc": "Maxes CPU, degrades services, marks critical events as escalated.",
        "color": "#dc2626", "default_intensity": 0.90,
        "start_pct": 0.50, "end_pct": 0.95,
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _term_table(df: "pd.DataFrame", highlight_col: str = "") -> str:
    """Render a DataFrame as a terminal-green HTML table (visible on black bg)."""
    import pandas as _pd
    cols = list(df.columns)
    hdr = "".join(
        f'<th style="color:#22c55e;text-align:left;padding:5px 10px;'
        f'border-bottom:1px solid #1a3a1a;white-space:nowrap;font-size:0.71rem;'
        f'background:#050f05">{c}</th>'
        for c in cols
    )
    body = ""
    for _, row in df.iterrows():
        is_flagged = False
        if highlight_col and highlight_col in row:
            try:
                is_flagged = int(float(str(row[highlight_col]))) == 1
            except Exception:
                is_flagged = str(row[highlight_col]).strip().lower() not in ("0", "none", "nan", "no", "")
        row_bg = "#1a0404" if is_flagged else "#050f05"
        cells = ""
        for c in cols:
            v = row[c]
            v_str = str(v) if _pd.notna(v) else "—"
            if c in ("attack_active", "attacked"):
                try:
                    flag = int(float(v_str)) == 1
                except Exception:
                    flag = False
                c_col = "#ef4444" if flag else "#22c55e"
                v_str = "YES" if flag else "NO"
            elif c in ("attack_type", "threat") and v_str.lower() not in ("none", "nan", "—", ""):
                c_col = "#f59e0b"
                v_str = v_str.upper()
            elif c in ("security_flag", "flag", "sla_breached"):
                try:
                    c_col = "#ef4444" if int(float(v_str)) == 1 else "#4a8a4a"
                except Exception:
                    c_col = "#4a8a4a"
            elif c == "latency_ms":
                try:
                    v_f = float(v_str)
                    # Baseline: mean=54ms max=108ms. DoS attack: mean=139ms max=278ms
                    c_col = "#ef4444" if v_f > 130 else "#f59e0b" if v_f > 85 else "#22c55e"
                    v_str = f"{v_f:,.0f} ms"
                except Exception:
                    c_col = "#7abd7a"
            elif c == "cpu_pct":
                try:
                    v_f = float(v_str)
                    # Ransomware pushes to 90-100%. DoS barely affects CPU.
                    c_col = "#ef4444" if v_f > 75 else "#f59e0b" if v_f > 55 else "#22c55e"
                    v_str = f"{v_f:.1f}%"
                except Exception:
                    c_col = "#7abd7a"
            elif c == "status":
                sl = v_str.lower()
                if sl in ("delayed", "escalated", "failed", "error", "timeout"):
                    c_col = "#ef4444"
                elif sl in ("pending", "waiting", "queued", "processing"):
                    c_col = "#f59e0b"
                elif sl == "completed":
                    c_col = "#22c55e"
                else:
                    c_col = "#7abd7a"
            elif c == "command_risk":
                try:
                    v_f = float(v_str)
                    # Baseline max=0.50. Spoof/tamper push to 0.7–0.95.
                    c_col = "#ef4444" if v_f > 0.55 else "#f59e0b" if v_f > 0.38 else "#22c55e"
                    v_str = f"{v_f:.2f}"
                except Exception:
                    c_col = "#7abd7a"
            else:
                c_col = "#7abd7a"
            cells += (
                f'<td style="color:{c_col};padding:4px 10px;border-bottom:1px solid #0f1a0f;'
                f'font-size:0.71rem;white-space:nowrap">{v_str}</td>'
            )
        body += f'<tr style="background:{row_bg}">{cells}</tr>'
    return (
        f'<div style="overflow-x:auto;overflow-y:auto;max-height:360px;'
        f'background:#050f05;border:1px solid #1a3a1a;border-radius:6px">'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'Share Tech Mono\',monospace">'
        f'<thead><tr>{hdr}</tr></thead><tbody>{body}</tbody>'
        f'</table></div>'
    )


def _append_history(entry: dict) -> None:
    with open(HIST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _load_history() -> list[dict]:
    if not HIST_PATH.exists():
        return []
    rows = []
    for line in HIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return list(reversed(rows))  # newest first


_ACTIVE_STATUS_FILE = GEN_DIR / "active_attacks.json"


def _write_active_status() -> None:
    """Write current active real-attack list to shared JSON for IDS bridge."""
    active = _real_eng.active_attacks() if _real_eng else []
    try:
        _ACTIVE_STATUS_FILE.write_text(
            json.dumps({"active": active, "ts": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
    except Exception:
        pass


def _do_launch(attack_keys: list[str], intensities: dict[str, float], label: str) -> dict:
    attack_rows = []
    for key in attack_keys:
        meta = ATTACKS[key]
        attack_rows.append({
            "attack_type": key,
            "intensity": intensities.get(key, meta["default_intensity"]),
            "start_pct": meta["start_pct"],
            "end_pct": meta["end_pct"],
            "target_departments": DEFAULT_DEPARTMENTS,
            "target_device_types": DEFAULT_DEVICE_TYPES,
        })
    plan = build_plan(total_events=5000, seed=42, attack_rows=attack_rows, scenario_name=label)
    save_attack_plan(plan, PLAN_PATH)
    impact = launch_attack_in_hospital(total_events=5000, seed=42)
    _append_history({
        "ts": datetime.now(timezone.utc).isoformat(),
        "scenario": label,
        "attacks": attack_keys,
        "intensities": {k: intensities.get(k, ATTACKS[k]["default_intensity"]) for k in attack_keys},
        "sla_delta": impact.get("delta", {}).get("sla_breach_rate", 0.0),
        "latency_delta": impact.get("delta", {}).get("avg_latency_ms", 0.0),
        "flagged_delta": impact.get("delta", {}).get("security_flagged_events", 0),
        "injected": impact.get("attack_injection", {}).get("total_attacks_injected", 0),
        "breakdown": impact.get("attack_injection", {}).get("attack_breakdown", {}),
    })
    return impact


def _do_reset() -> dict:
    plan = build_plan(total_events=5000, seed=42, attack_rows=[], scenario_name="reset")
    save_attack_plan(plan, PLAN_PATH)
    impact = launch_attack_in_hospital(total_events=5000, seed=42)
    _append_history({
        "ts": datetime.now(timezone.utc).isoformat(),
        "scenario": "RESET", "attacks": [], "intensities": {},
        "sla_delta": 0.0, "latency_delta": 0.0, "flagged_delta": 0, "injected": 0, "breakdown": {},
    })
    return impact


# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #080808 !important; }
.block-container { padding: 0.3rem 1.8rem 2rem 1.8rem !important; }
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { display: none !important; }

[data-testid="stSidebar"] {
    background-color: #050505 !important;
    border-right: 1px solid #1a3a1a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #3a6a3a !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 14px !important; border-radius: 4px !important;
    font-size: 0.88rem !important; font-weight: 600 !important;
    color: #3a6a3a !important; cursor: pointer !important;
    font-family: 'Share Tech Mono', monospace !important;
    display: block !important; transition: all 0.15s !important;
    border: none !important; letter-spacing: 0.03em;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #0a1a0a !important; color: #00ff41 !important;
}
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] span:first-child {
    display: none !important;
}

.term-header {
    font-family: 'Share Tech Mono', monospace;
    background: #050505; border: 1px solid #1a3a1a;
    border-top: 2px solid #00ff41; border-radius: 6px;
    padding: 14px 20px 10px 20px; margin-bottom: 20px;
}
.term-title { color: #00ff41; font-size: 1.25rem; letter-spacing: 0.08em; margin: 0; }
.term-sub   { color: #2d5a2d; font-size: 0.76rem; margin: 4px 0 0 0; letter-spacing: 0.04em; }

.status-bar {
    font-family: 'Share Tech Mono', monospace;
    background: #050505; border: 1px solid #1a3a1a;
    border-radius: 6px; padding: 8px 14px;
    font-size: 0.76rem; color: #2d5a2d;
    display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 16px;
}
.s-ok    { color: #22c55e; }
.s-warn  { color: #f59e0b; }
.s-alert { color: #ef4444; }

.atk-card {
    background: #0c0c0c; border: 1px solid #1a1a1a;
    border-radius: 8px; padding: 14px 14px 10px 14px;
}
.atk-icon { font-size: 1.7rem; line-height: 1; margin-bottom: 5px; }
.atk-name { color: #e2e8f0; font-size: 0.92rem; font-weight: 700; margin: 0; }
.atk-desc { color: #334155; font-size: 0.76rem; margin: 4px 0 6px 0; line-height: 1.4; }
.atk-tag  {
    display: inline-block; padding: 2px 8px; border-radius: 3px;
    font-size: 0.66rem; font-weight: 700; letter-spacing: 0.05em;
    text-transform: uppercase; font-family: 'Share Tech Mono', monospace;
}

.imp-card {
    background: #0c0c0c; border: 1px solid #1a1a1a;
    border-radius: 8px; padding: 12px 14px; text-align: center;
}
.imp-val { font-size: 1.6rem; font-weight: 700; font-family: 'Share Tech Mono', monospace; }
.imp-lbl { font-size: 0.68rem; color: #334155; text-transform: uppercase;
           letter-spacing: 0.05em; margin-top: 3px; }
.bad  { color: #ef4444; }
.good { color: #22c55e; }
.neu  { color: #64748b; }

.mono { font-family: 'Share Tech Mono', monospace; }
.section-label {
    font-family: 'Share Tech Mono', monospace; color: #2d5a2d;
    font-size: 0.7rem; letter-spacing: 0.06em; margin: 14px 0 8px 0;
}

[data-testid="stDataFrame"] { border-radius: 6px; }

.stButton > button {
    border-radius: 4px !important; font-weight: 700 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 0.04em !important; transition: all 0.12s !important;
}
.stButton > button[kind="primary"] {
    background-color: #dc2626 !important;
    border-color: #ef4444 !important; color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #b91c1c !important;
    box-shadow: 0 0 12px rgba(220,38,38,0.35) !important;
}
.stSlider > div > div > div { background: #00ff41 !important; }
hr { border-color: #151515 !important; }
</style>
"""


# ── Live event stream (module-level so fragment persists across rerenders) ─────

@st.fragment(run_every=3)
def _live_event_stream() -> None:
    if not EVENTS_CSV.exists():
        st.markdown(
            '<div style="font-family:\'Share Tech Mono\',monospace;color:#2d5a2d;'
            'padding:20px 0;text-align:center;font-size:0.78rem">'
            '> NO EVENT DATA — LAUNCH AN ATTACK TO POPULATE THE STREAM'
            '</div>',
            unsafe_allow_html=True,
        )
        return
    try:
        ev = pd.read_csv(EVENTS_CSV)
    except Exception:
        st.markdown(
            '<span style="font-family:\'Share Tech Mono\',monospace;color:#ef4444;'
            'font-size:0.78rem">> ERROR READING EVENT STREAM</span>',
            unsafe_allow_html=True,
        )
        return

    total = len(ev)
    if total == 0:
        return

    attacked_mask = (ev["attack_active"] == 1) if "attack_active" in ev.columns else pd.Series([False] * total, index=ev.index)
    attacked = int(attacked_mask.sum())
    pct = attacked / total if total > 0 else 0

    if attacked > 0:
        # ── Identify active attack types ──────────────────────────────────
        atk_types = []
        if "attack_type" in ev.columns:
            atk_types = [t for t in ev.loc[attacked_mask, "attack_type"].unique()
                         if str(t).lower() not in ("none", "nan", "")]
        type_str = " + ".join(t.upper() for t in atk_types) if atk_types else "UNKNOWN"

        # ── Red alert banner ──────────────────────────────────────────────
        st.markdown(
            f'<div style="background:#200000;border:2px solid #ef4444;border-radius:6px;'
            f'padding:12px 18px;margin-bottom:14px;font-family:\'Share Tech Mono\',monospace">'
            f'<div style="color:#ef4444;font-size:0.95rem;font-weight:700;letter-spacing:0.07em">'
            f'[!!!] ACTIVE ATTACK: {type_str}</div>'
            f'<div style="color:#7f1d1d;font-size:0.69rem;margin-top:5px">'
            f'{attacked:,} of {total:,} events compromised ({pct:.1%})'
            f' &nbsp;|&nbsp; table below shows compromised events only — values colored by severity'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Live metrics vs baseline ──────────────────────────────────────
        BEFORE_CSV = EVENTS_CSV.parent / "hospital_workflow_events_before_attack.csv"
        try:
            before_df = pd.read_csv(BEFORE_CSV) if BEFORE_CSV.exists() else None
        except Exception:
            before_df = None

        metric_defs = [
            # Thresholds calibrated to actual simulation output:
            # Baseline latency mean=54ms max=108ms; attacked mean=139ms
            # Baseline SLA breach=48%; DoS→63%, ransomware→~100%
            # Baseline CPU mean=43%; ransomware→90%+
            ("AVG LATENCY",  "latency_ms",    lambda s: s.mean(),        "{:.0f} ms", 130,  85),
            ("SLA BREACH",   "sla_breached",  lambda s: s.mean(),        "{:.1%}",    0.62, 0.53),
            ("AVG CPU",      "cpu_pct",       lambda s: s.mean(),        "{:.1f}%",   75,   55),
            ("SEC FLAGS",    "security_flag", lambda s: float(s.sum()),  "{:,.0f}",   30,   5),
        ]
        m_cols = st.columns(4)
        for idx, (lbl, col_name, agg_fn, fmt, thresh_bad, thresh_warn) in enumerate(metric_defs):
            if col_name not in ev.columns:
                continue
            cur = agg_fn(ev.loc[attacked_mask, col_name])
            c_col = "#ef4444" if cur > thresh_bad else "#f59e0b" if cur > thresh_warn else "#22c55e"

            base_line = ""
            delta_line = ""
            if before_df is not None and col_name in before_df.columns:
                base = agg_fn(before_df[col_name])
                base_line = f'baseline: {fmt.format(base)}'
                delta = cur - base
                if col_name == "sla_breached":
                    delta_line = f'+{delta * 100:.1f}pp' if delta >= 0 else f'{delta * 100:.1f}pp'
                elif col_name == "security_flag":
                    delta_line = f'+{int(delta):,}' if delta >= 0 else f'{int(delta):,}'
                else:
                    delta_line = f'+{delta:.0f}' if delta >= 0 else f'{delta:.0f}'

            m_cols[idx].markdown(
                f'<div style="background:#0c0c0c;border:1px solid #2a1010;'
                f'border-top:2px solid {c_col};border-radius:6px;padding:10px 12px;text-align:center">'
                f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:1.05rem;'
                f'font-weight:700;color:{c_col}">{fmt.format(cur)}</div>'
                f'{"<div style=\"font-size:0.60rem;color:#ef444499;margin-top:1px\">" + delta_line + " from baseline</div>" if delta_line else ""}'
                f'<div style="font-size:0.60rem;color:#334155;margin-top:3px">{lbl}</div>'
                f'{"<div style=\"font-size:0.57rem;color:#1f3a1f;margin-top:1px\">" + base_line + "</div>" if base_line else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

        # Show ATTACK events — not the tail (which may be post-attack)
        show_df = ev.loc[attacked_mask].tail(30).copy()
        stream_label = f'> SHOWING {min(30, attacked):,} MOST RECENT COMPROMISED EVENTS ({attacked:,} total attacked)'

    else:
        st.markdown(
            '<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.72rem;'
            'color:#22c55e;padding:4px 0;margin-bottom:8px">'
            'SYSTEM STATUS: CLEAN — NO ACTIVE ATTACKS</div>',
            unsafe_allow_html=True,
        )
        show_df = ev.tail(20).copy()
        stream_label = f'> LAST 20 EVENTS — {total:,} TOTAL IN DATASET'

    # ── Build table ───────────────────────────────────────────────────────────
    cols_show = [c for c in [
        "event_id", "department", "device_type", "status", "latency_ms",
        "cpu_pct", "command_risk", "attack_active", "attack_type", "security_flag", "sla_breached",
    ] if c in show_df.columns]
    display = show_df[cols_show].rename(columns={
        "attack_active": "attacked", "attack_type": "threat", "security_flag": "flag",
    })

    st.markdown(
        f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.67rem;'
        f'color:#2d5a2d;margin-bottom:5px">{stream_label}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(_term_table(display, highlight_col="attacked"), unsafe_allow_html=True)

    s_col = "#ef4444" if attacked > 0 else "#22c55e"
    s_txt = "UNDER ATTACK" if attacked > 0 else "CLEAN"
    st.markdown(
        f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.7rem;'
        f'color:#4a8a4a;margin-top:6px">'
        f'> {total:,} total events &nbsp;|&nbsp; '
        f'<span style="color:{s_col};font-weight:700">{attacked:,} compromised ({pct:.1%}) — {s_txt}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Page: Attack Console ───────────────────────────────────────────────────────

def page_console() -> None:
    st.markdown(
        '<div class="term-header">'
        '<div class="term-title">[ IoMT ATTACK CONSOLE ]</div>'
        '<div class="term-sub">> TARGET: MediCore Hospital Workflow System &nbsp;|&nbsp; '
        'ALL ATTACKS LOGGED &nbsp;|&nbsp; 5 ATTACK TYPES AVAILABLE</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Live status bar
    impact = load_attack_impact()
    if impact:
        sla_d = impact.get("delta", {}).get("sla_breach_rate", 0.0)
        lat_d = impact.get("delta", {}).get("avg_latency_ms", 0.0)
        inj   = impact.get("attack_injection", {}).get("total_attacks_injected", 0)
        types = ", ".join(impact.get("attack_injection", {}).get("attack_types", [])) or "none"
        sc = "s-alert" if sla_d > 0.05 else "s-ok"
        lc = "s-warn"  if lat_d > 50  else "s-ok"
        st.markdown(
            f'<div class="status-bar">'
            f'<span>HOSPITAL_STATUS:</span>'
            f'<span class="{sc}">SLA_BREACH {sla_d:+.1%}</span>'
            f'<span class="{lc}">LATENCY {lat_d:+.0f}ms</span>'
            f'<span class="s-alert">INJECTED {inj:,}</span>'
            f'<span class="s-warn">ATTACKS [{types.upper()}]</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-bar">'
            '<span>HOSPITAL_STATUS:</span>'
            '<span class="s-ok">CLEAN — NO ATTACKS ACTIVE</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Real Attack Mode ──────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#1a0000;border:2px solid #ef4444;border-radius:6px;'
        'padding:12px 18px;margin-bottom:12px;font-family:\'Share Tech Mono\',monospace">'
        '<div style="color:#ef4444;font-size:0.88rem;font-weight:700;letter-spacing:0.07em">'
        '[!!!] REAL ATTACK MODE — ACTUAL SYSTEM DISRUPTION</div>'
        '<div style="color:#7f1d1d;font-size:0.68rem;margin-top:6px;line-height:1.6">'
        'These attacks cause REAL changes to MediCore HMS at localhost:8502. '
        'DoS floods the actual HTTP server causing the dashboard to freeze. '
        'Tamper / Spoof / Replay write directly to hospital.db — visible instantly in MediCore pages. '
        'Ransomware overwrites actual CSV/JSON outputs so dashboard throws read errors. '
        'CPU Stress pins your actual processor. All attacks are reversible via STOP ALL.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Status: which real attacks are currently running
    active_real = _real_eng.active_attacks()
    if active_real:
        status_tags = " &nbsp; ".join(
            f'<span style="font-family:\'Share Tech Mono\',monospace;background:#ef444418;'
            f'color:#ef4444;border:1px solid #ef444440;padding:3px 10px;border-radius:3px;'
            f'font-size:0.72rem;font-weight:700">{a.upper()}: RUNNING</span>'
            for a in active_real
        )
        st.markdown(
            f'<div style="margin-bottom:10px">'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.67rem;'
            f'color:#ef4444;margin-right:8px">ACTIVE REAL ATTACKS:</span>{status_tags}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.7rem;'
            'color:#22c55e;margin-bottom:10px">REAL SYSTEM STATUS: ALL CLEAR — NO ACTIVE DISRUPTION</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">> SELECT &amp; LAUNCH REAL ATTACK AGAINST MEDICORE HMS</div>', unsafe_allow_html=True)

    REAL_ATTACKS = [
        {
            "key": "dos", "icon": "[DOS]", "label": "DoS FLOOD", "color": "#ef4444",
            "method": "TCP socket flood -- 50 threads x 500 req/s against localhost:8502",
            "iomt_impact": [
                "IoMT telemetry stream stops updating -- live vitals flatline",
                "Device status checks timeout -- all 140 devices appear unresponsive",
                "Security signal polling fails -- IDS model cannot scan devices",
            ],
            "hospital_impact": "Dashboard pages hang, forms fail, auto-refresh stalls",
        },
        {
            "key": "cpu", "icon": "[CPU]", "label": "CPU STRESS", "color": "#f97316",
            "method": "Busy-loop threads pin all CPU cores at 100% for 60s",
            "iomt_impact": [
                "IDS model inference slows from ms to seconds per device",
                "Telemetry chart re-computation (pandas groupby) becomes sluggish",
                "Auto-refresh fragments stretch from 3s to 20s+ cycles",
            ],
            "hospital_impact": "Entire system sluggish -- Task Manager shows Python at 90-100%",
        },
        {
            "key": "tamper", "icon": "[TMP]", "label": "DATA TAMPER", "color": "#a78bfa",
            "method": "Direct SQL UPDATE on hospital.db -- 5 targeted corruption queries",
            "iomt_impact": [
                "ALL 140 IoMT devices set to status=offline, firmware=CORRUPTED",
                "IDS detects mass anomaly -- every device flagged as compromised",
                "Device fleet shows 0% online -- complete fleet failure simulation",
            ],
            "hospital_impact": "Patients COMPROMISED, billing VOIDED, beds contaminated, triage escalated",
        },
        {
            "key": "ransomware", "icon": "[RNS]", "label": "RANSOMWARE", "color": "#dc2626",
            "method": "Overwrites all CSV/JSON in outputs/ with ENCRYPTED placeholders",
            "iomt_impact": [
                "IoMT telemetry CSV replaced -- charts show blank/empty series",
                "Device event history wiped -- no historical data available",
                "IDS detection results JSON overwritten with ransom message",
            ],
            "hospital_impact": "All dashboard pages crash -- pandas read errors everywhere",
        },
        {
            "key": "spoof", "icon": "[SPF]", "label": "DEVICE SPOOF", "color": "#f59e0b",
            "method": "INSERT 15 rogue devices (ROGUE001-015) into iot_devices table",
            "iomt_impact": [
                "Device count jumps from 140 to 155 -- 15 unknown devices appear",
                "All rogue devices: criticality=critical, firmware=UNKNOWN_ROGUE_v0.0",
                "IP addresses 10.0.99.x appear -- outside normal hospital subnet",
            ],
            "hospital_impact": "IoMT fleet trust collapses -- cannot distinguish real from fake devices",
        },
        {
            "key": "replay", "icon": "[RPL]", "label": "REPLAY INJECT", "color": "#06b6d4",
            "method": "Background thread duplicates triage entries every 1.5s for 60s",
            "iomt_impact": [
                "IoMT-linked patient queue inflated with ghost entries",
                "Device-triggered triage alerts replayed -- false emergency signals",
                "Queue integrity destroyed -- real patients lost behind duplicates",
            ],
            "hospital_impact": "Emergency triage queue grows every 2s -- 40+ duplicate entries",
        },
    ]

    real_action = None
    # Row 1: first 3 attacks
    r1c1, r1c2, r1c3 = st.columns(3)
    # Row 2: next 3 attacks
    r2c1, r2c2, r2c3 = st.columns(3)
    card_cols = [r1c1, r1c2, r1c3, r2c1, r2c2, r2c3]

    for col, atk in zip(card_cols, REAL_ATTACKS):
        key = atk["key"]
        c = atk["color"]
        is_running = key in active_real

        status_badge = (
            f'<span style="background:#22c55e22;color:#22c55e;border:1px solid #22c55e44;'
            f'padding:2px 8px;border-radius:3px;font-size:0.6rem;font-weight:700;'
            f'font-family:\'Share Tech Mono\',monospace">RUNNING</span>'
            if is_running else
            f'<span style="background:{c}18;color:{c};border:1px solid {c}35;'
            f'padding:2px 8px;border-radius:3px;font-size:0.6rem;font-weight:700;'
            f'font-family:\'Share Tech Mono\',monospace">{key.upper()}</span>'
        )

        iomt_items = "".join(
            f'<li style="font-size:0.64rem;color:#8b9ab5;margin-bottom:3px;line-height:1.4">{item}</li>'
            for item in atk["iomt_impact"]
        )

        border_color = "#22c55e" if is_running else c
        bg_color = "#001a00" if is_running else "#0c0c0c"

        col.markdown(
            f'<div style="background:{bg_color};border:1px solid {border_color}40;'
            f'border-top:3px solid {border_color};border-radius:8px;padding:14px 14px 10px 14px;'
            f'margin-bottom:8px;min-height:280px">'
            # Header: icon + name + badge
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">'
            f'<span style="font-size:1.4rem">{atk["icon"]}</span>'
            f'{status_badge}'
            f'</div>'
            f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.85rem;'
            f'font-weight:700;color:{border_color};letter-spacing:0.04em;margin-bottom:6px">'
            f'{atk["label"]}</div>'
            # Method
            f'<div style="font-size:0.66rem;color:#475569;line-height:1.5;margin-bottom:8px;'
            f'border-left:2px solid {c}44;padding-left:8px">{atk["method"]}</div>'
            # IoMT Impact
            f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:0.58rem;'
            f'color:#2d5a2d;letter-spacing:0.06em;margin-bottom:4px">IoMT DEVICE IMPACT</div>'
            f'<ul style="margin:0 0 6px 0;padding-left:14px">{iomt_items}</ul>'
            # Hospital one-liner
            f'<div style="font-size:0.62rem;color:#334155;margin-top:auto">'
            f'<span style="color:{c};font-weight:600">HMS:</span> {atk["hospital_impact"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        btn_label = "STOP" if is_running else "LAUNCH"
        if col.button(btn_label, key=f"real_{key}", type="primary", use_container_width=True):
            real_action = ("stop" if is_running else "launch", key)

    stop_col, _ = st.columns([1, 3])
    if stop_col.button("STOP ALL REAL ATTACKS + RESTORE", key="real_stop_all", use_container_width=True):
        real_action = ("stop_all", None)

    if real_action is not None:
        action, rkey = real_action
        if action == "launch":
            with st.spinner(f"Launching REAL {rkey.upper()} attack on MediCore..."):
                if rkey == "dos":
                    res = _real_eng.launch_dos()
                    summary = [
                        f"Target: localhost:{_real_eng.HOSPITAL_PORT}",
                        f"Threads: {res.get('threads', 0)} concurrent TCP connections",
                        f"Duration: {res.get('duration_sec', 0)}s",
                        "Effect: MediCore dashboard pages timeout / refuse connections",
                    ]
                elif rkey == "cpu":
                    res = _real_eng.launch_cpu_stress()
                    summary = [
                        f"Cores stressed: {res.get('cores_stressed', 0)}",
                        f"Duration: {res.get('duration_sec', 0)}s",
                        "Effect: System sluggish — check Task Manager CPU usage",
                    ]
                elif rkey == "tamper":
                    res = _real_eng.launch_tamper()
                    ch = res.get("changes", {})
                    if "error" in res:
                        summary = [
                            f"ERROR: {res['error']}",
                            "Make sure MediCore HMS is running so hospital.db exists, then retry.",
                        ]
                    else:
                        summary = [
                            f"IoT devices set OFFLINE/CORRUPTED: {ch.get('iot_offline', 0)}",
                            f"Patients set COMPROMISED: {ch.get('patients_compromised', 0)}",
                            f"Billing entries VOIDED: {ch.get('billing_voided', 0)}",
                            f"Beds set contaminated: {ch.get('beds_contaminated', 0)}",
                            f"Triage escalated to critical: {ch.get('triage_critical', 0)}",
                            "Effect: Check MediCore IoMT Devices + Patient Registry pages",
                        ]
                elif rkey == "ransomware":
                    res = _real_eng.launch_ransomware()
                    if "error" in res:
                        summary = [
                            f"ERROR: {res['error']}",
                            "Make sure MediCore outputs/ folder exists, then retry.",
                        ]
                    else:
                        summary = [
                            f"Files corrupted: {len(res.get('files_corrupted', []))} CSV/JSON files",
                            f"Backup saved at: {res.get('backup_dir', '—')}",
                            "Effect: Reload MediCore — charts blank, KPI errors, pandas read failures",
                        ]
                elif rkey == "spoof":
                    res = _real_eng.launch_spoof()
                    if "error" in res:
                        summary = [
                            f"ERROR: {res['error']}",
                            "Make sure MediCore HMS is running so hospital.db exists, then retry.",
                        ]
                    else:
                        summary = [
                            f"Rogue devices injected: {res.get('rogue_devices_injected', 0)} (ROGUE001–ROGUE015)",
                            "All rogue devices: criticality=critical, firmware=UNKNOWN_ROGUE_v0.0",
                            "Effect: Check MediCore IoMT Devices page — 15 unknown devices visible",
                        ]
                elif rkey == "replay":
                    res = _real_eng.launch_replay()
                    if "error" in res:
                        summary = [
                            f"ERROR: {res['error']}",
                            "Make sure MediCore HMS is running so hospital.db exists, then retry.",
                        ]
                    else:
                        summary = [
                            f"Duration: {res.get('duration_sec', 0)}s — inserting duplicate triage every 1.5s",
                            "Each entry tagged [REPLAY] in chief_complaint",
                            "Effect: MediCore Emergency page triage queue grows rapidly",
                        ]
                else:
                    res = {}
                    summary = ["Unknown attack"]
            # Store launch result in session state so it persists until next action
            log = st.session_state.setdefault("real_attack_log", {})
            failed = "error" in res
            log[rkey] = {
                "status": "FAILED" if failed else "ACTIVE",
                "launched_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "raw": res,
            }
            # Write shared active-attacks status for IDS bridge to read
            _write_active_status()
            st.rerun()

        elif action == "stop":
            with st.spinner(f"Stopping real {rkey.upper()}..."):
                if rkey == "dos":
                    _real_eng.stop_dos(); restore = {"restored": True}
                elif rkey == "cpu":
                    _real_eng.stop_cpu(); restore = {"restored": True}
                elif rkey == "tamper":
                    restore = _real_eng.stop_tamper()
                elif rkey == "ransomware":
                    restore = _real_eng.stop_ransomware()
                elif rkey == "spoof":
                    restore = _real_eng.stop_spoof()
                elif rkey == "replay":
                    restore = _real_eng.stop_replay()
                else:
                    restore = {}
            log = st.session_state.setdefault("real_attack_log", {})
            if rkey in log:
                log[rkey]["status"] = "STOPPED -- RESTORED" if restore.get("restored") else "STOPPED"
                log[rkey]["stopped_at"] = datetime.now(timezone.utc).isoformat()
                log[rkey]["restore"] = restore
            _write_active_status()
            st.rerun()

        elif action == "stop_all":
            with st.spinner("Stopping all real attacks and restoring hospital system..."):
                results = _real_eng.stop_all()
            log = st.session_state.setdefault("real_attack_log", {})
            for k in list(log.keys()):
                log[k]["status"] = "STOPPED -- RESTORED"
                log[k]["stopped_at"] = datetime.now(timezone.utc).isoformat()
            _write_active_status()
            st.rerun()

    # ── Real Attack Impact Log ─────────────────────────────────────────────
    real_log = st.session_state.get("real_attack_log", {})
    if real_log:
        st.markdown('<div class="section-label">> REAL ATTACK IMPACT — CHANGES MADE TO MEDICORE SYSTEM</div>', unsafe_allow_html=True)
        for atk_key, entry in real_log.items():
            status = entry.get("status", "")
            launched = entry.get("launched_at", "")[:16].replace("T", " ")
            stopped  = entry.get("stopped_at", "")[:16].replace("T", " ") if entry.get("stopped_at") else "—"
            is_active = "ACTIVE" in status
            is_failed = "FAILED" in status
            s_color   = "#ef4444" if is_active else ("#f97316" if is_failed else "#22c55e")
            s_bg      = "#1a0000" if is_active else ("#1a0800" if is_failed else "#001500")
            s_border  = "#ef444440" if is_active else ("#f9731640" if is_failed else "#22c55e40")

            summary_items = "".join(
                f'<li style="font-size:0.68rem;color:#4a8a4a;margin-bottom:3px">{item}</li>'
                for item in entry.get("summary", [])
            )
            restore_info = ""
            if entry.get("restore"):
                r = entry["restore"]
                if r.get("restored"):
                    restore_info = '<span style="color:#22c55e;font-size:0.66rem"> System restored from backup</span>'
                elif r.get("error"):
                    restore_info = f'<span style="color:#ef4444;font-size:0.66rem"> Restore error: {r["error"]}</span>'

            st.markdown(
                f'<div style="background:{s_bg};border:1px solid {s_border};border-left:3px solid {s_color};'
                f'border-radius:4px;padding:10px 14px;margin-bottom:8px;font-family:\'Share Tech Mono\',monospace">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
                f'<span style="font-size:0.78rem;font-weight:700;color:{s_color}">{atk_key.upper()}</span>'
                f'<span style="font-size:0.66rem;color:#334155">launched {launched} &nbsp;|&nbsp; '
                f'stopped {stopped}{restore_info}</span>'
                f'<span style="background:{s_color}22;color:{s_color};border:1px solid {s_color}44;'
                f'padding:2px 8px;border-radius:3px;font-size:0.63rem;font-weight:700">{status}</span>'
                f'</div>'
                f'<ul style="margin:0;padding-left:16px">{summary_items}</ul>'
                f'</div>',
                unsafe_allow_html=True,
            )

        cl1, cl2 = st.columns([1, 3])
        if cl1.button("Clear Impact Log", key="real_clear_log", use_container_width=True):
            st.session_state.pop("real_attack_log", None)
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Impact panel ──────────────────────────────────────────────────────
    imp = st.session_state.get("last_impact") or load_attack_impact()
    if imp:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">> HOSPITAL IMPACT — LAST ATTACK</div>', unsafe_allow_html=True)

        d  = imp.get("delta", {})
        ai = imp.get("attack_injection", {})
        inj   = ai.get("total_attacks_injected", 0)
        sla_d = d.get("sla_breach_rate", 0.0)
        lat_d = d.get("avg_latency_ms", 0.0)
        flg_d = d.get("security_flagged_events", 0)
        brk   = ai.get("attack_breakdown", {})

        c1, c2, c3, c4 = st.columns(4)
        for col, val, lbl, cls in [
            (c1, f"{inj:,}",        "Events Compromised",   "bad" if inj > 0 else "good"),
            (c2, f"{sla_d:+.1%}",   "SLA Breach Change",    "bad" if sla_d > 0 else "good"),
            (c3, f"{lat_d:+.0f}ms", "Latency Change",       "bad" if lat_d > 0 else "good"),
            (c4, f"{flg_d:+,}",     "New Security Flags",   "bad" if flg_d > 0 else "neu"),
        ]:
            col.markdown(
                f'<div class="imp-card"><div class="imp-val {cls}">{val}</div>'
                f'<div class="imp-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

        if brk:
            tags = " &nbsp; ".join(
                f'<span style="font-family:\'Share Tech Mono\',monospace;'
                f'background:{ATTACKS.get(k,{}).get("color","#64748b")}18;'
                f'color:{ATTACKS.get(k,{}).get("color","#64748b")};'
                f'border:1px solid {ATTACKS.get(k,{}).get("color","#64748b")}30;'
                f'padding:2px 10px;border-radius:3px;font-size:0.7rem;font-weight:700">'
                f'{k.upper()}: {v:,}</span>'
                for k, v in brk.items()
            )
            st.markdown(f'<div style="margin-top:10px">{tags}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        undo_col, _ = st.columns([1, 2])
        if undo_col.button(
            "↩  UNDO ATTACK — RESTORE HOSPITAL TO PRE-ATTACK STATE",
            key="btn_undo_attack",
            use_container_width=True,
        ):
            with st.spinner("Restoring hospital to pre-attack state..."):
                ok = undo_last_attack()
            if ok:
                st.session_state.pop("last_impact", None)
                _append_history({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "scenario": "UNDO_ATTACK", "attacks": [], "intensities": {},
                    "sla_delta": 0.0, "latency_delta": 0.0,
                    "flagged_delta": 0, "injected": 0, "breakdown": {},
                })
                st.success("Hospital fully restored -- pre-attack event data recovered, impact report cleared.")
            else:
                st.error("No pre-attack baseline found. Launch an attack first to create a restore point.")
            st.rerun()

    # ── Live event stream ──────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">> LIVE HOSPITAL EVENT STREAM — AUTO REFRESH EVERY 3s</div>', unsafe_allow_html=True)
    _live_event_stream()


# ── Page: Attack Log ──────────────────────────────────────────────────────────

def page_log() -> None:
    st.markdown(
        '<div class="term-header">'
        '<div class="term-title">[ ATTACK LOG ]</div>'
        '<div class="term-sub">> ALL ATTACKS LAUNCHED AGAINST MEDICORE HOSPITAL — NEWEST FIRST</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    history = _load_history()
    if not history:
        st.markdown(
            '<div style="font-family:\'Share Tech Mono\',monospace;color:#2d5a2d;'
            'padding:40px 0;text-align:center">'
            '> NO ATTACKS IN LOG — LAUNCH AN ATTACK FROM THE CONSOLE'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Summary KPIs
    n_attacks  = sum(1 for h in history if h.get("attacks"))
    n_resets   = sum(1 for h in history if not h.get("attacks"))
    n_injected = sum(h.get("injected", 0) for h in history)
    worst_sla  = max((h.get("sla_delta", 0) for h in history), default=0.0)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl, cls in [
        (c1, n_attacks,           "Attacks Launched",      "bad" if n_attacks > 0 else "neu"),
        (c2, n_resets,            "Resets Performed",      "good"),
        (c3, f"{n_injected:,}",   "Total Events Hit",      "bad" if n_injected > 0 else "neu"),
        (c4, f"{worst_sla:+.1%}", "Worst SLA Breach",      "bad" if worst_sla > 0.05 else "neu"),
    ]:
        col.markdown(
            f'<div class="imp-card"><div class="imp-val {cls}">{val}</div>'
            f'<div class="imp-lbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Hospital State Timeline ────────────────────────────────────────────
    st.markdown('<div class="section-label">> HOSPITAL STATE TIMELINE — WHEN WAS IT NORMAL?</div>', unsafe_allow_html=True)
    timeline_html = ""
    for h in history:  # already newest-first
        ts_str   = h["ts"][:16].replace("T", " ")
        is_atk   = bool(h.get("attacks"))
        scenario = h.get("scenario", "").upper()
        inj      = h.get("injected", 0)
        sla_d    = h.get("sla_delta", 0.0)
        lat_d    = h.get("latency_delta", 0.0)

        if is_atk:
            atk_icons = " · ".join(
                f'{ATTACKS.get(k, {}).get("icon", "")} {k.upper()}'
                for k in h.get("attacks", [])
            )
            bg, border, lbl_col = "#1a0000", "#ef444440", "#ef4444"
            label  = "ATTACK"
            detail = f'{atk_icons} &nbsp;|&nbsp; {inj:,} events &nbsp;|&nbsp; SLA {sla_d:+.1%} &nbsp;|&nbsp; Latency {lat_d:+.0f}ms'
        else:
            bg, border, lbl_col = "#001500", "#22c55e40", "#22c55e"
            label  = "NORMAL"
            detail = "hospital reset — clean state restored"

        timeline_html += (
            f'<div style="display:flex;align-items:center;gap:14px;padding:7px 12px;'
            f'background:{bg};border:1px solid {border};border-radius:4px;margin-bottom:4px">'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.67rem;'
            f'color:#334155;min-width:96px">{ts_str}</span>'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.73rem;'
            f'font-weight:700;color:{lbl_col};min-width:80px">{label}</span>'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.72rem;'
            f'color:#475569;flex:1">{scenario}</span>'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:0.67rem;'
            f'color:#334155;text-align:right">{detail}</span>'
            f'</div>'
        )
    st.markdown(timeline_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Actions: retrieve attack events + reset ────────────────────────────
    st.markdown('<div class="section-label">> ACTIONS</div>', unsafe_allow_html=True)
    ac1, ac2 = st.columns(2)
    if ac1.button("RETRIEVE ALL ATTACK EVENTS FROM HOSPITAL", use_container_width=True):
        st.session_state["show_atk_events"] = not st.session_state.get("show_atk_events", False)
    if ac2.button("RESET HOSPITAL TO NORMAL", type="primary", use_container_width=True):
        with st.spinner("Resetting hospital to clean state..."):
            _do_reset()
        st.success("Hospital reset -- all attacks cleared, clean state restored")
        st.rerun()

    if st.session_state.get("show_atk_events", False):
        if EVENTS_CSV.exists():
            ev_all = pd.read_csv(EVENTS_CSV)
            if "attack_active" in ev_all.columns:
                atk_ev = ev_all[ev_all["attack_active"] == 1].copy()
            else:
                atk_ev = ev_all.iloc[0:0]
            cols_show = [c for c in [
                "event_id", "department", "device_type", "latency_ms", "cpu_pct",
                "attack_type", "attack_intensity", "command_risk", "security_flag", "sla_breached",
            ] if c in atk_ev.columns]
            st.markdown(
                f'<div class="section-label">> {len(atk_ev):,} ATTACK EVENTS RETRIEVED FROM HOSPITAL</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_term_table(atk_ev[cols_show], highlight_col="attack_type"), unsafe_allow_html=True)
            csv_bytes = atk_ev[cols_show].to_csv(index=False).encode()
            st.download_button(
                "⬇  Download Attack Events CSV", csv_bytes,
                "hospital_attack_events.csv", "text/csv", use_container_width=True,
            )
        else:
            st.markdown(
                '<span style="font-family:\'Share Tech Mono\',monospace;color:#2d5a2d;font-size:0.78rem">'
                '> NO HOSPITAL EVENT DATA — LAUNCH AN ATTACK FIRST</span>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Before / After chart (last attack only) ────────────────────────────
    impact = load_attack_impact()
    if impact and impact.get("before") and impact.get("after"):
        st.markdown('<div class="section-label">> BEFORE vs AFTER — LAST ATTACK ON HOSPITAL</div>', unsafe_allow_html=True)

        bef     = impact["before"]["executive"]
        aft     = impact["after"]["executive"]
        bef_sec = impact["before"]["security_readiness"]
        aft_sec = impact["after"]["security_readiness"]

        labels = ["SLA Breach %", "Avg Latency (ms)", "Security Flags", "High-Risk Devices"]
        before_v = [
            bef.get("sla_breach_rate", 0) * 100,
            bef.get("avg_latency_ms", 0),
            bef_sec.get("security_flagged_events", 0),
            bef_sec.get("high_risk_devices", 0),
        ]
        after_v = [
            aft.get("sla_breach_rate", 0) * 100,
            aft.get("avg_latency_ms", 0),
            aft_sec.get("security_flagged_events", 0),
            aft_sec.get("high_risk_devices", 0),
        ]

        fig = go.Figure()
        fig.add_bar(name="Before Attack", x=labels, y=before_v, marker_color="#22c55e", opacity=0.85)
        fig.add_bar(name="After Attack",  x=labels, y=after_v,  marker_color="#ef4444", opacity=0.85)
        fig.update_layout(
            barmode="group", template="plotly_dark",
            paper_bgcolor="#0c0c0c", plot_bgcolor="#080808",
            font=dict(family="Share Tech Mono, monospace", color="#22c55e", size=11),
            title=dict(text="Hospital Metrics: Before vs After Attack", font=dict(color="#00ff41")),
            height=300, margin=dict(t=44, b=20, l=10, r=10),
            legend=dict(orientation="h", y=-0.22, xanchor="center", x=0.5),
            xaxis=dict(gridcolor="#1a3a1a"),
            yaxis=dict(gridcolor="#1a3a1a"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── SLA/Latency timeline (all history) ────────────────────────────────
    if len(history) > 1:
        st.markdown('<div class="section-label">> SLA BREACH CHANGE OVER ALL ATTACKS</div>', unsafe_allow_html=True)
        chrono = list(reversed(history))
        times  = [h["ts"][:16].replace("T", " ") for h in chrono]
        sla_v  = [round(h.get("sla_delta", 0) * 100, 2) for h in chrono]
        lat_v  = [round(h.get("latency_delta", 0), 1) for h in chrono]

        fig2 = go.Figure()
        fig2.add_bar(x=times, y=sla_v, name="SLA Δ (%)", marker_color="#ef4444")
        fig2.add_scatter(x=times, y=lat_v, name="Latency Δ (ms)",
                         mode="lines+markers", line=dict(color="#f59e0b", width=2),
                         yaxis="y2")
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0c0c0c", plot_bgcolor="#080808",
            font=dict(family="Share Tech Mono, monospace", color="#22c55e", size=11),
            title=dict(text="Attack Impact Timeline", font=dict(color="#00ff41")),
            height=250, margin=dict(t=44, b=30, l=10, r=60),
            legend=dict(orientation="h", y=-0.3, xanchor="center", x=0.5),
            xaxis=dict(gridcolor="#1a3a1a"),
            yaxis=dict(
                title=dict(text="SLA Δ (%)", font=dict(color="#ef4444")),
                gridcolor="#1a3a1a",
            ),
            yaxis2=dict(
                title=dict(text="Latency Δ (ms)", font=dict(color="#f59e0b")),
                overlaying="y",
                side="right",
                gridcolor="#1a3a1a",
            ),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Full log table ─────────────────────────────────────────────────────
    st.markdown('<div class="section-label">> FULL EVENT LOG</div>', unsafe_allow_html=True)
    rows = []
    for h in history:
        atk_str = ", ".join(h.get("attacks", [])).upper() or "RESET"
        rows.append({
            "Time":      h["ts"][:19].replace("T", " "),
            "Scenario":  h.get("scenario", "—").upper(),
            "Attacks":   atk_str,
            "Injected":  h.get("injected", 0),
            "SLA Δ":     f"{h.get('sla_delta', 0):+.2%}",
            "Latency Δ": f"{h.get('latency_delta', 0):+.1f}ms",
            "Flags Δ":   f"{h.get('flagged_delta', 0):+,}",
        })
    st.markdown(_term_table(pd.DataFrame(rows)), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Clear Attack Log"):
        if HIST_PATH.exists():
            HIST_PATH.unlink()
        st.success("Log cleared.")
        st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────

PAGES = {
    "Attack Console": page_console,
    "Attack Log":     page_log,
}


def main() -> None:
    st.set_page_config(
        page_title="IoMT Attack Lab",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(
            """
<div style="padding:14px 12px 6px 12px">
  <div style="font-family:'Share Tech Mono',monospace;font-size:1.05rem;
  font-weight:700;color:#00ff41;letter-spacing:0.08em">ATTACK LAB</div>
  <div style="font-family:'Share Tech Mono',monospace;font-size:0.66rem;
  color:#1a3a1a;margin-top:3px;letter-spacing:0.04em">IoMT CYBER RANGE v1.0</div>
</div>
<div style="border-top:1px solid #1a3a1a;margin:4px 0 10px 0"></div>
""",
            unsafe_allow_html=True,
        )
        page = st.radio("", list(PAGES.keys()), key="nav", label_visibility="collapsed")

        hist = _load_history()
        n_atk = sum(1 for h in hist if h.get("attacks"))
        imp2  = load_attack_impact()
        sla_now = imp2.get("delta", {}).get("sla_breach_rate", 0.0) if imp2 else 0.0
        sla_col = "#ef4444" if sla_now > 0.05 else "#1a3a1a"

        st.markdown(
            f"""
<div style="border-top:1px solid #1a3a1a;margin-top:24px;padding:12px 12px 6px 12px">
  <div style="font-family:'Share Tech Mono',monospace;font-size:0.67rem;
  color:#1a3a1a;line-height:2.0">
    <span style="color:{sla_col}">■</span> SLA_BREACH: {sla_now:+.1%}<br>
    <span style="color:#1a3a1a">■</span> LOG_ENTRIES: {n_atk}<br>
    <span style="color:#1a3a1a">■</span> TARGET: MEDICORE_HMS
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    PAGES[page]()


if __name__ == "__main__":
    main()
