"""MediCore IoMT — Device Monitoring Dashboard
Run: streamlit run hospital/app.py --server.port 8502
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
OUT = ROOT / "outputs"
DB_PATH = str(OUT / "hospital.db")
IDS_RESULTS = OUT / "ids_detection_results.json"

sys.path.insert(0, str(PROJECT))
from hospital.db import (
    DEPARTMENTS, DEVICE_TYPES, init_db, seed_devices,
    get_devices, get_device_counts, get_dept_device_summary,
    generate_vitals, get_live_vitals,
)

# ── Theme ─────────────────────────────────────────────────────────────────────
BG       = "#0c1222"
CARD_BG  = "#111a2e"
BORDER   = "#1c2d4a"
TEXT     = "#c8d6e5"
HEADING  = "#e8edf3"
ACCENT   = "#2563eb"     # blue
GREEN    = "#22c55e"
RED      = "#ef4444"
AMBER    = "#f59e0b"
CYAN     = "#06b6d4"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
.stApp {{ background-color: {BG} !important; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

[data-testid="stSidebar"]   {{ background-color: #080e1a !important; border-right: 1px solid {BORDER} !important; }}
[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stToolbar"]   {{ display: none !important; }}
[data-testid="stHeader"]    {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
footer    {{ display: none !important; }}

.hdr {{
    background: linear-gradient(135deg, #0a1628, #101d35);
    border: 1px solid {BORDER}; border-left: 4px solid {ACCENT};
    border-radius: 10px; padding: 14px 24px; margin-bottom: 16px;
    display: flex; align-items: center; justify-content: space-between;
}}
.hdr-title {{ font-size: 1.15rem; font-weight: 800; color: {HEADING}; }}
.hdr-sub   {{ font-size: 0.72rem; color: #64748b; margin-top: 2px; }}

.kpi {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 16px 18px; text-align: center;
}}
.kpi-val {{ font-size: 1.8rem; font-weight: 800; line-height: 1.1; }}
.kpi-lbl {{ font-size: 0.68rem; color: #64748b; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.06em; margin-top: 4px; }}

.card {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 16px; margin-bottom: 12px;
}}
.card-title {{
    font-size: 0.82rem; font-weight: 700; color: {HEADING};
    border-bottom: 2px solid {ACCENT}; padding-bottom: 6px; margin-bottom: 10px;
    text-transform: uppercase; letter-spacing: 0.04em;
}}
.status-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 5px; vertical-align: middle;
}}
.dot-green  {{ background: {GREEN}; }}
.dot-red    {{ background: {RED}; }}
.dot-amber  {{ background: {AMBER}; }}
.dot-cyan   {{ background: {CYAN}; }}

.pill {{
    display: inline-flex; align-items: center; gap: 4px;
    border-radius: 20px; padding: 3px 10px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.04em;
    text-transform: uppercase; margin-right: 4px;
}}
.pill-green  {{ background: rgba(34,197,94,0.12); color: {GREEN}; border: 1px solid rgba(34,197,94,0.3); }}
.pill-red    {{ background: rgba(239,68,68,0.12); color: {RED}; border: 1px solid rgba(239,68,68,0.3); }}
.pill-amber  {{ background: rgba(245,158,11,0.12); color: {AMBER}; border: 1px solid rgba(245,158,11,0.3); }}
.pill-cyan   {{ background: rgba(6,182,212,0.12); color: {CYAN}; border: 1px solid rgba(6,182,212,0.3); }}
.pill-blue   {{ background: rgba(37,99,235,0.12); color: {ACCENT}; border: 1px solid rgba(37,99,235,0.3); }}

.alert-banner {{
    border-left: 4px solid {RED}; background: rgba(239,68,68,0.08);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: #fca5a5;
}}
.info-banner {{
    border-left: 4px solid {ACCENT}; background: rgba(37,99,235,0.06);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: #93c5fd;
}}

[data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; }}
.stButton > button {{ border-radius: 8px !important; font-weight: 600 !important; font-size: 0.78rem !important; }}

div[data-testid="stMetricValue"]  {{ color: {HEADING} !important; }}
div[data-testid="stMetricLabel"]  {{ color: #64748b !important; }}
div[data-testid="stMetricDelta"]  {{ font-size: 0.72rem !important; }}
</style>
"""


def _plotly_dark() -> dict:
    return dict(
        template="plotly_dark",
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(family="Inter", color=TEXT, size=11),
    )


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def _bootstrap() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    init_db(str(OUT))
    seed_devices(DB_PATH, total_devices=200)


# ── Live vitals fragment (auto-refresh every 2s) ──────────────────────────────

@st.fragment(run_every=2)
def _live_vitals_fragment() -> None:
    prev = st.session_state.get("_vitals_state")
    df, new_states = generate_vitals(DB_PATH, prev_states=prev)
    st.session_state["_vitals_state"] = new_states
    st.session_state["_latest_vitals"] = df


# ── IDS alert reader ─────────────────────────────────────────────────────────

