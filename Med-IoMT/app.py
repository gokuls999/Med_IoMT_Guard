"""MedGuard-IDS — Unified Dashboard
Single Streamlit app combining Hospital IoMT, IDS Detection, and Attack Lab.
Run: streamlit run app.py
"""
from __future__ import annotations

import json
import random as _random
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Pickle compatibility: trained_model.pkl was saved when modules lived at root level.
# Register aliases so joblib/pickle can find them under the old names.
import core.stacking_model, core.preprocess, core.trust_engine, core.blockchain as _bc_mod
for _alias, _mod in [
    ("stacking_model", core.stacking_model),
    ("preprocess", core.preprocess),
    ("trust_engine", core.trust_engine),
    ("blockchain", _bc_mod),
]:
    sys.modules.setdefault(_alias, _mod)

from core.blockchain import LightweightBlockchain
from core.realtime_engine import RealtimeDetectionEngine
from core.stacking_model import load_trained_bundle
from core.trust_engine import TrustEngine
from hospital.db import (
    DEPARTMENTS, DEVICE_TYPES, init_db, seed_devices,
    get_devices, get_device_counts, get_dept_device_summary,
    generate_vitals, get_live_vitals,
)
from ids.bridge import db_exists, get_active_attacks, get_hospital_stream
from attack_lab.engine import (
    active_attacks as atk_active, stop_all as atk_stop_all,
    launch_dos, stop_dos, launch_tamper, stop_tamper,
    launch_spoof, stop_spoof, launch_ransomware, stop_ransomware,
    launch_replay, stop_replay, launch_mitm, stop_mitm,
    DB_PATH as ATK_DB_PATH,
)

MODEL_PATH   = ROOT / "trained_model.pkl"
HOSPITAL_OUT = ROOT / "hospital" / "outputs"
DB_PATH      = str(HOSPITAL_OUT / "hospital.db")
IDS_OUT_JSON = HOSPITAL_OUT / "ids_detection_results.json"

# ── Theme definitions ────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg": "#0c1222", "card": "#111a2e", "border": "#1c2d4a",
        "text": "#c8d6e5", "heading": "#e8edf3", "muted": "#64748b",
        "accent": "#2563eb", "green": "#22c55e", "red": "#ef4444",
        "amber": "#f59e0b", "cyan": "#06b6d4", "purple": "#a78bfa",
        "sidebar_bg": "#080e1a", "input_bg": "#0f172a",
        "table_bg": "#0f1729", "hover": "#1e293b",
    },
    "light": {
        "bg": "#f8fafc", "card": "#ffffff", "border": "#e2e8f0",
        "text": "#334155", "heading": "#0f172a", "muted": "#94a3b8",
        "accent": "#2563eb", "green": "#16a34a", "red": "#dc2626",
        "amber": "#d97706", "cyan": "#0891b2", "purple": "#7c3aed",
        "sidebar_bg": "#f1f5f9", "input_bg": "#f8fafc",
        "table_bg": "#ffffff", "hover": "#f1f5f9",
    },
}


def _t() -> dict:
    return THEMES[st.session_state.get("_theme", "dark")]


