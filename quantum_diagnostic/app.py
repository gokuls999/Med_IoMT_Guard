"""
Quantum IoMT Diagnostic Dashboard  —  port 8504
Binu's hierarchical quantum-enhanced IoMT framework:
  ANUKF  ->  Q-Flex ViT  ->  BMOCO  ->  HQAN  ->  RBWKA  ->  VQC  ->  Adaptive SHARP
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quantum IoMT Diagnostics",
    page_icon="assets/icon.png" if os.path.exists("assets/icon.png") else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Colour tokens ──────────────────────────────────────────────────────────────
C_PRIMARY  = "#2563eb"   # blue
C_TEAL     = "#0891b2"   # secondary
C_GREEN    = "#16a34a"
C_AMBER    = "#d97706"
C_RED      = "#dc2626"
C_PURPLE   = "#7c3aed"
C_SLATE    = "#64748b"
C_NAVY     = "#0f172a"
C_TEXT     = "#0f172a"
C_MUTED    = "#64748b"
C_BORDER   = "#e2e8f0"
C_BG       = "#f1f5f9"
C_SURFACE  = "#ffffff"

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Layout ─────────────────────────────────────────── */
.stApp { background: #f1f5f9; color: #0f172a; }
/* padding-top: 4rem clears the Streamlit header bar */
.block-container { padding: 4rem 2.5rem 2rem !important; max-width: 1280px; }

/* ── Sidebar ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #94a3b8 !important; }
[data-testid="stSidebar"] hr  { border-color: #1e293b !important; }

/* Sidebar nav labels */
[data-testid="stSidebar"] .stRadio label {
    color: #cbd5e1 !important;
    font-size: 0.84rem !important;
    padding: 0.25rem 0 !important;
}
/* ALL sidebar buttons — outlined ghost style by default */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #cbd5e1 !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    padding: 0.5rem 0 !important;
    transition: background .15s, border-color .15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1e293b !important;
    border-color: #475569 !important;
    color: #f1f5f9 !important;
}
/* "Run Pipeline" button — highlight with blue (it is always the last button) */
[data-testid="stSidebar"] .stButton:last-of-type > button {
    background: #2563eb !important;
    color: #ffffff !important;
    border-color: #2563eb !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton:last-of-type > button:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
}
/* Sidebar widget labels */
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stSelectbox label {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
}

/* ── KPI cards ──────────────────────────────────────── */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-top: 3px solid;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.kpi-label {
    font-size: 0.67rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}
.kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0.2rem 0 0.1rem;
    line-height: 1;
}
.kpi-sub { font-size: 0.71rem; color: #94a3b8; }

/* ── Surface card ───────────────────────────────────── */
.surface {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    margin-bottom: 1rem;
}

/* ── Page headers ───────────────────────────────────── */
.page-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.25rem;
}
.page-desc { font-size: 0.82rem; color: #64748b; margin: 0 0 1.2rem; }

/* Stage tag */
.stage-tag {
    display: inline-block;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
    border-radius: 4px;
    padding: 0.15rem 0.55rem;
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.6rem;
}

/* Section divider */
.sec {
    font-size: 0.73rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.35rem;
    margin: 1.4rem 0 0.9rem;
}

/* ── Alert boxes ────────────────────────────────────── */
.a-critical {
    background:#fef2f2; border:1px solid #fecaca;
    border-left:4px solid #dc2626; border-radius:6px;
    padding:.65rem 1rem; color:#991b1b; margin:3px 0;
}
.a-warning {
    background:#fffbeb; border:1px solid #fde68a;
    border-left:4px solid #d97706; border-radius:6px;
    padding:.65rem 1rem; color:#92400e; margin:3px 0;
}
.a-normal {
    background:#f0fdf4; border:1px solid #bbf7d0;
    border-left:4px solid #16a34a; border-radius:6px;
    padding:.65rem 1rem; color:#14532d; margin:3px 0;
}
.a-info {
    background:#eff6ff; border:1px solid #bfdbfe;
    border-left:4px solid #2563eb; border-radius:6px;
    padding:.65rem 1rem; color:#1e40af; margin:3px 0;
}

/* ── Patient list rows ──────────────────────────────── */
.pat-row {
    background:#ffffff; border:1px solid #e2e8f0;
    border-radius:6px; padding:.45rem .9rem; margin:2px 0;
    display:flex; justify-content:space-between; align-items:center;
    font-size:.79rem; color:#334155;
}

/* ── Misc ───────────────────────────────────────────── */
header    { display: none !important; }
#MainMenu { display: none !important; }
footer    { display: none !important; }

/* ── Page nav buttons ───────────────────────────────── */
.nav-wrap {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: .6rem .8rem .5rem;
    margin-bottom: .8rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.nav-wrap .stButton > button {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    color: #475569 !important;
    font-size: .77rem !important;
    font-weight: 500 !important;
    padding: .3rem .5rem !important;
    width: 100% !important;
    transition: all .12s !important;
}
.nav-wrap .stButton > button:hover {
    background: #eff6ff !important;
    border-color: #93c5fd !important;
    color: #1d4ed8 !important;
}
.nav-wrap .nav-active > button {
    background: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}


.stTabs [data-baseweb="tab"] { font-size:0.82rem; font-weight:600; color:#334155; }
.stDataFrame { border-radius:8px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)


# ── Plotly light-theme helper ──────────────────────────────────────────────────
def _pl(**kw):
    base = dict(
        template="plotly_white",
        paper_bgcolor=C_SURFACE,
        plot_bgcolor="#f8fafc",
        font=dict(color="#334155", size=11),
        margin=dict(l=48, r=20, t=44, b=40),
        colorway=[C_PRIMARY, C_TEAL, C_GREEN, C_AMBER, C_RED, C_PURPLE, C_SLATE],
    )
    base.update(kw)
    return base


# ── KPI card helper ────────────────────────────────────────────────────────────
def kpi(col, label, value, sub, color):
    col.markdown(
        f'<div class="kpi-card" style="border-top-color:{color}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ── Hospital connection state ──────────────────────────────────────────────────
import hospital_bridge as hb

if "hospital_connected" not in st.session_state:
    st.session_state["hospital_connected"] = False
if "results_synthetic" not in st.session_state:
    st.session_state["results_synthetic"] = None
if "results_hospital" not in st.session_state:
    st.session_state["results_hospital"] = None

hosp_available = hb.is_available()
hosp_connected = st.session_state["hospital_connected"]


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div style="font-size:1rem;font-weight:700;color:#f1f5f9;padding:.4rem 0 .05rem">'
    'Quantum IoMT</div>'
    '<div style="font-size:.7rem;color:#475569;margin-bottom:.6rem">'
    'Hierarchical Diagnostic Framework</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

PAGES = [
    "Pipeline Overview",
    "Biosignal Input",
    "ANUKF Preprocessing",
    "Q-Flex ViT  —  Feature Extraction",
    "BMOCO  —  Feature Selection",
    "HQAN + VQC  —  Prediction",
    "Adaptive SHARP  —  Explainability",
    "Clinical Alerts",
    "Hospital Comparison",
]
PAGE_SHORT = [
    "Overview",
    "Biosignals",
    "ANUKF",
    "Q-Flex ViT",
    "BMOCO",
    "HQAN + VQC",
    "Adaptive SHARP",
    "Alerts",
    "Comparison",
]

if "page_idx" not in st.session_state:
    st.session_state["page_idx"] = 0

# ── Hospital connection panel ──────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.72rem;font-weight:600;color:#64748b;'
    'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">'
    'Hospital Connection</div>',
    unsafe_allow_html=True,
)

if not hosp_available:
    st.sidebar.markdown(
        '<div style="background:#1c1010;border:1px solid #7f1d1d;border-radius:6px;'
        'padding:.5rem .8rem;font-size:.75rem;color:#fca5a5">'
        '&#9679; MediCore offline — start the hospital dashboard (port 8502) first.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    if hosp_connected:
        stats = hb.get_stats()
        st.sidebar.markdown(
            f'<div style="background:#052e16;border:1px solid #166534;border-radius:6px;'
            f'padding:.55rem .8rem;font-size:.74rem;color:#4ade80">'
            f'&#9679; Connected to MediCore HMS<br>'
            f'<span style="color:#86efac">'
            f'{stats.get("n_devices","?")} devices &nbsp;|&nbsp; '
            f'{stats.get("n_depts","?")} depts &nbsp;|&nbsp; '
            f'{stats.get("n_alerts","?")} alerts</span></div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Disconnect from Hospital"):
            st.session_state["hospital_connected"] = False
            st.rerun()
    else:
        st.sidebar.markdown(
            '<div style="background:#0f172a;border:1px solid #334155;border-radius:6px;'
            'padding:.55rem .8rem;font-size:.74rem;color:#64748b">'
            '&#9675; Not connected &nbsp;—&nbsp; using synthetic data</div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Connect to MediCore HMS"):
            st.session_state["hospital_connected"] = True
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.72rem;font-weight:600;color:#64748b;'
    'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">'
    'Pipeline Settings</div>',
    unsafe_allow_html=True,
)

# When connected, patient slider is disabled (count comes from hospital)
if hosp_connected:
    n_patients = None
    st.sidebar.markdown(
        '<div style="font-size:.74rem;color:#64748b;margin-bottom:.4rem">'
        'Patient count: from hospital DB</div>',
        unsafe_allow_html=True,
    )
else:
    n_patients = st.sidebar.slider("Patients (synthetic)", 30, 100, 60, step=10)

fast_mode = st.sidebar.checkbox("Fast mode (fewer iterations)", value=True)
seed      = st.sidebar.number_input("Random seed", value=42, step=1)

# Data source badge
src_label = "MediCore HMS" if hosp_connected else "Synthetic data"
src_color = "#16a34a"      if hosp_connected else "#64748b"
st.sidebar.markdown(
    f'<div style="font-size:.72rem;color:{src_color};margin-bottom:.5rem">'
    f'Data source: <strong>{src_label}</strong></div>',
    unsafe_allow_html=True,
)

run_btn = st.sidebar.button("Run Pipeline")  # also triggered by main_run below

# Status indicators
if hosp_connected and st.session_state.get("results_hospital"):
    st.sidebar.markdown(
        '<div style="text-align:center;font-size:.74rem;color:#16a34a;margin-top:.3rem">'
        '&#10003; Hospital pipeline complete</div>',
        unsafe_allow_html=True,
    )
if st.session_state.get("results_synthetic"):
    st.sidebar.markdown(
        '<div style="text-align:center;font-size:.74rem;color:#2563eb;margin-top:.3rem">'
        '&#10003; Synthetic pipeline complete</div>',
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.65rem;color:#334155">Binu — PhD Research &nbsp;·&nbsp; 2026</div>',
    unsafe_allow_html=True,
)


# ── Top navigation bar (always visible, independent of sidebar) ───────────────
st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
_ROW1 = PAGE_SHORT[:5]   # Overview · Biosignals · ANUKF · Q-Flex ViT · BMOCO
_ROW2 = PAGE_SHORT[5:]   # HQAN+VQC · Adaptive SHARP · Alerts · Comparison
_cur  = st.session_state["page_idx"]

_r1_cols = st.columns(len(_ROW1))
for _i, (_col, _label) in enumerate(zip(_r1_cols, _ROW1)):
    _cls = "nav-active" if _cur == _i else ""
    with _col:
        st.markdown(f'<div class="{_cls}">', unsafe_allow_html=True)
        if st.button(_label, key=f"nav_{_i}"):
            st.session_state["page_idx"] = _i
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

_r2_cols = st.columns(len(_ROW2))
for _i, (_col, _label) in enumerate(zip(_r2_cols, _ROW2), start=len(_ROW1)):
    _cls = "nav-active" if _cur == _i else ""
    with _col:
        st.markdown(f'<div class="{_cls}">', unsafe_allow_html=True)
        if st.button(_label, key=f"nav_{_i}"):
            st.session_state["page_idx"] = _i
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Action bar (below nav, always visible) ────────────────────────────────────
_a1, _a2, _a3, _a4 = st.columns([3, 2, 2, 3])
with _a2:
    if hosp_available:
        if hosp_connected:
            if st.button("Disconnect HMS", key="main_disconnect", use_container_width=True):
                st.session_state["hospital_connected"] = False
                st.rerun()
        else:
            if st.button("Connect to HMS", key="main_connect", use_container_width=True):
                st.session_state["hospital_connected"] = True
                st.rerun()
    else:
        st.markdown(
            '<div style="font-size:.72rem;color:#ef4444;padding:.35rem 0">HMS offline</div>',
            unsafe_allow_html=True,
        )
with _a3:
    run_btn_main = st.button(
        "Run Pipeline", key="main_run", type="primary", use_container_width=True
    )

# Status dot
_src_color = "#16a34a" if hosp_connected else "#64748b"
_src_label  = "MediCore HMS" if hosp_connected else "Synthetic data"
_a1.markdown(
    f'<div style="font-size:.72rem;color:{_src_color};padding:.35rem 0">'
    f'&#9679; {_src_label}</div>',
    unsafe_allow_html=True,
)

st.markdown('<hr style="margin:.3rem 0 .8rem;border-color:#e2e8f0">', unsafe_allow_html=True)
page = PAGES[st.session_state["page_idx"]]


# ── Pipeline runner ────────────────────────────────────────────────────────────
def _execute_pipeline(seed, fast_mode, hospital_patients=None, n_patients=60):
    from pipeline import run_pipeline
    status = st.empty()

    def cb(step, msg):
        pct = int(step / 9 * 100)
        status.markdown(
            f'<div class="a-info" style="padding:.5rem 1rem">'
            f'Step {step}/8 &nbsp;—&nbsp; {msg} &nbsp; ({pct}%)</div>',
            unsafe_allow_html=True,
        )

    result = run_pipeline(
        n_patients=n_patients, seed=seed,
        bmoco_iters=8 if fast_mode else 20,
        rbwka_iters=12 if fast_mode else 30,
        progress_cb=cb,
        override_patients=hospital_patients,
    )
    status.empty()
    return result


if run_btn or run_btn_main:
    with st.spinner("Initialising quantum circuits…"):
        if hosp_connected:
            patients, dept_rows = hb.fetch_hospital_patients(seed=int(seed))
            result = _execute_pipeline(int(seed), fast_mode,
                                       hospital_patients=patients,
                                       n_patients=len(patients))
            result["_source"]    = "hospital"
            result["_dept_rows"] = dept_rows
            st.session_state["results_hospital"] = result
        else:
            result = _execute_pipeline(int(seed), fast_mode,
                                       n_patients=n_patients or 60)
            result["_source"] = "synthetic"
            st.session_state["results_synthetic"] = result

# Active result = hospital if connected, else synthetic
R = (st.session_state["results_hospital"] if hosp_connected
     else st.session_state["results_synthetic"])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1  —  Pipeline Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == PAGES[0]:
    st.markdown('<div class="page-title">Pipeline Overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Binu\'s hierarchical quantum-enhanced IoMT diagnostic framework '
        '— 9 integrated stages from raw biosignals to clinical alerts.</div>',
        unsafe_allow_html=True,
    )

    # Stage pipeline chart
    stage_labels = [
        "Data\nInput", "ANUKF\nFilter", "Q-Flex\nViT", "BMOCO\nSelect",
        "HQAN\nAttention", "DQA + DRA\nDynamic", "RBWKA\nOptimise",
        "VQC\nPredict", "Adaptive\nSHARP",
    ]
    stage_colors = [C_TEAL, C_PRIMARY, C_PURPLE, C_GREEN,
                    C_PURPLE, C_PRIMARY, C_AMBER, C_PURPLE, C_GREEN]

    fig = go.Figure()
    for i, (lbl, col) in enumerate(zip(stage_labels, stage_colors)):
        fig.add_trace(go.Scatter(
            x=[i], y=[0], mode="markers+text",
            marker=dict(size=58, color=col, opacity=0.9,
                        line=dict(color="#ffffff", width=2)),
            text=[lbl], textposition="bottom center",
            textfont=dict(size=9, color=C_TEXT),
            hovertext=lbl, hoverinfo="text", showlegend=False,
        ))
        if i < len(stage_labels) - 1:
            fig.add_annotation(
                x=i + 0.52, y=0, ax=i + 0.48, ay=0,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.4,
                arrowcolor="#94a3b8", arrowwidth=2,
            )

    fig.update_layout(
        height=210, showlegend=False,
        xaxis=dict(visible=False, range=[-0.6, len(stage_labels) - 0.4]),
        yaxis=dict(visible=False, range=[-0.9, 0.45]),
        **_pl(margin=dict(l=10, r=10, t=10, b=95), plot_bgcolor=C_BG),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Pipeline Stages",    "9",  "End-to-end integrated",         C_PRIMARY)
    kpi(c2, "Quantum Circuits",   "2",  "VQC + Q-Flex attention",        C_PURPLE)
    kpi(c3, "Biosignal Inputs",   "5",  "ECG · BP · Temp · EEG · SpO2", C_TEAL)
    kpi(c4, "Novel Algorithms",   "5",  "ANUKF · BMOCO · HQAN · RBWKA · VQC", C_GREEN)

    # Research gap table
    st.markdown('<div class="sec">Research Gaps Addressed</div>', unsafe_allow_html=True)
    import pandas as pd
    df = pd.DataFrame([
        ["Noisy biosignals",        "ANUKF adaptive non-linear filtering",     "Classical low-pass / basic Kalman"],
        ["Feature redundancy",      "BMOCO binary multi-objective optimisation","PCA / manual selection"],
        ["Computational overhead",  "DRA dynamic resource allocation",          "Fixed-size classical models"],
        ["Diagnosis accuracy",      "VQC + HQAN quantum-enhanced inference",    "Classical CNN / LSTM"],
        ["No explainability",       "Adaptive SHARP context-aware XAI",         "Black-box predictions"],
        ["Isolated research silos", "Single integrated 9-stage pipeline",       "Signal / optimise / predict separately"],
    ], columns=["Research Gap", "This Framework", "Existing Approaches"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Algorithm reference
    st.markdown('<div class="sec">Novel Algorithm Reference</div>', unsafe_allow_html=True)
    df2 = pd.DataFrame([
        ["ANUKF",         "Adaptive Neural Unscented Kalman Filter",  "Stage 2",  "Biosignal denoising"],
        ["Q-Flex ViT",    "Quantum Flexibility Vision Transformer",   "Stage 3",  "Feature extraction"],
        ["BMOCO",         "Binary Multi-Objective Cheetah Optimisation","Stage 4","Feature selection"],
        ["HQAN",          "Hybrid Quantum Attention Network",          "Stage 5",  "Attention-based analysis"],
        ["DQA",           "Dynamic Quantum Attention",                 "Stage 5",  "Adaptive attention weighting"],
        ["DRA",           "Dynamic Resource Allocation",               "Stage 5",  "Runtime resource management"],
        ["RBWKA",         "Revamped Black-Winged Kite Algorithm",      "Stage 6",  "VQC weight optimisation"],
        ["VQC",           "Variational Quantum Circuits",              "Stage 7",  "Quantum-classical prediction"],
        ["Adaptive SHARP","Adaptive SHAP",                             "Stage 8",  "Clinical explainability"],
    ], columns=["Acronym", "Full Name", "Stage", "Role"])
    st.dataframe(df2, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2  —  Biosignal Input
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[1]:
    st.markdown('<div class="stage-tag">Stage 1  —  Data Collection</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Biosignal Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Multimodal physiological data streams: ECG, Blood Pressure, Temperature, EEG, and Pulse Oximetry.</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Click <strong>Run Full Pipeline</strong> in the sidebar to load patient data.</div>', unsafe_allow_html=True)
    else:
        patients = R["patients"]
        pid = st.selectbox(
            "Select patient",
            range(len(patients)),
            format_func=lambda i: f"Patient {i:03d}  —  {'Abnormal' if patients[i].label else 'Normal'}",
        )
        p = patients[pid]

        if p.label:
            st.markdown('<div class="a-critical"><strong>Ground truth: ABNORMAL</strong> — Patient flags active diagnostic concern.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="a-normal"><strong>Ground truth: NORMAL</strong> — All vitals within expected range.</div>', unsafe_allow_html=True)

        t = np.arange(len(p.ecg))
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=["ECG", "Systolic Blood Pressure",
                            "Body Temperature", "EEG",
                            "SpO2", "Diastolic Blood Pressure"],
            vertical_spacing=0.12, horizontal_spacing=0.1,
        )
        signals = [
            (1, 1, p.ecg,  C_PRIMARY, "mV"),
            (1, 2, p.sbp,  C_RED,     "mmHg"),
            (2, 1, p.temp, C_AMBER,   "deg C"),
            (2, 2, p.eeg,  C_PURPLE,  "uV"),
            (3, 1, p.spo2, C_GREEN,   "%"),
            (3, 2, p.dbp,  C_TEAL,    "mmHg"),
        ]
        for r, c, sig, col, unit in signals:
            fig.add_trace(
                go.Scatter(x=t, y=sig, line=dict(color=col, width=1.3),
                           name=unit, showlegend=False),
                row=r, col=c,
            )
        fig.update_layout(height=520, **_pl(title=f"Patient {pid:03d}  —  Raw Biosignal Streams"))
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        kpi(c1, "Heart Rate (ECG)", f"{60 + p.label*28 + int(np.std(p.ecg)*4)}", "bpm", C_PRIMARY)
        kpi(c2, "Systolic BP",      f"{np.mean(p.sbp):.1f}", "mmHg", C_RED)
        kpi(c3, "Temperature",      f"{np.mean(p.temp):.2f}", "deg C", C_AMBER)
        kpi(c4, "SpO2",             f"{np.mean(p.spo2):.1f}", "%",    C_GREEN)
        kpi(c5, "EEG Beta Power",   f"{np.var(p.eeg):.3f}", "uV^2",  C_PURPLE)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3  —  ANUKF Preprocessing
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[2]:
    st.markdown('<div class="stage-tag">Stage 2  —  Preprocessing</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">ANUKF  —  Adaptive Neural Unscented Kalman Filter</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Removes noise and uncertainty from biosignals using non-linear state estimation with per-signal adaptive noise covariance (Q, R) tuned by a neural component.</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        sig_choice = st.selectbox(
            "Signal channel",
            ["ecg", "sbp", "dbp", "temp", "eeg", "spo2"],
            format_func=lambda s: s.upper(),
        )
        sample = R["anukf_sample"][sig_choice]
        t = np.arange(len(sample["raw"]))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=sample["raw"], name="Raw (noisy)",
                                  line=dict(color=C_RED, width=1.1, dash="dot")))
        fig.add_trace(go.Scatter(x=t, y=sample["filtered"], name="ANUKF filtered",
                                  line=dict(color=C_PRIMARY, width=2.2)))
        fig.update_layout(height=360,
                          **_pl(title=f"ANUKF  —  {sig_choice.upper()}  Signal Denoising",
                                legend=dict(orientation="h", y=1.08)))
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4 = st.columns(4)
        snr = sample["snr_db"]
        kpi(c1, "SNR",             f"{snr:+.1f} dB", "Signal-to-noise ratio",   C_PRIMARY if snr > 0 else C_RED)
        kpi(c2, "Process Noise Q", f"{sample['Q']:.2e}", "Adaptive (auto-tuned)", C_PURPLE)
        kpi(c3, "Meas. Noise R",   f"{sample['R']:.2e}", "Adaptive (auto-tuned)", C_TEAL)
        kpi(c4, "Noise Removed",   f"{np.std(sample['residual']):.4f}", "Residual std", C_AMBER)

        # Residual
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=t, y=sample["residual"], name="Residual",
                                   line=dict(color=C_SLATE, width=1.0),
                                   fill="tozeroy", fillcolor="rgba(100,116,139,0.12)"))
        fig2.update_layout(height=200, **_pl(title="Residual Noise (Raw  minus  Filtered)"))
        st.plotly_chart(fig2, use_container_width=True)

        # SNR across all signals
        st.markdown('<div class="sec">SNR Improvement Across All Signal Channels</div>', unsafe_allow_html=True)
        snr_map = {k: R["anukf_sample"][k]["snr_db"] for k in R["anukf_sample"]}
        fig3 = go.Figure(go.Bar(
            x=list(snr_map.keys()), y=list(snr_map.values()),
            marker_color=[C_GREEN if v > 0 else C_RED for v in snr_map.values()],
            text=[f"{v:+.1f} dB" for v in snr_map.values()],
            textposition="outside", textfont=dict(size=11, color=C_TEXT),
        ))
        fig3.update_layout(height=280, **_pl(title="ANUKF SNR by Channel"))
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4  —  Q-Flex ViT
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[3]:
    st.markdown('<div class="stage-tag">Stage 3  —  Feature Extraction</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Q-Flex ViT  —  Quantum Flexibility Vision Transformer</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Extracts multimodal features using a hybrid quantum-classical Vision Transformer. Quantum attention heads compute cross-entangled similarity between query and key projections.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Quantum Attention Circuit", "Feature Space Analysis"])

    with tab1:
        from quantum_circuits import draw_attention_circuit
        import matplotlib
        import matplotlib.pyplot as plt
        matplotlib.use("Agg")
        with st.spinner("Rendering circuit diagram…"):
            fig_circ = draw_attention_circuit()
        st.pyplot(fig_circ, use_container_width=True)
        st.markdown(
            '<div class="surface">'
            '<strong>Circuit description</strong><br>'
            'Wires 0-1 encode the <em>Query</em> projection via angle embedding. '
            'Wires 2-3 encode the <em>Key</em> projection. '
            'Hadamard + CNOT gates create cross-entanglement between query and key subspaces. '
            'Controlled-RZ gates introduce phase-shifted attention weights. '
            'Final Z-basis measurements yield four attention coefficients that weight the feature vector.'
            '</div>',
            unsafe_allow_html=True,
        )

    with tab2:
        if R is None:
            st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
        else:
            import pandas as pd
            X = R["X_norm"]
            y = R["y"]
            names = R["feature_names"]

            # Top-feature correlation with label
            corr = np.abs(np.corrcoef(X.T, y)[:-1, -1])
            top18 = np.argsort(corr)[-18:][::-1]
            corr_mat = np.corrcoef(X[:, top18].T)
            fig = px.imshow(
                corr_mat,
                x=[names[i] for i in top18],
                y=[names[i] for i in top18],
                color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                title="Feature Correlation Matrix (top-18 label-correlated features)",
            )
            fig.update_layout(height=420, **_pl())
            st.plotly_chart(fig, use_container_width=True)

            # Class separation scatter
            top2 = np.argsort(corr)[-2:]
            fig2 = px.scatter(
                x=X[:, top2[1]], y=X[:, top2[0]],
                color=["Abnormal" if yi else "Normal" for yi in y],
                color_discrete_map={"Normal": C_GREEN, "Abnormal": C_RED},
                labels={"x": names[top2[1]], "y": names[top2[0]]},
                title="Top-2 Features  —  Class Separation",
            )
            fig2.update_layout(height=340, **_pl())
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5  —  BMOCO Feature Selection
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[4]:
    st.markdown('<div class="stage-tag">Stage 4  —  Feature Selection</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">BMOCO  —  Binary Multi-Objective Cheetah Optimisation</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Selects the optimal feature subset by simultaneously maximising diagnostic accuracy and minimising feature count. Three hunting phases: Scout (global), Chase (convergence), Attack (local refinement).</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        sel_idx  = R["sel_idx"]
        history  = R["bmoco_history"]
        n_total  = len(R["feature_names"])
        n_sel    = len(sel_idx)

        c1, c2, c3, c4 = st.columns(4)
        kpi(c1, "Features Selected", f"{n_sel}",
            f"of {n_total} total", C_PRIMARY)
        kpi(c2, "Dimensionality Reduction",
            f"{100*(1 - n_sel/n_total):.0f}%",
            "Feature count reduced", C_GREEN)
        kpi(c3, "Best Fitness",
            f"{R['bmoco_best_fitness']:.4f}",
            "Accuracy minus feature penalty", C_PURPLE)
        kpi(c4, "Iterations", str(len(history)), "Cheetah search steps", C_TEAL)

        tab1, tab2 = st.tabs(["Convergence", "Feature Map"])

        with tab1:
            iters = [h["iteration"] for h in history]
            fits  = [h["best_fitness"] for h in history]
            nsel  = [h["n_selected"] for h in history]
            fig = make_subplots(rows=2, cols=1,
                                subplot_titles=["Fitness Convergence", "Number of Selected Features"],
                                vertical_spacing=0.15)
            fig.add_trace(go.Scatter(x=iters, y=fits, name="Fitness",
                                      line=dict(color=C_PRIMARY, width=2),
                                      fill="tozeroy", fillcolor="rgba(37,99,235,0.08)"),
                          row=1, col=1)
            fig.add_trace(go.Scatter(x=iters, y=nsel, name="Features",
                                      line=dict(color=C_AMBER, width=2),
                                      fill="tozeroy", fillcolor="rgba(217,119,6,0.08)"),
                          row=2, col=1)
            fig.update_layout(height=400, showlegend=False,
                              **_pl(title="BMOCO Cheetah Optimisation Convergence"))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            import pandas as pd
            sel_set = set(sel_idx)
            df = pd.DataFrame(
                [(fn, "Selected" if i in sel_set else "Removed")
                 for i, fn in enumerate(R["feature_names"])],
                columns=["Feature", "Status"],
            )
            # Highlight selected vs removed
            def _style(val):
                if val == "Selected":
                    return "background-color:#f0fdf4;color:#15803d;font-weight:600"
                return "background-color:#fef2f2;color:#991b1b"
            st.dataframe(df.style.applymap(_style, subset=["Status"]),
                         height=420, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6  —  HQAN + VQC Prediction
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[5]:
    st.markdown('<div class="stage-tag">Stages 5–7  —  HQAN  ·  RBWKA  ·  VQC</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">HQAN + VQC  —  Quantum Prediction</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Hybrid Quantum Attention Network analyses selected features; RBWKA optimises VQC gate parameters; Variational Quantum Circuit produces the final diagnosis probability.</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["VQC Circuit", "RBWKA Optimisation", "Attention Map", "Results"])

        with tab1:
            from quantum_circuits import draw_vqc_circuit
            import matplotlib
            matplotlib.use("Agg")
            with st.spinner("Rendering VQC diagram…"):
                fig_vqc = draw_vqc_circuit()
            st.pyplot(fig_vqc, use_container_width=True)
            st.markdown(
                '<div class="surface">'
                '<strong>VQC Architecture  —  4 qubits, 3 layers</strong><br>'
                '<ul style="margin:.4rem 0 0 1rem;color:#334155;font-size:.82rem">'
                '<li><strong>Angle Embedding</strong> — input features encoded as qubit rotation angles (RY)</li>'
                '<li><strong>Strongly Entangling Layers</strong> — parametrised RZ/RY/RX gates with full CNOT entanglement</li>'
                '<li><strong>Measurement</strong> — expectation value Z0 x Z1 mapped to [0, 1] probability</li>'
                '<li><strong>Optimised by RBWKA</strong> — kite algorithm searches optimal gate angles without gradients</li>'
                '</ul></div>',
                unsafe_allow_html=True,
            )

        with tab2:
            hist = R["rbwka_history"]
            if hist:
                iters = [h["iteration"] for h in hist]
                fits  = [h["best_fitness"] for h in hist]
                fig = go.Figure(go.Scatter(
                    x=iters, y=fits, name="Best accuracy",
                    line=dict(color=C_AMBER, width=2.2),
                    fill="tozeroy", fillcolor="rgba(217,119,6,0.08)",
                ))
                fig.add_hline(y=R["rbwka_best_fitness"], line_dash="dash",
                              line_color=C_GREEN,
                              annotation_text=f"Best: {R['rbwka_best_fitness']:.3f}",
                              annotation_font_color=C_GREEN)
                fig.update_layout(height=340,
                                  **_pl(title="RBWKA  —  VQC Weight Optimisation Convergence"))
                st.plotly_chart(fig, use_container_width=True)
            c1, c2 = st.columns(2)
            kpi(c1, "Final Training Accuracy", f"{R['rbwka_best_fitness']*100:.1f}%",
                "On optimisation subset", C_GREEN)
            kpi(c2, "RBWKA Iterations", str(len(hist)), "Kite search steps", C_AMBER)

        with tab3:
            attn = R["hqan_attn"]
            n_show = min(50, len(attn))
            fig = px.imshow(
                attn[:n_show].T,
                labels=dict(x="Patient", y="Attention Head", color="Weight"),
                color_continuous_scale="Blues",
                title="HQAN Quantum Attention Weights",
            )
            fig.update_layout(height=280, **_pl())
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            probs = R["probs"]
            preds = R["preds"]
            y     = R["y"]

            c1, c2, c3, c4 = st.columns(4)
            kpi(c1, "Accuracy",  f"{R['accuracy']*100:.1f}%",  "", C_GREEN)
            kpi(c2, "Precision", f"{R['precision']*100:.1f}%", "", C_PRIMARY)
            kpi(c3, "Recall",    f"{R['recall']*100:.1f}%",    "", C_AMBER)
            kpi(c4, "F1 Score",  f"{R['f1']*100:.1f}%",        "", C_PURPLE)

            col_a, col_b = st.columns(2)

            with col_a:
                fig2 = go.Figure()
                fig2.add_trace(go.Histogram(x=probs[y==0], name="Normal",
                                             nbinsx=20, marker_color=C_GREEN, opacity=0.75))
                fig2.add_trace(go.Histogram(x=probs[y==1], name="Abnormal",
                                             nbinsx=20, marker_color=C_RED, opacity=0.75))
                fig2.add_vline(x=0.5, line_dash="dash", line_color=C_AMBER,
                               annotation_text="Threshold")
                fig2.update_layout(barmode="overlay", height=320,
                                   **_pl(title="VQC Output Probability Distribution"))
                st.plotly_chart(fig2, use_container_width=True)

            with col_b:
                cm = R["confusion"]
                fig3 = px.imshow(
                    [[cm["TN"], cm["FP"]], [cm["FN"], cm["TP"]]],
                    x=["Pred Normal", "Pred Abnormal"],
                    y=["True Normal", "True Abnormal"],
                    text_auto=True, color_continuous_scale="Blues",
                    title="Confusion Matrix",
                )
                fig3.update_layout(height=320, **_pl())
                st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7  —  Adaptive SHARP
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[6]:
    st.markdown('<div class="stage-tag">Stage 8  —  Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Adaptive SHARP  —  Clinical Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Adaptive SHAP adapts explanation granularity to anomaly severity. Features above the adaptive threshold are flagged as clinically significant.</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        importance = R["importance"]
        feat_names = R["sharp_feature_names"]
        threshold  = R["adaptive_threshold"]
        sig_mask   = R["significant_features"]
        order      = R["importance_order"]

        # Global importance bar chart
        colors = [C_PRIMARY if sig_mask[i] else C_SLATE for i in order]
        fig = go.Figure(go.Bar(
            x=importance[order],
            y=[feat_names[i] for i in order],
            orientation="h",
            marker_color=colors,
            text=[f"{importance[i]:.4f}" for i in order],
            textposition="outside",
            textfont=dict(size=10, color=C_TEXT),
        ))
        fig.add_vline(x=threshold, line_dash="dash", line_color=C_AMBER,
                      annotation_text=f"Adaptive threshold = {threshold:.4f}",
                      annotation_font_color=C_AMBER)
        fig.update_layout(
            height=max(320, len(feat_names) * 22),
            **_pl(title="Adaptive SHARP  —  Global Feature Importance",
                  xaxis_title="Permutation Importance Score",
                  yaxis_title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns([1, 1])

        with col_a:
            st.markdown('<div class="sec">Significant Features</div>', unsafe_allow_html=True)
            sig_feats = [(feat_names[i], float(importance[i]))
                         for i in range(len(feat_names)) if sig_mask[i]]
            sig_feats.sort(key=lambda x: -x[1])
            if sig_feats:
                max_imp = sig_feats[0][1]
                sensor_colors = {
                    "ECG": C_PRIMARY, "SBP": C_RED, "DBP": C_TEAL,
                    "Temp": C_AMBER,  "EEG": C_PURPLE, "SpO2": C_GREEN,
                }
                for name, imp in sig_feats:
                    sensor = name.split("_")[0]
                    clr = sensor_colors.get(sensor, C_SLATE)
                    bar_px = int(imp / (max_imp + 1e-9) * 160)
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;margin:4px 0">'
                        f'<span style="color:{C_TEXT};width:120px;font-size:.78rem">{name}</span>'
                        f'<div style="background:{clr};width:{bar_px}px;height:10px;'
                        f'border-radius:3px;flex-shrink:0"></div>'
                        f'<span style="color:{C_MUTED};font-size:.72rem">{imp:.4f}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div class="a-warning">No features exceeded the adaptive threshold.</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="sec">Clinical Interpretation</div>', unsafe_allow_html=True)
            interp = {
                "ECG":  ("ECG patterns dominate prediction.",  "Possible arrhythmia or cardiac event — request 12-lead ECG."),
                "SBP":  ("Systolic BP is the key driver.",     "Hypertension or hypotension risk — monitor haemodynamics."),
                "DBP":  ("Diastolic pressure leads.",          "Possible diastolic dysfunction or vascular issue."),
                "Temp": ("Temperature is the primary signal.", "Infection or fever — consider inflammatory markers."),
                "EEG":  ("EEG activity drives prediction.",    "Neurological event — neurologist review recommended."),
                "SpO2": ("Oxygen saturation is critical.",     "Respiratory compromise — hypoxia risk — immediate review."),
            }
            top_sensor = sig_feats[0][0].split("_")[0] if sig_feats else None
            if top_sensor and top_sensor in interp:
                title, detail = interp[top_sensor]
                st.markdown(
                    f'<div class="a-info"><strong>{title}</strong><br>{detail}</div>',
                    unsafe_allow_html=True,
                )

            # Sensor-group importance
            sensor_imp = {}
            for name, imp in zip(feat_names, importance):
                s = name.split("_")[0]
                sensor_imp[s] = sensor_imp.get(s, 0) + imp
            fig2 = go.Figure(go.Pie(
                labels=list(sensor_imp.keys()),
                values=list(sensor_imp.values()),
                hole=0.45,
                marker_colors=[C_PRIMARY, C_RED, C_TEAL, C_AMBER, C_PURPLE, C_GREEN],
                textinfo="label+percent",
                textfont_size=11,
            ))
            fig2.update_layout(
                height=300,
                showlegend=False,
                **_pl(title="Importance by Sensor Group",
                      margin=dict(l=20, r=20, t=44, b=20)),
            )
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8  —  Clinical Alerts
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[7]:
    st.markdown('<div class="stage-tag">Stage 9  —  Output</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Clinical Alerts and Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Real-time diagnostic risk scores from the VQC. Patients are triaged into three risk bands: Critical (p > 0.75), Warning (0.50–0.75), Normal (p <= 0.50).</div>', unsafe_allow_html=True)

    if R is None:
        st.markdown('<div class="a-info">Run the pipeline first.</div>', unsafe_allow_html=True)
    else:
        probs   = R["probs"]
        preds   = R["preds"]
        y       = R["y"]
        patients = R["patients"]

        n_crit = int(np.sum(probs > 0.75))
        n_warn = int(np.sum((probs > 0.5) & (probs <= 0.75)))
        n_norm = int(np.sum(probs <= 0.5))

        c1, c2, c3, c4 = st.columns(4)
        kpi(c1, "Critical",        str(n_crit), "p > 0.75  —  Immediate review", C_RED)
        kpi(c2, "Warning",         str(n_warn), "p 0.50–0.75  —  Monitor closely", C_AMBER)
        kpi(c3, "Normal",          str(n_norm), "p <= 0.50  —  Stable", C_GREEN)
        kpi(c4, "VQC Accuracy",    f"{R['accuracy']*100:.1f}%", "Quantum diagnosis", C_PRIMARY)

        col_a, col_b = st.columns([1, 1])

        with col_a:
            st.markdown('<div class="sec">Patient Alert Board  (top 20 by risk)</div>', unsafe_allow_html=True)
            rows = sorted(zip(range(len(patients)), probs, preds, y), key=lambda x: -x[1])
            for pid, prob, pred, gt in rows[:20]:
                if prob > 0.75:
                    css, status = "a-critical", "CRITICAL"
                elif prob > 0.5:
                    css, status = "a-warning",  "WARNING"
                else:
                    css, status = "a-normal",   "NORMAL"
                correct = "Correct" if pred == gt else "Incorrect"
                gt_lbl  = "Abnormal" if gt else "Normal"
                st.markdown(
                    f'<div class="{css}">'
                    f'<span style="font-weight:600">Patient {pid:03d}</span>'
                    f'&nbsp;&nbsp;{status}&nbsp;&nbsp;'
                    f'<span style="font-size:.78rem">p = {prob:.3f}'
                    f'&nbsp;|&nbsp;GT: {gt_lbl}'
                    f'&nbsp;|&nbsp;{correct}</span></div>',
                    unsafe_allow_html=True,
                )

        with col_b:
            # Risk distribution violin
            fig = go.Figure()
            for lbl, mask, col in [("Normal", y==0, C_GREEN), ("Abnormal", y==1, C_RED)]:
                fig.add_trace(go.Violin(
                    y=probs[mask], name=lbl,
                    box_visible=True, meanline_visible=True,
                    fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.15)",
                    line_color=col,
                ))
            fig.add_hline(y=0.5, line_dash="dash", line_color=C_AMBER,
                          annotation_text="Decision boundary")
            fig.add_hline(y=0.75, line_dash="dot", line_color=C_RED,
                          annotation_text="Critical threshold")
            fig.update_layout(height=360,
                              **_pl(title="VQC Risk Score Distribution by Class"))
            st.plotly_chart(fig, use_container_width=True)

            # Summary donut
            fig2 = go.Figure(go.Pie(
                labels=["Critical", "Warning", "Normal"],
                values=[n_crit, n_warn, n_norm],
                hole=0.5,
                marker_colors=[C_RED, C_AMBER, C_GREEN],
                textinfo="label+value",
                textfont_size=12,
            ))
            fig2.update_layout(
                height=280, showlegend=False,
                **_pl(title="Patient Risk Distribution",
                      margin=dict(l=20, r=20, t=44, b=10)),
            )
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9  —  Hospital Comparison
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[8]:
    st.markdown('<div class="page-title">Hospital Comparison</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">'
        'Side-by-side comparison: MediCore HMS traditional monitoring vs the Quantum IoMT '
        'diagnostic pipeline. Run the pipeline once with each data source to populate both columns.'
        '</div>',
        unsafe_allow_html=True,
    )

    R_syn  = st.session_state.get("results_synthetic")
    R_hosp = st.session_state.get("results_hospital")

    # Connection guide
    if not hosp_available:
        st.markdown(
            '<div class="a-critical">'
            '<strong>MediCore HMS is not running.</strong><br>'
            'Start the hospital dashboard at <code>http://localhost:8502</code> first, '
            'then return here and click <strong>Connect to MediCore HMS</strong> in the sidebar.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        # Step-by-step guide
        steps_done = []
        if R_syn:  steps_done.append("synthetic")
        if R_hosp: steps_done.append("hospital")

        guide = [
            ("1", "Disconnect from hospital (sidebar)", "synthetic" in steps_done or not hosp_connected),
            ("2", "Click Run Pipeline  —  runs on synthetic patient data", "synthetic" in steps_done),
            ("3", "Click Connect to MediCore HMS (sidebar)", "hospital" in steps_done or hosp_connected),
            ("4", "Click Run Pipeline  —  runs on real hospital device data", "hospital" in steps_done),
            ("5", "Review the comparison below", len(steps_done) == 2),
        ]
        st.markdown('<div class="sec">Steps to compare</div>', unsafe_allow_html=True)
        for num, txt, done in guide:
            icon  = "&#10003;" if done else "&#9675;"
            color = "#16a34a"  if done else "#64748b"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:.6rem;'
                f'margin:3px 0;font-size:.82rem;color:#334155">'
                f'<span style="color:{color};font-weight:700;width:1.2rem">{icon}</span>'
                f'{txt}</div>',
                unsafe_allow_html=True,
            )

    if R_syn is None and R_hosp is None:
        st.markdown(
            '<div class="a-info" style="margin-top:1rem">'
            'No pipeline results yet. Follow the steps above.</div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Metrics comparison ─────────────────────────────────────────────────
        st.markdown('<div class="sec">Diagnostic Performance</div>', unsafe_allow_html=True)
        col_h, col_q = st.columns(2)

        with col_h:
            st.markdown(
                '<div class="surface"><div style="font-size:.78rem;font-weight:700;'
                'color:#475569;text-transform:uppercase;letter-spacing:.07em;'
                'margin-bottom:.8rem">Traditional Hospital Monitoring (MediCore HMS)</div>',
                unsafe_allow_html=True,
            )
            if R_hosp:
                dept_rows = R_hosp.get("_dept_rows", [])
                total_risk = sum(int(r.get("risk_events") or 0) for r in dept_rows)
                total_all  = sum(int(r.get("total_readings") or 1) for r in dept_rows)
                alert_rate = total_risk / max(total_all, 1) * 100
                n_depts    = len(dept_rows)
                n_flagged  = sum(1 for r in dept_rows
                                  if (int(r.get("risk_events") or 0) /
                                      max(int(r.get("total_readings") or 1), 1)) > 0.10)
                import pandas as pd
                df_dept = pd.DataFrame([{
                    "Department": r["department"],
                    "Devices":    r.get("n_devices", "?"),
                    "Risk Events": r.get("risk_events", 0),
                    "Total Readings": r.get("total_readings", 0),
                    "Alert Rate %": f"{int(r.get('risk_events',0))/max(int(r.get('total_readings',1)),1)*100:.1f}",
                    "HMS Flag": "Flagged" if (int(r.get('risk_events',0))/
                                               max(int(r.get('total_readings',1)),1)) > 0.10 else "Normal",
                } for r in dept_rows])
                st.dataframe(df_dept, hide_index=True, use_container_width=True)
                kpi(st, "System-wide Alert Rate", f"{alert_rate:.1f}%",
                    f"{total_risk} alerts in {total_all} readings", C_RED)
                kpi(st, "Departments Flagged", f"{n_flagged} / {n_depts}",
                    "Threshold: >10% alert rate", C_AMBER)
            else:
                st.markdown(
                    '<div class="a-info">Connect to hospital and run pipeline to see HMS data.</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_q:
            st.markdown(
                '<div class="surface"><div style="font-size:.78rem;font-weight:700;'
                'color:#475569;text-transform:uppercase;letter-spacing:.07em;'
                'margin-bottom:.8rem">Quantum IoMT Diagnostic System</div>',
                unsafe_allow_html=True,
            )
            R_show = R_hosp or R_syn
            if R_show:
                probs  = R_show["probs"]
                preds  = R_show["preds"]
                y_true = R_show["y"]
                source = R_show.get("_source", "synthetic")

                c1, c2 = st.columns(2)
                kpi(c1, "VQC Accuracy",  f"{R_show['accuracy']*100:.1f}%",
                    "Quantum prediction", C_PRIMARY)
                kpi(c2, "F1 Score",      f"{R_show['f1']*100:.1f}%",
                    "Balanced metric", C_PURPLE)
                c3, c4 = st.columns(2)
                kpi(c3, "Precision",     f"{R_show['precision']*100:.1f}%",
                    "Low false positives", C_GREEN)
                kpi(c4, "Recall",        f"{R_show['recall']*100:.1f}%",
                    "Catches true positives", C_TEAL)

                source_badge = "Hospital data" if source == "hospital" else "Synthetic data"
                st.markdown(
                    f'<div style="font-size:.72rem;color:{C_TEAL};margin-top:.5rem">'
                    f'Source: {source_badge}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="a-info">Run the pipeline to see quantum metrics.</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Side-by-side probability plots ────────────────────────────────────
        if R_syn and R_hosp:
            st.markdown('<div class="sec">Risk Score Comparison  —  Synthetic vs Hospital Data</div>', unsafe_allow_html=True)
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=["Synthetic Patients", "Hospital Departments (MediCore)"],
            )
            for col_idx, (Rx, name) in enumerate([(R_syn, "Synthetic"), (R_hosp, "Hospital")], 1):
                y  = Rx["y"]
                pr = Rx["probs"]
                for lbl, mask, clr in [("Normal", y==0, C_GREEN), ("Abnormal", y==1, C_RED)]:
                    fig.add_trace(
                        go.Histogram(x=pr[mask], name=f"{lbl} ({name})",
                                     nbinsx=15, marker_color=clr, opacity=0.7,
                                     showlegend=(col_idx == 1)),
                        row=1, col=col_idx,
                    )
                fig.add_vline(x=0.5, line_dash="dash", line_color=C_AMBER, row=1, col=col_idx)
            fig.update_layout(barmode="overlay", height=320,
                              **_pl(title="VQC Output Probability  —  Both Sources"))
            st.plotly_chart(fig, use_container_width=True)

            # Delta table — key metric differences
            st.markdown('<div class="sec">Key Metric Delta</div>', unsafe_allow_html=True)
            import pandas as pd
            metrics = ["accuracy", "precision", "recall", "f1"]
            df_delta = pd.DataFrame({
                "Metric":    [m.capitalize() for m in metrics],
                "Synthetic": [f"{R_syn[m]*100:.1f}%"  for m in metrics],
                "Hospital":  [f"{R_hosp[m]*100:.1f}%" for m in metrics],
                "Delta":     [f"{(R_hosp[m] - R_syn[m])*100:+.1f}%" for m in metrics],
            })
            st.dataframe(df_delta, hide_index=True, use_container_width=True)

        elif R_syn or R_hosp:
            R_available = R_syn or R_hosp
            src = R_available.get("_source", "unknown")
            st.markdown(
                f'<div class="a-warning">Only <strong>{src}</strong> pipeline results are available. '
                f'Run the pipeline with the other data source to unlock the side-by-side comparison.</div>',
                unsafe_allow_html=True,
            )
