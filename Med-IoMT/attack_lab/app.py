"""IoMT Attack Lab — Adversary Console
Run: streamlit run attack_lab/app.py --server.port 8503
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))

from attack_lab.engine import (
    active_attacks, stop_all,
    launch_dos, stop_dos,
    launch_tamper, stop_tamper,
    launch_spoof, stop_spoof,
    launch_ransomware, stop_ransomware,
    launch_replay, stop_replay,
    launch_mitm, stop_mitm,
    DB_PATH,
)

# ── Theme ─────────────────────────────────────────────────────────────────────
BG = "#0a0a0a"
CARD = "#111111"
BORDER = "#222222"
GREEN = "#22c55e"
RED = "#ef4444"
AMBER = "#f59e0b"
CYAN = "#06b6d4"
PURPLE = "#a78bfa"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
.stApp {{ background-color: {BG} !important; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

[data-testid="stSidebar"]   {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stToolbar"]   {{ display: none !important; }}
[data-testid="stHeader"]    {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
footer    {{ display: none !important; }}

.hdr {{
    background: linear-gradient(135deg, #1a0000, #2a0000);
    border: 1px solid #3a0000; border-left: 4px solid {RED};
    border-radius: 10px; padding: 14px 24px; margin-bottom: 16px;
}}
.hdr-title {{ font-size: 1.15rem; font-weight: 800; color: {RED}; font-family: 'JetBrains Mono', monospace !important; }}
.hdr-sub   {{ font-size: 0.72rem; color: #666; margin-top: 2px; }}

.atk-card {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 16px; margin-bottom: 10px;
    transition: border-color 0.2s;
}}
.atk-card:hover {{ border-color: #444; }}
.atk-card.active {{ border-color: {RED}; border-width: 2px; background: #1a0808; }}

.atk-name {{
    font-size: 0.88rem; font-weight: 700; color: #e0e0e0;
    font-family: 'JetBrains Mono', monospace !important;
}}
.atk-desc {{ font-size: 0.72rem; color: #888; margin-top: 4px; }}

.log-line {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem; color: {GREEN}; line-height: 1.6;
    padding: 2px 0;
}}
.log-err {{ color: {RED}; }}
.log-warn {{ color: {AMBER}; }}

.pill {{
    display: inline-flex; align-items: center; gap: 4px;
    border-radius: 20px; padding: 3px 10px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.pill-red    {{ background: rgba(239,68,68,0.15); color: {RED}; border: 1px solid rgba(239,68,68,0.3); }}
.pill-green  {{ background: rgba(34,197,94,0.15); color: {GREEN}; border: 1px solid rgba(34,197,94,0.3); }}
.pill-amber  {{ background: rgba(245,158,11,0.15); color: {AMBER}; border: 1px solid rgba(245,158,11,0.3); }}

.counter {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 2rem; font-weight: 800; color: {RED}; text-align: center;
}}
.counter-lbl {{
    font-size: 0.68rem; color: #666; text-align: center;
    text-transform: uppercase; letter-spacing: 0.06em;
}}

.stButton > button {{
    border-radius: 8px !important; font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}}
</style>
"""

ATTACKS = {
    "dos": {
        "name": "DoS FLOOD",
        "desc": "TCP connection flood against hospital port 8502. Overwhelms the server with 80 parallel threads. Knocks 40 devices offline.",
        "color": RED,
        "launch": launch_dos,
        "stop": stop_dos,
    },
    "tamper": {
        "name": "DATA TAMPER",
        "desc": "Corrupts device firmware versions and marks 60% of devices as compromised. Injects 50 falsified vital sign readings with dangerous values.",
        "color": PURPLE,
        "launch": launch_tamper,
        "stop": stop_tamper,
    },
    "spoof": {
        "name": "DEVICE SPOOF",
        "desc": "Injects 25 rogue devices into the hospital network with fake identities. All marked as critical-class with unknown firmware.",
        "color": AMBER,
        "launch": launch_spoof,
        "stop": stop_spoof,
    },
    "ransomware": {
        "name": "RANSOMWARE",
        "desc": "Encrypts all device data and locks the entire IoMT fleet. Corrupts output files. Simulates full hospital ransomware incident.",
        "color": "#dc2626",
        "launch": launch_ransomware,
        "stop": stop_ransomware,
    },
    "replay": {
        "name": "REPLAY ATTACK",
        "desc": "Continuously replays stale vital sign data with bradycardia and low SpO2 readings. Creates flood of false clinical alerts.",
        "color": CYAN,
        "launch": launch_replay,
        "stop": stop_replay,
    },
    "mitm": {
        "name": "MAN-IN-THE-MIDDLE",
        "desc": "Intercepts telemetry from critical devices and injects subtly altered readings. Designed to cause incorrect clinical decisions.",
        "color": "#f97316",
        "launch": launch_mitm,
        "stop": stop_mitm,
    },
}