def _css() -> str:
    t = _t()
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
.stApp {{ background-color: {t["bg"]} !important; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

[data-testid="stSidebar"] {{
    background-color: {t["sidebar_bg"]} !important;
    border-right: 1px solid {t["border"]} !important;
}}
[data-testid="stSidebar"] * {{ color: {t["text"]} !important; }}
[data-testid="stToolbar"]   {{ display: none !important; }}
[data-testid="stHeader"]    {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
footer    {{ display: none !important; }}

.hdr {{
    background: {t["card"]};
    border: 1px solid {t["border"]}; border-left: 4px solid {t["accent"]};
    border-radius: 10px; padding: 14px 24px; margin-bottom: 16px;
    display: flex; align-items: center; justify-content: space-between;
}}
.hdr-red {{ border-left-color: {t["red"]} !important; }}
.hdr-title {{ font-size: 1.15rem; font-weight: 800; color: {t["heading"]}; }}
.hdr-title-red {{ font-size: 1.15rem; font-weight: 800; color: {t["red"]};
    font-family: 'JetBrains Mono', monospace !important; }}
.hdr-sub {{ font-size: 0.72rem; color: {t["muted"]}; margin-top: 2px; }}

.kpi {{
    background: {t["card"]}; border: 1px solid {t["border"]};
    border-radius: 10px; padding: 16px 18px; text-align: center;
}}
.kpi-val {{ font-size: 1.8rem; font-weight: 800; line-height: 1.1; }}
.kpi-lbl {{ font-size: 0.68rem; color: {t["muted"]}; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.06em; margin-top: 4px; }}

.card {{
    background: {t["card"]}; border: 1px solid {t["border"]};
    border-radius: 10px; padding: 16px; margin-bottom: 12px;
}}
.card-title {{
    font-size: 0.82rem; font-weight: 700; color: {t["heading"]};
    border-bottom: 2px solid {t["accent"]}; padding-bottom: 6px; margin-bottom: 10px;
    text-transform: uppercase; letter-spacing: 0.04em;
}}

.pill {{
    display: inline-flex; align-items: center; gap: 4px;
    border-radius: 20px; padding: 3px 10px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.04em;
    text-transform: uppercase; margin-right: 4px;
}}
.pill-green  {{ background: rgba(34,197,94,0.12); color: {t["green"]}; border: 1px solid rgba(34,197,94,0.3); }}
.pill-red    {{ background: rgba(239,68,68,0.12); color: {t["red"]}; border: 1px solid rgba(239,68,68,0.3); }}
.pill-amber  {{ background: rgba(245,158,11,0.12); color: {t["amber"]}; border: 1px solid rgba(245,158,11,0.3); }}
.pill-cyan   {{ background: rgba(6,182,212,0.12); color: {t["cyan"]}; border: 1px solid rgba(6,182,212,0.3); }}
.pill-blue   {{ background: rgba(37,99,235,0.12); color: {t["accent"]}; border: 1px solid rgba(37,99,235,0.3); }}

.dot {{ width: 6px; height: 6px; border-radius: 50%; display: inline-block; }}
.dot-g {{ background: {t["green"]}; }} .dot-r {{ background: {t["red"]}; }}
.dot-c {{ background: {t["cyan"]}; }} .dot-y {{ background: {t["amber"]}; }}

.alert-banner {{
    border-left: 4px solid {t["red"]}; background: rgba(239,68,68,0.08);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: {t["red"]};
}}
.ok-banner {{
    border-left: 4px solid {t["green"]}; background: rgba(34,197,94,0.08);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: {t["green"]};
}}
.info-banner {{
    border-left: 4px solid {t["accent"]}; background: rgba(37,99,235,0.06);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: {t["accent"]};
}}
.idle-banner {{
    border-left: 4px solid {t["cyan"]}; background: rgba(6,182,212,0.06);
    padding: 10px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
    font-size: 0.82rem; color: {t["cyan"]};
}}

.tbl-label {{
    font-size: 0.7rem; font-weight: 700; color: {t["muted"]};
    text-transform: uppercase; letter-spacing: 0.06em; margin: 12px 0 5px 0;
}}

.atk-card {{
    background: {t["card"]}; border: 1px solid {t["border"]};
    border-radius: 10px; padding: 16px; margin-bottom: 10px;
    transition: border-color 0.2s;
}}
.atk-card.active {{ border-color: {t["red"]}; border-width: 2px; }}
.atk-name {{
    font-size: 0.88rem; font-weight: 700; color: {t["heading"]};
    font-family: 'JetBrains Mono', monospace !important;
}}
.atk-desc {{ font-size: 0.72rem; color: {t["muted"]}; margin-top: 4px; }}

.log-line {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem; color: {t["green"]}; line-height: 1.6; padding: 2px 0;
}}
.log-err {{ color: {t["red"]}; }}
.log-warn {{ color: {t["amber"]}; }}

.counter {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 2rem; font-weight: 800; color: {t["red"]}; text-align: center;
}}
.counter-lbl {{
    font-size: 0.68rem; color: {t["muted"]}; text-align: center;
    text-transform: uppercase; letter-spacing: 0.06em;
}}

.live-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px; animation: pulse-dot 1.5s ease-in-out infinite;
}}
@keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
}}

