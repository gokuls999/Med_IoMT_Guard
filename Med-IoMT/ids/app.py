"""MedGuard-IDS -- Live Detection Dashboard
Run: streamlit run ids/app.py --server.port 8501
"""
from __future__ import annotations

import io
import json
import random as _random
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))

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
from ids.bridge import db_exists, get_active_attacks, get_hospital_stream

MODEL_PATH   = PROJECT / "trained_model.pkl"
_IOMT_ROOT   = PROJECT.parent                # Binu - IoMT root
IDS_OUT_JSON = _IOMT_ROOT / "hospital_workflow_system" / "outputs" / "ids_detection_results.json"

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#0d1117"
CARD    = "#161b22"
BORDER  = "#1e3a5f"
CYAN    = "#06b6d4"
GREEN   = "#22c55e"
RED     = "#ef4444"
AMBER   = "#f59e0b"
TEXT    = "#c8d6e5"
HEADING = "#f0f9ff"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
.stApp           {{ background-color: {BG} !important; }}
.block-container {{ padding: 1rem 2rem 2rem 2rem !important; max-width: 100% !important; }}

[data-testid="collapsedControl"] {{ display: none !important; }}
[data-testid="stSidebar"]        {{ display: none !important; }}
[data-testid="stToolbar"]        {{ display: none !important; }}
[data-testid="stHeader"]         {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
footer    {{ display: none !important; }}

.hdr {{
    background: linear-gradient(135deg, #0a1628, #0f2540);
    border: 1px solid {BORDER}; border-left: 4px solid {CYAN};
    border-radius: 10px; padding: 12px 20px; margin-bottom: 14px;
    display: flex; align-items: center; justify-content: space-between;
}}
.hdr-title {{ font-size: 1.1rem; font-weight: 800; color: {HEADING}; }}
.hdr-sub   {{ font-size: 0.7rem; color: #475569; margin-top: 2px; }}

.pill {{
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: 20px; padding: 3px 11px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
    text-transform: uppercase; margin-right: 6px;
}}
.pill-green  {{ background:rgba(34,197,94,0.12);  color:{GREEN}; border:1px solid rgba(34,197,94,0.3); }}
.pill-red    {{ background:rgba(239,68,68,0.12);  color:{RED}; border:1px solid rgba(239,68,68,0.3); }}
.pill-cyan   {{ background:rgba(6,182,212,0.12);  color:{CYAN}; border:1px solid rgba(6,182,212,0.3); }}
.pill-yellow {{ background:rgba(234,179,8,0.12);  color:#eab308; border:1px solid rgba(234,179,8,0.3); }}
.dot {{ width:6px; height:6px; border-radius:50%; display:inline-block; }}
.dot-g {{ background:{GREEN}; }} .dot-r {{ background:{RED}; }}
.dot-c {{ background:{CYAN}; }} .dot-y {{ background:#eab308; }}

.banner-threat {{
    background:rgba(239,68,68,0.1); border-left:4px solid {RED};
    padding:9px 16px; border-radius:0 8px 8px 0;
    font-size:0.83rem; color:#fca5a5; margin:8px 0;
}}
.banner-ok {{
    background:rgba(34,197,94,0.08); border-left:4px solid {GREEN};
    padding:9px 16px; border-radius:0 8px 8px 0;
    font-size:0.83rem; color:#86efac; margin:8px 0;
}}
.banner-idle {{
    background:rgba(6,182,212,0.06); border-left:4px solid {CYAN};
    padding:9px 16px; border-radius:0 8px 8px 0;
    font-size:0.83rem; color:#67e8f9; margin:8px 0;
}}
.tbl-label {{
    font-size:0.7rem; font-weight:700; color:#475569;
    text-transform:uppercase; letter-spacing:0.06em; margin:12px 0 5px 0;
}}
[data-testid="stDataFrame"] {{ border-radius:8px; overflow:hidden; }}
.stButton > button {{ border-radius:8px !important; font-weight:600 !important; font-size:0.8rem !important; }}
</style>
"""


# ── Silent background watcher ─────────────────────────────────────────────────

@st.fragment(run_every=3)
def _silent_watcher() -> None:
    if not st.session_state.get("_hospital_connected"):
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

    log = st.session_state.get("_log", [])
    st.session_state["_log"]               = (rows + log)[:300]
    st.session_state["_anomaly_count"]     = anomaly_count
    st.session_state["_attack_label"]      = attack_label
    st.session_state["_blockchain_blocks"] = len(bc.chain)
    st.session_state["_active_attacks"]    = active_atks

    # Write results to shared JSON so hospital dashboard can read them.
    # Use the accumulated session log (not just the latest scan) so the
    # hospital dashboard sees stable results instead of flickering when
    # random sampling produces a momentarily clean scan.
    try:
        full_log = st.session_state.get("_log", rows)
        # Only write the latest scan's 140 records (not accumulated history)
        # so anomaly_count never exceeds total device count.
        write_log = full_log[:len(rows)] if len(full_log) > len(rows) else full_log
        write_anomaly = sum(1 for r in write_log if r.get("prediction") == 1)
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


# ── Attack Reference Data ────────────────────────────────────────────────────
ATTACK_INFO = [
    {
        "name": "DoS Flood",
        "type": "dos",
        "method": "TCP/UDP socket flood targeting hospital network endpoints with high-volume traffic.",
        "iomt_impact": [
            "IoMT telemetry streams stop updating -- live patient vitals flatline on monitors.",
            "Device status checks timeout -- all connected devices appear unresponsive.",
            "Security signal polling fails -- IDS model cannot scan devices during flood.",
        ],
        "detection": "Model detects abnormal packet rates, elevated latency, and connection saturation. "
                     "Anomaly score spikes above threshold; trust score drops rapidly for affected devices.",
    },
    {
        "name": "Device Spoofing",
        "type": "spoof",
        "method": "Attacker clones legitimate device MAC/IP addresses to inject false telemetry data.",
        "iomt_impact": [
            "Fake device identities inject fabricated vital signs (e.g., normal readings for a crashing patient).",
            "Hospital staff may act on spoofed data, leading to wrong clinical decisions.",
            "Legitimate device trust scores degrade as spoofed traffic appears anomalous.",
        ],
        "detection": "Stacking model (RF+GRU+XGB) identifies feature-level inconsistencies between spoofed and "
                     "genuine traffic. Trust engine penalises devices showing identity conflicts.",
    },
    {
        "name": "Data Tampering",
        "type": "tamper",
        "method": "Man-in-the-middle interception modifying IoMT data packets in transit.",
        "iomt_impact": [
            "Patient vital readings are altered (e.g., SpO2 changed from 88% to 98%).",
            "Lab results or medication dosages corrupted, risking patient safety.",
            "Firmware update payloads modified to inject malicious code into devices.",
        ],
        "detection": "Model flags statistical anomalies in feature distributions. Blockchain ledger provides "
                     "tamper-evident audit trail -- any modified prediction is detectable via hash chain verification.",
    },
    {
        "name": "Replay Attack",
        "type": "replay",
        "method": "Previously captured legitimate network packets are re-transmitted to bypass authentication.",
        "iomt_impact": [
            "Old telemetry data replayed as current, masking real-time patient deterioration.",
            "Authentication tokens reused to gain unauthorised access to device control APIs.",
            "Stale medication orders re-executed, causing duplicate drug administration.",
        ],
        "detection": "Temporal analysis detects duplicate/stale packet patterns. Trust-weighted scoring "
                     "reduces confidence for devices exhibiting repetitive traffic signatures.",
    },
    {
        "name": "Ransomware Burst",
        "type": "ransomware",
        "method": "Rapid encryption of device firmware and patient data files across the IoMT network.",
        "iomt_impact": [
            "IoMT devices locked -- ventilators, infusion pumps, monitors become inoperable.",
            "Patient data encrypted and inaccessible, disrupting all clinical workflows.",
            "Device firmware corrupted, requiring full re-flash to restore functionality.",
        ],
        "detection": "Burst detector identifies coordinated high-intensity anomalies across multiple devices. "
                     "Model confidence is highest for ransomware due to dramatic feature deviation from baseline.",
    },
]


def _pdf_safe(text: str) -> str:
    """Replace unicode chars unsupported by Helvetica with ASCII equivalents."""
    return (text
            .replace("\u2014", "--")   # em dash
            .replace("\u2013", "-")    # en dash
            .replace("\u2018", "'")    # left single quote
            .replace("\u2019", "'")    # right single quote
            .replace("\u201c", '"')    # left double quote
            .replace("\u201d", '"')    # right double quote
            .replace("\u2022", "-")    # bullet
            .replace("\u2026", "...")  # ellipsis
            )


def _generate_pdf(log: list, anomaly_count: int, attack_label: str, bc_blocks: int) -> bytes:
    """Generate a professional PDF report with attack details, IoMT impact, and predictions."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    W = 190   # usable width
    LM = 10   # left margin
    BG = (13, 17, 23)
    CYAN = (6, 182, 212)
    TEXT = (200, 214, 229)
    WHITE = (240, 249, 255)
    RED = (239, 68, 68)
    GREEN = (34, 197, 94)
    AMBER = (245, 158, 11)
    MUTED = (130, 140, 155)

    def _dark_page():
        pdf.add_page()
        pdf.set_fill_color(*BG)
        pdf.rect(0, 0, 210, 297, "F")

    def _section_title(title: str):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*CYAN)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_draw_color(*CYAN)
        pdf.line(LM, pdf.get_y(), LM + 55, pdf.get_y())
        pdf.ln(4)

    def _label_value(label: str, value: str, label_w: int = 55):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(label_w, 6, label)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*TEXT)
        pdf.cell(0, 6, value, ln=True)

    # ── Page 1: Header & Summary ─────────────────────────────────────────
    _dark_page()

    # Title bar
    pdf.set_fill_color(6, 182, 212)
    pdf.rect(0, 0, 210, 36, "F")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(13, 17, 23)
    pdf.set_y(8)
    pdf.cell(0, 12, "MedGuard-IDS", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "IoMT Intrusion Detection Report", ln=True, align="C")
    pdf.set_y(42)

    # Timestamp
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True, align="R")
    pdf.ln(4)

    # Summary section
    total = len(log)
    alerts = anomaly_count
    clear = total - alerts

    _section_title("Detection Summary")
    _label_value("Total Devices Scanned", str(total))
    _label_value("Alerts Raised", str(alerts))
    _label_value("Devices Clear", str(clear))
    _label_value("Active Attack(s)", attack_label)
    _label_value("Blockchain Blocks", str(bc_blocks))
    _label_value("Model", "RF + GRU + XGB Stacking Ensemble")
    _label_value("Trust Engine", "Adaptive per-device (alpha=0.08, beta=0.03)")
    pdf.ln(6)

    # ── Attack Types Reference ───────────────────────────────────────────
    _section_title("Attack Types & IoMT Device Impact")

    for atk in ATTACK_INFO:
        # Check page space
        if pdf.get_y() > 230:
            _dark_page()

        # Attack name
        color = RED if atk["type"] in ("dos", "ransomware") else AMBER
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(0, 7, f"{atk['name']}  ({atk['type'].upper()})", ln=True)

        # Method
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*MUTED)
        pdf.set_x(LM + 4)
        pdf.multi_cell(W - 4, 5, _pdf_safe(f"Method: {atk['method']}"))

        # IoMT Impact
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*TEXT)
        pdf.set_x(LM + 4)
        pdf.cell(0, 6, "IoMT Impact:", ln=True)
        pdf.set_font("Helvetica", "", 8)
        for impact in atk["iomt_impact"]:
            pdf.set_x(LM + 8)
            pdf.multi_cell(W - 8, 4.5, _pdf_safe(f"- {impact}"))

        # Detection
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*GREEN)
        pdf.set_x(LM + 4)
        pdf.cell(0, 6, "Detection:", ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*TEXT)
        pdf.set_x(LM + 8)
        pdf.multi_cell(W - 8, 4.5, _pdf_safe(atk["detection"]))
        pdf.ln(3)

    # ── Page 2+: Detection Log Table ─────────────────────────────────────
    if log:
        _dark_page()
        _section_title("Detection Log - Per-Device Predictions")

        cols = ["Device", "Attack", "Anomaly", "Final", "Thresh", "Pred", "Trust Bef", "Trust Aft"]
        widths = [28, 18, 20, 20, 18, 14, 22, 22]  # total = 162, centered
        table_x = LM + (W - sum(widths)) / 2

        def _table_header():
            pdf.set_x(table_x)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(20, 30, 45)
            pdf.set_text_color(*CYAN)
            for i, col in enumerate(cols):
                pdf.cell(widths[i], 7, col, border=1, align="C", fill=True)
            pdf.ln()

        _table_header()

        pdf.set_font("Helvetica", "", 7)
        for row in log[:60]:
            is_alert = row.get("prediction", 0) == 1
            pdf.set_text_color(*(RED if is_alert else TEXT))

            dev_id = str(row.get("device_id", ""))
            if len(dev_id) > 12:
                dev_id = dev_id[:12]
            vals = [
                dev_id,
                str(row.get("attack_type", "none"))[:8],
                str(row.get("anomaly_score", "")),
                str(row.get("final_score", "")),
                str(row.get("threshold", "")),
                "ALERT" if is_alert else "OK",
                str(row.get("trust_before", "")),
                str(row.get("trust_after", "")),
            ]
            pdf.set_x(table_x)
            bg = (25, 15, 15) if is_alert else BG
            pdf.set_fill_color(*bg)
            for i, v in enumerate(vals):
                pdf.cell(widths[i], 5.5, v, border=1, align="C", fill=True)
            pdf.ln()

            if pdf.get_y() > 268:
                _dark_page()
                _table_header()
                pdf.set_font("Helvetica", "", 7)

        # ── Statistics ───────────────────────────────────────────────────
        pdf.ln(8)
        _section_title("Prediction Statistics")

        scores = [r.get("anomaly_score", 0) for r in log]
        trust_vals = [r.get("trust_after", 0) for r in log]
        alert_rows = [r for r in log if r.get("prediction") == 1]

        _label_value("Mean Anomaly Score", f"{sum(scores)/len(scores):.4f}")
        _label_value("Max Anomaly Score", f"{max(scores):.4f}")
        _label_value("Mean Trust (after)", f"{sum(trust_vals)/len(trust_vals):.4f}")
        _label_value("Min Trust (after)", f"{min(trust_vals):.4f}")
        _label_value("Alert Rate", f"{len(alert_rows)}/{len(log)} ({len(alert_rows)/len(log)*100:.1f}%)")

        if alert_rows:
            alert_types: dict[str, int] = {}
            for r in alert_rows:
                t = r.get("attack_type", "unknown")
                alert_types[t] = alert_types.get(t, 0) + 1
            breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(alert_types.items()))
            _label_value("Alert Breakdown", breakdown)

    # ── Footer ───────────────────────────────────────────────────────────
    pdf.ln(10)
    pdf.set_draw_color(*MUTED)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(80, 90, 100)
    pdf.cell(0, 5, "MedGuard-IDS  |  RF + GRU + XGB Stacking  |  Adaptive Trust Engine  |  Blockchain Logged", ln=True, align="C")
    pdf.cell(0, 5, "Auto-generated from live IDS detection data.", ln=True, align="C")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="MedGuard-IDS",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="hdr">'
        '  <div>'
        '    <div class="hdr-title">MedGuard-IDS</div>'
        '    <div class="hdr-sub">IoMT Intrusion Detection  |  RF + GRU + XGB Stacking  |  Adaptive Trust  |  Blockchain Logged</div>'
        '  </div>'
        '</div>',
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
    if "_log" not in st.session_state:
        st.session_state["_log"] = []

    connected = st.session_state.get("_hospital_connected", False)

    # Controls
    col_r, col_cl, col_c, col_x = st.columns([1, 1, 2, 6])
    with col_r:
        if st.button("Reset", use_container_width=True):
            for k in ("_te", "_bc", "_log", "_prev_attack_label", "_prev_anomaly_count",
                      "_anomaly_count", "_attack_label", "_blockchain_blocks", "_active_attacks"):
                st.session_state.pop(k, None)
            try:
                IDS_OUT_JSON.unlink(missing_ok=True)
            except Exception:
                pass
            st.rerun()

    with col_cl:
        if st.button("Clear Log", use_container_width=True):
            st.session_state["_log"] = []
            for k in ("_anomaly_count", "_attack_label", "_active_attacks", "_blockchain_blocks"):
                st.session_state.pop(k, None)
            try:
                IDS_OUT_JSON.unlink(missing_ok=True)
            except Exception:
                pass
            st.rerun()

    with col_c:
        if connected:
            if st.button("Disconnect from Hospital", use_container_width=True, type="primary"):
                st.session_state["_hospital_connected"] = False
                try:
                    IDS_OUT_JSON.unlink(missing_ok=True)
                except Exception:
                    pass
                st.rerun()
        else:
            btn_disabled = not hospital_ok
            if st.button("Connect to Hospital", use_container_width=True, disabled=btn_disabled):
                st.session_state["_hospital_connected"] = True
                st.rerun()
            if btn_disabled:
                st.caption("Start hospital dashboard (port 8502) first")

    # Read display data
    log           = st.session_state.get("_log", [])
    anomaly_count = st.session_state.get("_anomaly_count", 0)
    attack_label  = st.session_state.get("_attack_label", "None")
    active_atks   = st.session_state.get("_active_attacks", [])
    bc_blocks     = st.session_state.get("_blockchain_blocks", 0)

    # Status pills
    if connected:
        conn_pill = '<span class="pill pill-green"><span class="dot dot-g"></span>Hospital Connected</span>'
    else:
        conn_pill = '<span class="pill pill-yellow"><span class="dot dot-y"></span>Disconnected</span>'

    st.markdown(
        f'<div style="margin-bottom:10px">'
        f'{conn_pill}'
        f'<span class="pill {"pill-red" if active_atks else "pill-cyan"}">'
        f'  <span class="dot {"dot-r" if active_atks else "dot-c"}"></span>'
        f'  Attack: {attack_label}'
        f'</span>'
        f'<span class="pill pill-cyan"><span class="dot dot-c"></span>Blocks: {bc_blocks}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # State-based content
    if not connected:
        st.markdown(
            '<div class="banner-idle">Click Connect to Hospital to start live detection.</div>',
            unsafe_allow_html=True,
        )
    elif anomaly_count > 0:
        st.markdown(
            f'<div class="banner-threat">INTRUSION DETECTED -- {anomaly_count} device(s) flagged'
            f'{" | " + attack_label if active_atks else ""}</div>',
            unsafe_allow_html=True,
        )
    elif log:
        st.markdown(
            '<div class="banner-ok">All devices nominal -- No threats detected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="banner-idle">Connected -- waiting for first detection scan...</div>',
            unsafe_allow_html=True,
        )

    # Detection log
    if log:
        st.markdown('<div class="tbl-label">Detection Log -- latest results</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(log[:50]), use_container_width=True, hide_index=True)

        # PDF Report download
        ts_label = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        pdf_bytes = _generate_pdf(log, anomaly_count, attack_label, bc_blocks)
        st.download_button(
            label="Download IDS Report (PDF)",
            data=pdf_bytes,
            file_name=f"MedGuard_IDS_Report_{ts_label}.pdf",
            mime="application/pdf",
        )
    else:
        # Show attack reference even when no log data yet
        st.markdown(
            '<div class="tbl-label">Attack Types Reference -- What each attack does to IoMT devices</div>',
            unsafe_allow_html=True,
        )
        for atk in ATTACK_INFO:
            color = RED if atk["type"] in ("dos", "ransomware") else AMBER
            st.markdown(
                f'<div style="background:{CARD};border:1px solid {BORDER};border-left:3px solid {color};'
                f'border-radius:6px;padding:10px 14px;margin-bottom:8px">'
                f'<div style="font-weight:700;color:{color};font-size:0.9rem">{atk["name"]} ({atk["type"].upper()})</div>'
                f'<div style="color:#94a3b8;font-size:0.78rem;margin:3px 0">{atk["method"]}</div>'
                + "".join(f'<div style="color:{TEXT};font-size:0.76rem;padding-left:8px">- {imp}</div>' for imp in atk["iomt_impact"])
                + f'<div style="color:{GREEN};font-size:0.76rem;margin-top:4px;font-weight:600">Detection: {atk["detection"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Silent background watcher
    _silent_watcher()


if __name__ == "__main__":
    main()