def main() -> None:
    st.set_page_config(
        page_title="IoMT Attack Lab",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # Init session state
    if "_attack_log" not in st.session_state:
        st.session_state["_attack_log"] = []

    def _log(msg: str, level: str = "info") -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        st.session_state["_attack_log"].insert(0, (ts, msg, level))
        st.session_state["_attack_log"] = st.session_state["_attack_log"][:100]

    # Header
    st.markdown(
        '<div class="hdr">'
        '  <div>'
        '    <div class="hdr-title">ATTACK LAB  //  IoMT Adversary Console</div>'
        '    <div class="hdr-sub">Controlled cyberattack environment for MedGuard-IDS validation</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Check hospital DB
    db_ok = Path(DB_PATH).exists()
    if not db_ok:
        st.markdown(
            '<div style="background:#1a0808;border:1px solid #3a0000;border-radius:10px;padding:16px;'
            'color:#fca5a5;font-size:0.85rem">'
            'Hospital database not found. Start the hospital dashboard (port 8502) first.</div>',
            unsafe_allow_html=True,
        )
        return

    current = active_attacks()

    # Status bar
    if current:
        attacks_str = " | ".join(ATTACKS[a]["name"] for a in current if a in ATTACKS)
        st.markdown(
            f'<div style="background:#1a0808;border-left:4px solid {RED};padding:10px 16px;'
            f'border-radius:0 8px 8px 0;margin-bottom:12px;font-size:0.82rem;color:#fca5a5">'
            f'ATTACKS ACTIVE: {attacks_str}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#081a08;border-left:4px solid #22c55e;padding:10px 16px;'
            'border-radius:0 8px 8px 0;margin-bottom:12px;font-size:0.82rem;color:#86efac">'
            'System nominal. No active attacks.</div>',
            unsafe_allow_html=True,
        )

    # Counters
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="counter">{len(current)}</div><div class="counter-lbl">Active Attacks</div>', unsafe_allow_html=True)
    with c2:
        total_launched = sum(1 for _, _, l in st.session_state["_attack_log"] if l == "attack")
        st.markdown(f'<div class="counter" style="color:{AMBER}">{total_launched}</div><div class="counter-lbl">Total Launched</div>', unsafe_allow_html=True)
    with c3:
        total_stopped = sum(1 for _, _, l in st.session_state["_attack_log"] if l == "restore")
        st.markdown(f'<div class="counter" style="color:{GREEN}">{total_stopped}</div><div class="counter-lbl">Restored</div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Stop All button ───────────────────────────────────────────────────────
    if current:
        if st.button("STOP ALL ATTACKS", type="primary", use_container_width=True):
            results = stop_all()
            for k, v in results.items():
                _log(f"Stopped {k}: {v}", "restore")
            st.rerun()

    # ── Attack cards ──────────────────────────────────────────────────────────
    st.markdown("")

    cols = st.columns(3)
    for idx, (key, atk) in enumerate(ATTACKS.items()):
        is_active = key in current
        with cols[idx % 3]:
            card_class = "atk-card active" if is_active else "atk-card"
            st.markdown(
                f'<div class="{card_class}">'
                f'<div class="atk-name" style="color:{atk["color"]}">{atk["name"]}</div>'
                f'<div class="atk-desc">{atk["desc"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if is_active:
                if st.button(f"STOP {atk['name']}", key=f"stop_{key}", use_container_width=True):
                    result = atk["stop"]()
                    _log(f"Stopped {atk['name']}: {json.dumps(result, default=str)}", "restore")
                    st.rerun()
            else:
                if st.button(f"LAUNCH {atk['name']}", key=f"launch_{key}", use_container_width=True):
                    result = atk["launch"]()
                    _log(f"Launched {atk['name']}: {json.dumps(result, default=str)}", "attack")
                    st.rerun()

    # ── Attack log ────────────────────────────────────────────────────────────
    st.markdown("")
    st.markdown(
        '<div style="background:#111;border:1px solid #222;border-radius:10px;padding:16px">'
        '<div style="font-size:0.82rem;font-weight:700;color:#888;border-bottom:1px solid #222;'
        'padding-bottom:6px;margin-bottom:8px;font-family:JetBrains Mono,monospace;'
        'text-transform:uppercase;letter-spacing:0.06em">Attack Log</div>',
        unsafe_allow_html=True,
    )
    log = st.session_state.get("_attack_log", [])
    if log:
        lines = []
        for ts, msg, level in log[:30]:
            css_class = "log-err" if level == "attack" else ("log-line" if level == "restore" else "log-warn")
            prefix = ">>>" if level == "attack" else "<<<" if level == "restore" else "---"
            lines.append(f'<div class="log-line {css_class}">[{ts}] {prefix} {msg}</div>')
        st.markdown("\n".join(lines), unsafe_allow_html=True)
    else:
        st.markdown('<div class="log-line">Waiting for commands...</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