[data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; }}
.stButton > button {{ border-radius: 8px !important; font-weight: 600 !important; font-size: 0.78rem !important; }}
</style>
"""


def _plotly_theme() -> dict:
    t = _t()
    return dict(
        template="plotly_dark" if st.session_state.get("_theme", "dark") == "dark" else "plotly_white",
        paper_bgcolor=t["card"],
        plot_bgcolor=t["card"],
        font=dict(family="Inter", color=t["text"], size=11),
    )


# ── Bootstrap ────────────────────────────────────────────────────────────────

def _bootstrap() -> None:
    HOSPITAL_OUT.mkdir(parents=True, exist_ok=True)
    init_db(str(HOSPITAL_OUT))
    seed_devices(DB_PATH, total_devices=200)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1: Hospital IoMT Dashboard
# ═════════════════════════════════════════════════════════════════════════════

def _refresh_vitals() -> None:
    """Generate new vitals and store in session state (called from within fragments)."""
    prev = st.session_state.get("_vitals_state")
    df, new_states = generate_vitals(DB_PATH, prev_states=prev)
    st.session_state["_vitals_state"] = new_states
    st.session_state["_latest_vitals"] = df


def _read_ids_alerts() -> dict | None:
    if IDS_OUT_JSON.exists():
        try:
            return json.loads(IDS_OUT_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def page_hospital() -> None:
    t = _t()

    st.markdown(
        '<div class="hdr"><div>'
        '<div class="hdr-title">MediCore IoMT  |  Device Monitoring Center</div>'
        '<div class="hdr-sub">Real-time IoMT device fleet management and telemetry monitoring</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    _hospital_live_fragment()


@st.fragment(run_every=3)
def _hospital_live_fragment() -> None:
    """Auto-refreshing fragment that covers ALL hospital content — KPIs, vitals, charts."""
    t = _t()

    _refresh_vitals()

    # IDS alert banner
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

    # KPI row
    counts = get_device_counts(DB_PATH)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    kpis = [
        (c1, counts["total"],       "Total Devices",  t["accent"]),
        (c2, counts["online"],      "Online",         t["green"]),
        (c3, counts["offline"],     "Offline",        t["red"]),
        (c4, counts["maintenance"], "Maintenance",    t["amber"]),
        (c5, counts["compromised"], "Compromised",    t["red"]),
        (c6, counts["critical"],    "Critical-Class", t["cyan"]),
    ]
    for col, val, lbl, color in kpis:
        with col:
            st.markdown(
                f'<div class="kpi" style="border-top:3px solid {color}">'
                f'<div class="kpi-val" style="color:{color}">{val}</div>'
                f'<div class="kpi-lbl">{lbl}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # ── Live IoMT Device Monitor (top section — most prominent) ──────────────
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title">'
        f'<span class="live-dot" style="background:{t["green"]}"></span>'
        f'Live IoMT Device Monitor  —  Real-Time Telemetry Stream</div>',
        unsafe_allow_html=True,
    )

    vitals = st.session_state.get("_latest_vitals", pd.DataFrame())
    if not vitals.empty:
        risk_count = int(vitals["risk_flag"].sum()) if "risk_flag" in vitals.columns else 0
        total_streaming = len(vitals)
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f'<div class="kpi" style="border-top:2px solid {t["green"]};padding:10px">'
                f'<div class="kpi-val" style="font-size:1.3rem;color:{t["green"]}">{total_streaming}</div>'
                f'<div class="kpi-lbl">Streaming Devices</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div class="kpi" style="border-top:2px solid {t["red"]};padding:10px">'
                f'<div class="kpi-val" style="font-size:1.3rem;color:{t["red"]}">{risk_count}</div>'
                f'<div class="kpi-lbl">Risk Flagged</div></div>',
                unsafe_allow_html=True,
            )
        with m3:
            avg_hr = vitals["heart_rate"].mean() if "heart_rate" in vitals.columns else 0
            st.markdown(
                f'<div class="kpi" style="border-top:2px solid {t["cyan"]};padding:10px">'
                f'<div class="kpi-val" style="font-size:1.3rem;color:{t["cyan"]}">{avg_hr:.0f}</div>'
                f'<div class="kpi-lbl">Avg Heart Rate</div></div>',
                unsafe_allow_html=True,
            )
        with m4:
            avg_spo2 = vitals["spo2"].mean() if "spo2" in vitals.columns else 0
            st.markdown(
                f'<div class="kpi" style="border-top:2px solid {t["amber"]};padding:10px">'
                f'<div class="kpi-val" style="font-size:1.3rem;color:{t["amber"]}">{avg_spo2:.1f}%</div>'
                f'<div class="kpi-lbl">Avg SpO2</div></div>',
                unsafe_allow_html=True,
            )

        vitals_sorted = vitals.sort_values("risk_flag", ascending=False)
        display_v = vitals_sorted[[
            c for c in ["device_id", "device_type", "department",
                        "heart_rate", "spo2", "systolic_bp", "temperature_c",
                        "glucose_mg_dl", "ecg_rhythm", "risk_flag"]
            if c in vitals_sorted.columns
        ]].head(60)
        st.dataframe(display_v, use_container_width=True, hide_index=True, height=350)
    else:
        st.markdown('<div class="info-banner">Generating initial telemetry data... refresh in 2 seconds.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")

    # Two-column layout: Device Inventory + Charts
    left, right = st.columns([3, 2])

    with left:
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
            show_cols = [c for c in ["device_id", "device_type", "department", "criticality",
                                     "manufacturer", "model_number", "status", "ip_address", "firmware_version"]
                        if c in devs.columns]
            st.dataframe(devs[show_cols], use_container_width=True, hide_index=True, height=420)
        else:
            st.markdown('<div class="info-banner">No devices match the selected filters.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        dept_df = get_dept_device_summary(DB_PATH)
        if not dept_df.empty:
            st.markdown('<div class="card"><div class="card-title">Devices by Department</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Online", x=dept_df["department"], y=dept_df["online"], marker_color=t["green"]))
            fig.add_trace(go.Bar(name="Offline", x=dept_df["department"], y=dept_df["offline"], marker_color=t["red"]))
            if "compromised" in dept_df.columns:
                fig.add_trace(go.Bar(name="Compromised", x=dept_df["department"], y=dept_df["compromised"], marker_color="#dc2626"))
            fig.update_layout(
                barmode="stack", height=280, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                xaxis=dict(tickangle=-45),
                **_plotly_theme(),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        devs_all = get_devices(DB_PATH)
        if not devs_all.empty:
            st.markdown('<div class="card"><div class="card-title">Device Type Distribution</div>', unsafe_allow_html=True)
            type_counts = devs_all["device_type"].value_counts().head(12)
            fig2 = go.Figure(go.Bar(
                x=type_counts.values, y=type_counts.index,
                orientation="h", marker_color=t["accent"],
            ))
            fig2.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                **_plotly_theme(),
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Criticality + Status donuts
    devs_all = get_devices(DB_PATH)
    if not devs_all.empty:
        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="card"><div class="card-title">Criticality Distribution</div>', unsafe_allow_html=True)
            crit_counts = devs_all["criticality"].value_counts()
            colors_map = {"critical": t["red"], "high": t["amber"], "medium": t["cyan"], "low": t["green"]}
            fig3 = go.Figure(go.Pie(
                labels=crit_counts.index, values=crit_counts.values,
                marker=dict(colors=[colors_map.get(c, t["accent"]) for c in crit_counts.index]),
                hole=0.45, textinfo="label+value", textfont=dict(size=11),
            ))
            fig3.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, **_plotly_theme())
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card"><div class="card-title">Status Overview</div>', unsafe_allow_html=True)
            stat_counts = devs_all["status"].value_counts()
            s_colors = {"online": t["green"], "offline": t["red"], "maintenance": t["amber"],
                       "compromised": "#dc2626", "error": "#dc2626", "corrupted": "#dc2626"}
            fig4 = go.Figure(go.Pie(
                labels=stat_counts.index, values=stat_counts.values,
                marker=dict(colors=[s_colors.get(s, t["accent"]) for s in stat_counts.index]),
                hole=0.45, textinfo="label+value", textfont=dict(size=11),
            ))
            fig4.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, **_plotly_theme())
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown(
        f'<div style="text-align:center;color:{t["muted"]};font-size:0.65rem;margin-top:20px">'
        f'MediCore IoMT  |  {counts["total"]} devices across {len(DEPARTMENTS)} departments  |  '
        f'Last refresh: {datetime.now(timezone.utc).strftime("%H:%M:%S UTC")}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── end of _hospital_live_fragment ──


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2: MedGuard-IDS Detection Dashboard
# ═════════════════════════════════════════════════════════════════════════════


def _generate_attack_pdf(log_rows: list, attack_label: str, anomaly_count: int) -> bytes:
    """Generate a PDF incident report for detected attacks. Returns PDF bytes."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    W = 190   # usable width
    LM = 10   # left margin

    # Color palette
    C_RED = (220, 38, 38)
    C_DARK_RED = (153, 27, 27)
    C_GREEN = (34, 197, 94)
    C_BLUE = (37, 99, 235)
    C_DARK = (30, 30, 30)
    C_BODY = (55, 55, 55)
    C_MUTED = (120, 120, 120)
    C_LIGHT_BG = (248, 248, 250)

    def _section(title: str, color: tuple = C_DARK):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*color)
        pdf.cell(0, 9, title, ln=True)
        pdf.set_draw_color(*color)
        pdf.line(LM, pdf.get_y(), LM + 50, pdf.get_y())
        pdf.ln(4)

    def _kv(label: str, value: str, lw: int = 52):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(lw, 6, label)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*C_DARK)
        pdf.cell(0, 6, value, ln=True)

    # ── Header ───────────────────────────────────────────────────────────
    pdf.add_page()

    pdf.set_fill_color(*C_RED)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(8)
    pdf.cell(0, 10, "MedGuard-IDS Incident Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(255, 220, 220)
    pdf.cell(0, 6, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True, align="C")
    pdf.set_y(40)

    # ── Attack Summary ───────────────────────────────────────────────────
    total_scanned = len(log_rows)
    detection_rate = (anomaly_count / total_scanned * 100) if total_scanned else 0

    pdf.set_fill_color(255, 245, 245)
    pdf.set_draw_color(*C_RED)
    box_y = pdf.get_y()
    pdf.rect(LM, box_y, W, 30, "DF")
    pdf.set_xy(LM + 6, box_y + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*C_RED)
    pdf.cell(0, 8, f"Attack: {attack_label}", ln=True)
    pdf.set_x(LM + 6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_BODY)
    pdf.cell(50, 6, f"Devices Flagged: {anomaly_count}")
    pdf.cell(50, 6, f"Devices Clear: {total_scanned - anomaly_count}")
    pdf.cell(0, 6, f"Detection Rate: {detection_rate:.1f}%", ln=True)
    pdf.set_y(box_y + 34)

    # ── Affected Devices Table ───────────────────────────────────────────
    flagged = [r for r in log_rows if r.get("prediction") == 1]
    if flagged:
        _section("Affected IoMT Devices", C_RED)

        col_w = [28, 22, 24, 22, 22, 22, 22, 28]
        headers = ["Device ID", "Attack", "Anomaly", "Final", "Threshold", "Trust Bef", "Trust Aft", "Response"]
        table_x = LM + (W - sum(col_w)) / 2

        def _tbl_hdr():
            pdf.set_x(table_x)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(*C_DARK)
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
            pdf.ln()

        _tbl_hdr()
        pdf.set_font("Helvetica", "", 7)

        for r in flagged[:40]:
            pdf.set_x(table_x)
            pdf.set_fill_color(255, 250, 250)
            pdf.set_text_color(*C_DARK_RED)
            pdf.cell(col_w[0], 5.5, str(r.get("device_id", "?"))[:12], border=1, align="C", fill=True)
            pdf.cell(col_w[1], 5.5, str(r.get("attack_type", "?"))[:10], border=1, align="C", fill=True)
            pdf.cell(col_w[2], 5.5, str(r.get("anomaly_score", 0)), border=1, align="C", fill=True)
            pdf.cell(col_w[3], 5.5, str(r.get("final_score", 0)), border=1, align="C", fill=True)
            pdf.cell(col_w[4], 5.5, str(r.get("threshold", 0)), border=1, align="C", fill=True)
            pdf.cell(col_w[5], 5.5, str(r.get("trust_before", 0)), border=1, align="C", fill=True)
            pdf.cell(col_w[6], 5.5, str(r.get("trust_after", 0)), border=1, align="C", fill=True)
            pdf.set_text_color(*C_RED)
            pdf.cell(col_w[7], 5.5, str(r.get("response", "ALERT")), border=1, align="C", fill=True)
            pdf.ln()

            if pdf.get_y() > 265:
                pdf.add_page()
                _tbl_hdr()
                pdf.set_font("Helvetica", "", 7)

        if len(flagged) > 40:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*C_MUTED)
            pdf.cell(0, 6, f"... and {len(flagged) - 40} more affected devices", ln=True)
        pdf.ln(4)

    # ── Clear Devices ────────────────────────────────────────────────────
    clear = [r for r in log_rows if r.get("prediction") == 0]
    if clear:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*C_GREEN)
        pdf.cell(0, 8, f"Clear Devices: {len(clear)}", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*C_BODY)
        pdf.cell(0, 5, "These devices passed all anomaly checks and are operating normally.", ln=True)
        pdf.ln(4)

    # ── Trust Analysis ───────────────────────────────────────────────────
    if flagged:
        _section("Trust Analysis", C_DARK)

        avg_tb = sum(r.get("trust_before", 0) for r in flagged) / len(flagged)
        avg_ta = sum(r.get("trust_after", 0) for r in flagged) / len(flagged)
        avg_sc = sum(r.get("anomaly_score", 0) for r in flagged) / len(flagged)
        max_sc = max(r.get("anomaly_score", 0) for r in flagged)

        _kv("Avg Trust Before Attack", f"{avg_tb:.4f}")
        _kv("Avg Trust After Attack", f"{avg_ta:.4f}")
        _kv("Trust Degradation", f"{avg_tb - avg_ta:.4f}")
        _kv("Avg Anomaly Score", f"{avg_sc:.4f}")
        _kv("Max Anomaly Score", f"{max_sc:.4f}")
        pdf.ln(4)

    # ── Recommended Actions ──────────────────────────────────────────────
    _section("Recommended Actions", C_BLUE)
    actions = [
        "Immediately isolate all flagged IoMT devices from the hospital network.",
        "Notify clinical engineering and cybersecurity incident response team.",
        "Verify patient safety for all devices marked ALERT_RAISED.",
        "Review blockchain ledger for tamper evidence (block hashes logged).",
        "Restore affected devices from known-good firmware/configuration.",
        "Conduct forensic analysis on compromised device traffic logs.",
    ]
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C_BODY)
    for i, a in enumerate(actions, 1):
        pdf.cell(W, 6.5, f"  {i}.  {a}", ln=True)
    pdf.ln(4)

    # ── Footer ───────────────────────────────────────────────────────────
    pdf.set_draw_color(200, 200, 200)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(0, 5, "MedGuard-IDS  |  Adaptive Trust-Aware Stacking IDS for IoMT  |  Blockchain-Verified", ln=True, align="C")

    return pdf.output()