def _read_ids_alerts() -> dict | None:
    if IDS_RESULTS.exists():
        try:
            return json.loads(IDS_RESULTS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="MediCore IoMT",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    _bootstrap()

    # Header
    st.markdown(
        '<div class="hdr">'
        '  <div>'
        '    <div class="hdr-title">MediCore IoMT  |  Device Monitoring Center</div>'
        '    <div class="hdr-sub">Real-time IoMT device fleet management and telemetry monitoring</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Run live vitals in background
    _live_vitals_fragment()

    # ── IDS alert banner ──────────────────────────────────────────────────────
    ids_data = _read_ids_alerts()
    if ids_data and ids_data.get("anomaly_count", 0) > 0:
        attacks = ids_data.get("attack_label", "Unknown")
        count = ids_data["anomaly_count"]
        st.markdown(
            f'<div class="alert-banner">'
            f'SECURITY ALERT  |  MedGuard-IDS detected {count} compromised device(s)  |  '
            f'Attack: {attacks}</div>',
            unsafe_allow_html=True,
        )

    # ── KPI row ───────────────────────────────────────────────────────────────
    counts = get_device_counts(DB_PATH)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    kpis = [
        (c1, counts["total"],       "Total Devices",  ACCENT),
        (c2, counts["online"],      "Online",         GREEN),
        (c3, counts["offline"],     "Offline",        RED),
        (c4, counts["maintenance"], "Maintenance",    AMBER),
        (c5, counts["compromised"], "Compromised",    RED),
        (c6, counts["critical"],    "Critical-Class", CYAN),
    ]
    for col, val, lbl, color in kpis:
        with col:
            top_border = f"border-top: 3px solid {color};"
            st.markdown(
                f'<div class="kpi" style="{top_border}">'
                f'<div class="kpi-val" style="color:{color}">{val}</div>'
                f'<div class="kpi-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        # Device inventory table
        st.markdown('<div class="card"><div class="card-title">Device Inventory</div>', unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            dept_filter = st.selectbox("Department", ["all"] + DEPARTMENTS, key="dept_f")
        with fc2:
            status_filter = st.selectbox("Status", ["all", "online", "offline", "maintenance", "compromised"], key="stat_f")
        with fc3:
            type_filter = st.selectbox("Device Type", ["all"] + sorted(DEVICE_TYPES.keys()), key="type_f")

        devs = get_devices(DB_PATH, department=dept_filter, status=status_filter)
        if type_filter != "all":
            devs = devs[devs["device_type"] == type_filter]

        if not devs.empty:
            display_cols = ["device_id", "device_type", "department", "criticality",
                           "manufacturer", "model_number", "status", "ip_address", "firmware_version"]
            show_cols = [c for c in display_cols if c in devs.columns]
            st.dataframe(devs[show_cols], use_container_width=True, hide_index=True, height=420)
        else:
            st.markdown('<div class="info-banner">No devices match the selected filters.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        # Department summary chart
        dept_df = get_dept_device_summary(DB_PATH)
        if not dept_df.empty:
            st.markdown('<div class="card"><div class="card-title">Devices by Department</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Online", x=dept_df["department"], y=dept_df["online"], marker_color=GREEN))
            fig.add_trace(go.Bar(name="Offline", x=dept_df["department"], y=dept_df["offline"], marker_color=RED))
            if "compromised" in dept_df.columns:
                fig.add_trace(go.Bar(name="Compromised", x=dept_df["department"], y=dept_df["compromised"], marker_color="#dc2626"))
            fig.update_layout(
                barmode="stack", height=280, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(tickangle=-45),
                **_plotly_dark(),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Device type distribution
        devs_all = get_devices(DB_PATH)
        if not devs_all.empty:
            st.markdown('<div class="card"><div class="card-title">Device Type Distribution</div>', unsafe_allow_html=True)
            type_counts = devs_all["device_type"].value_counts().head(12)
            fig2 = go.Figure(go.Bar(
                x=type_counts.values,
                y=type_counts.index,
                orientation="h",
                marker_color=ACCENT,
            ))
            fig2.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                **_plotly_dark(),
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Live telemetry section ────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">Live Telemetry Stream</div>', unsafe_allow_html=True)
    vitals = st.session_state.get("_latest_vitals", pd.DataFrame())
    if not vitals.empty:
        # Show risk flagged rows at top
        vitals_sorted = vitals.sort_values("risk_flag", ascending=False)
        display_v = vitals_sorted[[
            "device_id", "device_type", "department",
            "heart_rate", "spo2", "systolic_bp", "temperature_c",
            "glucose_mg_dl", "ecg_rhythm", "risk_flag",
        ]].head(50)
        st.dataframe(display_v, use_container_width=True, hide_index=True, height=300)
    else:
        st.markdown('<div class="info-banner">Generating initial telemetry data...</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Criticality breakdown ─────────────────────────────────────────────────
    if not devs_all.empty:
        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card"><div class="card-title">Criticality Distribution</div>', unsafe_allow_html=True)
            crit_counts = devs_all["criticality"].value_counts()
            colors_map = {"critical": RED, "high": AMBER, "medium": CYAN, "low": GREEN}
            fig3 = go.Figure(go.Pie(
                labels=crit_counts.index,
                values=crit_counts.values,
                marker=dict(colors=[colors_map.get(c, ACCENT) for c in crit_counts.index]),
                hole=0.45,
                textinfo="label+value",
                textfont=dict(size=11),
            ))
            fig3.update_layout(
                height=260, margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                **_plotly_dark(),
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card"><div class="card-title">Status Overview</div>', unsafe_allow_html=True)
            stat_counts = devs_all["status"].value_counts()
            s_colors = {"online": GREEN, "offline": RED, "maintenance": AMBER,
                       "compromised": "#dc2626", "error": "#dc2626", "corrupted": "#dc2626"}
            fig4 = go.Figure(go.Pie(
                labels=stat_counts.index,
                values=stat_counts.values,
                marker=dict(colors=[s_colors.get(s, ACCENT) for s in stat_counts.index]),
                hole=0.45,
                textinfo="label+value",
                textfont=dict(size=11),
            ))
            fig4.update_layout(
                height=260, margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                **_plotly_dark(),
            )
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown(
        f'<div style="text-align:center;color:#475569;font-size:0.65rem;margin-top:20px">'
        f'MediCore IoMT  |  {counts["total"]} devices across {len(DEPARTMENTS)} departments  |  '
        f'Last refresh: {datetime.now(timezone.utc).strftime("%H:%M:%S UTC")}'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