@st.fragment(run_every=3)
def _ids_watcher() -> None:
    if not st.session_state.get("_ids_connected"):
        return

    trained = st.session_state.get("_model")
    te      = st.session_state.get("_te")
    bc      = st.session_state.get("_bc")
    if not trained or not te:
        return

    records, device_info = get_hospital_stream()
    if not records:
        return

    rt = RealtimeDetectionEngine(
        model=trained.model, preprocessor=trained.preprocessor,
        trust_engine=te, blockchain=bc,
        base_threshold=0.5, use_trust_weighted_score=True,
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for rec, info in zip(records, device_info):
        trust_before = te.get_trust(info["device_id"])
        out = rt.process_record(rec)
        pkt_rate = round(float(rec.get("rate", 0)), 1)
        latency_ms = round(max(5.0, _random.uniform(5, 20) * max(1.0, pkt_rate / 333.0)), 1)
        rows.append({
            "timestamp":    ts,
            "device_id":    info["device_id"],
            "attack_type":  info["attack_type"],
            "packet_rate":  pkt_rate,
            "latency_ms":   latency_ms,
            "anomaly_score":round(out["anomaly_score"], 4),
            "final_score":  round(out["final_score"],   4),
            "threshold":    round(out["threshold"],     4),
            "prediction":   out["prediction"],
            "trust_before": round(trust_before,         4),
            "trust_after":  round(out["trust"],         4),
            "response":     "ALERT_RAISED" if out["prediction"] == 1 else "CLEAR",
            "block_hash":   out["block_hash"],
        })

    active_atks = get_active_attacks()
    anomaly_count = sum(1 for r in rows if r["prediction"] == 1)
    attack_label = ", ".join(a.upper() for a in active_atks) if active_atks else "None"
    prev_label = st.session_state.get("_prev_attack_label", "__init__")
    prev_anomaly = st.session_state.get("_prev_anomaly_count", -1)

    log = st.session_state.get("_ids_log", [])
    st.session_state["_ids_log"]            = (rows + log)[:300]
    st.session_state["_anomaly_count"]      = anomaly_count
    st.session_state["_attack_label"]       = attack_label
    st.session_state["_blockchain_blocks"]  = len(bc.chain)
    st.session_state["_active_attacks_ids"] = active_atks

    try:
        full_log = st.session_state.get("_ids_log", rows)
        full_anomaly = sum(1 for r in full_log if r.get("prediction") == 1)
        write_anomaly = max(anomaly_count, full_anomaly) if active_atks else anomaly_count
        IDS_OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        IDS_OUT_JSON.write_text(json.dumps({
            "log": full_log[:140], "anomaly_count": write_anomaly,
            "attack_label": attack_label, "active_attacks": active_atks,
            "timestamp": ts, "blockchain_blocks": len(bc.chain),
        }, indent=2), encoding="utf-8")
    except Exception:
        pass

    if attack_label != prev_label or anomaly_count != prev_anomaly:
        st.session_state["_prev_attack_label"] = attack_label
        st.session_state["_prev_anomaly_count"] = anomaly_count
        st.rerun()


def page_ids() -> None:
    t = _t()

    st.markdown(
        '<div class="hdr"><div>'
        '<div class="hdr-title">MedGuard-IDS</div>'
        '<div class="hdr-sub">IoMT Intrusion Detection  |  RF + GRU + XGB Stacking  |  Adaptive Trust  |  Blockchain Logged</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if not MODEL_PATH.exists():
        st.error(f"Trained model not found: {MODEL_PATH}")
        return

    hospital_ok = db_exists()

    # Session objects
    if "_model" not in st.session_state:
        with st.spinner("Loading model..."):
            st.session_state["_model"] = load_trained_bundle(str(MODEL_PATH))
    if "_te" not in st.session_state:
        st.session_state["_te"] = TrustEngine(alpha=0.08, beta=0.03, default_trust=0.8)
    if "_bc" not in st.session_state:
        st.session_state["_bc"] = LightweightBlockchain()
    if "_ids_log" not in st.session_state:
        st.session_state["_ids_log"] = []

    connected = st.session_state.get("_ids_connected", False)

    # Controls
    col_r, col_cl, col_c, col_x = st.columns([1, 1, 2, 6])
    with col_r:
        if st.button("Reset", use_container_width=True, key="ids_reset"):
            for k in ("_te", "_bc", "_ids_log", "_prev_attack_label", "_prev_anomaly_count",
                      "_anomaly_count", "_attack_label", "_blockchain_blocks", "_active_attacks_ids"):
                st.session_state.pop(k, None)
            try:
                IDS_OUT_JSON.unlink(missing_ok=True)
            except Exception:
                pass
            st.rerun()

    with col_cl:
        if st.button("Clear Log", use_container_width=True, key="ids_clear"):
            st.session_state["_ids_log"] = []
            for k in ("_anomaly_count", "_attack_label", "_active_attacks_ids", "_blockchain_blocks"):
                st.session_state.pop(k, None)
            try:
                IDS_OUT_JSON.unlink(missing_ok=True)
            except Exception:
                pass
            st.rerun()

    with col_c:
        if connected:
            if st.button("Disconnect from Hospital", use_container_width=True, type="primary", key="ids_disc"):
                st.session_state["_ids_connected"] = False
                try:
                    IDS_OUT_JSON.unlink(missing_ok=True)
                except Exception:
                    pass
                st.rerun()
        else:
            btn_disabled = not hospital_ok
            if st.button("Connect to Hospital", use_container_width=True, disabled=btn_disabled, key="ids_conn"):
                st.session_state["_ids_connected"] = True
                st.rerun()
            if btn_disabled:
                st.caption("Hospital database not initialized yet. Visit Hospital page first.")

    # Status data
    log           = st.session_state.get("_ids_log", [])
    anomaly_count = st.session_state.get("_anomaly_count", 0)
    attack_label  = st.session_state.get("_attack_label", "None")
    active_atks   = st.session_state.get("_active_attacks_ids", [])
    bc_blocks     = st.session_state.get("_blockchain_blocks", 0)

    # Pills
    if connected:
        conn_pill = f'<span class="pill pill-green"><span class="dot dot-g"></span>Hospital Connected</span>'
    else:
        conn_pill = f'<span class="pill pill-amber"><span class="dot dot-y"></span>Disconnected</span>'

    st.markdown(
        f'<div style="margin-bottom:10px">{conn_pill}'
        f'<span class="pill {"pill-red" if active_atks else "pill-cyan"}">'
        f'<span class="dot {"dot-r" if active_atks else "dot-c"}"></span>'
        f'Attack: {attack_label}</span>'
        f'<span class="pill pill-cyan"><span class="dot dot-c"></span>Blocks: {bc_blocks}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Status banners
    if not connected:
        st.markdown('<div class="idle-banner">Click Connect to Hospital to start live detection.</div>', unsafe_allow_html=True)
    elif anomaly_count > 0:
        st.markdown(
            f'<div class="alert-banner">INTRUSION DETECTED -- {anomaly_count} device(s) flagged'
            f'{" | " + attack_label if active_atks else ""}</div>',
            unsafe_allow_html=True,
        )
        # PDF report download
        if log:
            try:
                pdf_bytes = _generate_attack_pdf(log, attack_label, anomaly_count)
                ts_file = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="Download Incident Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"MedGuard_Incident_{ts_file}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=False,
                    key="pdf_dl",
                )
            except Exception as exc:
                st.caption(f"PDF generation error: {exc}")
    elif log:
        st.markdown('<div class="ok-banner">All devices nominal -- No threats detected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="idle-banner">Connected -- waiting for first detection scan...</div>', unsafe_allow_html=True)

    # Detection log
    if log:
        st.markdown('<div class="tbl-label">Detection Log -- latest results</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(log[:50]), use_container_width=True, hide_index=True)

    _ids_watcher()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3: Attack Lab
# ═════════════════════════════════════════════════════════════════════════════

ATTACKS = {
    "dos": {
        "name": "DoS FLOOD",
        "desc": "TCP connection flood against hospital. Overwhelms the server with 80 parallel threads. Knocks 40 devices offline.",
        "launch": launch_dos, "stop": stop_dos,
    },
    "tamper": {
        "name": "DATA TAMPER",
        "desc": "Corrupts device firmware versions and marks 60% of devices as compromised. Injects 50 falsified vital sign readings.",
        "launch": launch_tamper, "stop": stop_tamper,
    },
    "spoof": {
        "name": "DEVICE SPOOF",
        "desc": "Injects 25 rogue devices into the hospital network with fake identities. All marked as critical-class.",
        "launch": launch_spoof, "stop": stop_spoof,
    },
    "ransomware": {
        "name": "RANSOMWARE",
        "desc": "Encrypts all device data and locks the entire IoMT fleet. Corrupts output files. Full hospital ransomware incident.",
        "launch": launch_ransomware, "stop": stop_ransomware,
    },
    "replay": {
        "name": "REPLAY ATTACK",
        "desc": "Replays stale vital sign data with bradycardia and low SpO2 readings. Creates flood of false clinical alerts.",
        "launch": launch_replay, "stop": stop_replay,
    },
    "mitm": {
        "name": "MAN-IN-THE-MIDDLE",
        "desc": "Intercepts telemetry from critical devices and injects subtly altered readings. Causes incorrect clinical decisions.",
        "launch": launch_mitm, "stop": stop_mitm,
    },
}


def page_attack_lab() -> None:
    t = _t()

    if "_attack_log" not in st.session_state:
        st.session_state["_attack_log"] = []

    def _log(msg: str, level: str = "info") -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        st.session_state["_attack_log"].insert(0, (ts, msg, level))
        st.session_state["_attack_log"] = st.session_state["_attack_log"][:100]

    st.markdown(
        '<div class="hdr hdr-red"><div>'
        '<div class="hdr-title-red">ATTACK LAB  //  IoMT Adversary Console</div>'
        '<div class="hdr-sub">Controlled cyberattack environment for MedGuard-IDS validation</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    db_ok = Path(ATK_DB_PATH).exists()
    if not db_ok:
        st.markdown(
            '<div class="alert-banner">'
            'Hospital database not found. Visit the Hospital IoMT page first to initialize the database.</div>',
            unsafe_allow_html=True,
        )
        return

    current = atk_active()

    # Status bar
    if current:
        attacks_str = " | ".join(ATTACKS[a]["name"] for a in current if a in ATTACKS)
        st.markdown(
            f'<div class="alert-banner">ATTACKS ACTIVE: {attacks_str}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="ok-banner">System nominal. No active attacks.</div>',
            unsafe_allow_html=True,
        )

    # Counters
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="counter">{len(current)}</div><div class="counter-lbl">Active Attacks</div>', unsafe_allow_html=True)
    with c2:
        total_launched = sum(1 for _, _, l in st.session_state["_attack_log"] if l == "attack")
        st.markdown(f'<div class="counter" style="color:{t["amber"]}">{total_launched}</div><div class="counter-lbl">Total Launched</div>', unsafe_allow_html=True)
    with c3:
        total_stopped = sum(1 for _, _, l in st.session_state["_attack_log"] if l == "restore")
        st.markdown(f'<div class="counter" style="color:{t["green"]}">{total_stopped}</div><div class="counter-lbl">Restored</div>', unsafe_allow_html=True)

    st.markdown("")

    if current:
        if st.button("STOP ALL ATTACKS", type="primary", use_container_width=True, key="atk_stop_all"):
            results = atk_stop_all()
            for k, v in results.items():
                _log(f"Stopped {k}: {v}", "restore")
            st.rerun()

    st.markdown("")

    # Attack cards
    atk_colors = {
        "dos": t["red"], "tamper": t["purple"], "spoof": t["amber"],
        "ransomware": "#dc2626", "replay": t["cyan"], "mitm": "#f97316",
    }

    cols = st.columns(3)
    for idx, (key, atk) in enumerate(ATTACKS.items()):
        is_active = key in current
        color = atk_colors.get(key, t["red"])
        with cols[idx % 3]:
            card_class = "atk-card active" if is_active else "atk-card"
            st.markdown(
                f'<div class="{card_class}">'
                f'<div class="atk-name" style="color:{color}">{atk["name"]}</div>'
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

    # Attack log
    st.markdown("")
    st.markdown(
        f'<div class="card">'
        f'<div class="card-title" style="border-bottom-color:{t["red"]}">Attack Log</div>',
        unsafe_allow_html=True,
    )
    atk_log = st.session_state.get("_attack_log", [])
    if atk_log:
        lines = []
        for ts, msg, level in atk_log[:30]:
            css_class = "log-err" if level == "attack" else ("log-line" if level == "restore" else "log-warn")
            prefix = ">>>" if level == "attack" else "<<<" if level == "restore" else "---"
            lines.append(f'<div class="log-line {css_class}">[{ts}] {prefix} {msg}</div>')
        st.markdown("\n".join(lines), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="log-line">Waiting for commands...</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="MedGuard-IDS",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Init theme
    if "_theme" not in st.session_state:
        st.session_state["_theme"] = "dark"

    st.markdown(_css(), unsafe_allow_html=True)

    _bootstrap()

    # Sidebar
    t = _t()
    with st.sidebar:
        st.markdown(
            f'<div style="padding:10px 0 20px 0;border-bottom:1px solid {t["border"]};margin-bottom:20px">'
            f'<div style="font-size:1.1rem;font-weight:800;color:{t["heading"]}">MedGuard-IDS</div>'
            f'<div style="font-size:0.65rem;color:{t["muted"]};margin-top:2px">Unified IoMT Security Platform</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigation",
            ["Hospital IoMT", "Intrusion Detection", "Attack Lab"],
            key="_page",
            label_visibility="collapsed",
        )

        st.markdown(f'<div style="margin-top:30px;border-top:1px solid {t["border"]};padding-top:15px"></div>', unsafe_allow_html=True)

        # Theme toggle
        theme_label = "Switch to Light Mode" if st.session_state["_theme"] == "dark" else "Switch to Dark Mode"
        if st.button(theme_label, use_container_width=True, key="theme_toggle"):
            st.session_state["_theme"] = "light" if st.session_state["_theme"] == "dark" else "dark"
            st.rerun()

        current_theme = "Dark" if st.session_state["_theme"] == "dark" else "Light"
        st.markdown(
            f'<div style="text-align:center;font-size:0.65rem;color:{t["muted"]};margin-top:8px">'
            f'Theme: {current_theme}</div>',
            unsafe_allow_html=True,
        )

        # Status info
        st.markdown(
            f'<div style="margin-top:40px;padding-top:15px;border-top:1px solid {t["border"]}">'
            f'<div style="font-size:0.65rem;color:{t["muted"]};line-height:1.8">'
            f'Platform: Streamlit<br>'
            f'ML Engine: RF + XGB + GRU<br>'
            f'Trust: Adaptive 3-Tier<br>'
            f'Ledger: SHA-256 Blockchain'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # Render selected page
    if page == "Hospital IoMT":
        page_hospital()
    elif page == "Intrusion Detection":
        page_ids()
    elif page == "Attack Lab":
        page_attack_lab()


if __name__ == "__main__":
    main()
