"""
Quantum IoMT IDS Live Monitor — port 8505
6-page live dashboard for the Quantum-Enhanced Intrusion Detection System.
  Live Monitor · Architecture · Evaluation · Quantum Circuits · Attack Impact · Research Notes
"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path

st.set_page_config(
    page_title="Quantum IDS Live Monitor",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

from stream_engine import (
    PatientStreamBuffer, run_evaluation, simulate_attack_degradation,
    ATTACK_PROFILES, confidence_to_risk, load_active_attacks,
    RISK_LABELS, RISK_COLORS, ATK_COLORS,
)

# ── Palette ────────────────────────────────────────────────────────────────────
C = dict(
    primary="#2563eb", teal="#0891b2", green="#16a34a",
    amber="#d97706",   red="#dc2626",  purple="#7c3aed",
    slate="#64748b",   navy="#0f172a", bg="#f1f5f9",
    surface="#ffffff", border="#e2e8f0", muted="#94a3b8", text="#0f172a",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp            { background:#f1f5f9; color:#0f172a; }
.block-container  { padding:4rem 2.5rem 2rem !important; max-width:1320px; }
[data-testid="stSidebar"] { background:#0f172a !important; border-right:1px solid #1e293b; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color:#94a3b8 !important; }
[data-testid="stSidebar"] hr  { border-color:#1e293b !important; }
header { display:none !important; } #MainMenu { display:none !important; } footer { display:none !important; }
.kpi-card  { background:#fff; border:1px solid #e2e8f0; border-top:3px solid;
             border-radius:8px; padding:1rem 1.25rem; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.kpi-label { font-size:.67rem; color:#64748b; text-transform:uppercase;
             letter-spacing:.08em; font-weight:600; }
.kpi-value { font-size:1.6rem; font-weight:700; color:#0f172a;
             margin:.2rem 0 .1rem; line-height:1; }
.kpi-sub   { font-size:.71rem; color:#94a3b8; }
.surface   { background:#fff; border:1px solid #e2e8f0; border-radius:8px;
             padding:1.25rem 1.5rem; box-shadow:0 1px 3px rgba(0,0,0,.05); margin-bottom:1rem; }
.sec       { font-size:.73rem; font-weight:700; color:#475569; text-transform:uppercase;
             letter-spacing:.08em; border-bottom:1px solid #e2e8f0;
             padding-bottom:.35rem; margin:1.4rem 0 .9rem; }
.pg-title  { font-size:1.3rem; font-weight:700; color:#0f172a; margin:0 0 .25rem; }
.pg-desc   { font-size:.82rem; color:#64748b; margin:0 0 1.2rem; }
.stage-tag { display:inline-block; background:#eff6ff; border:1px solid #bfdbfe;
             color:#1d4ed8; border-radius:4px; padding:.15rem .55rem; font-size:.67rem;
             font-weight:700; text-transform:uppercase; letter-spacing:.07em; margin-bottom:.6rem; }
.alert-attack { background:#fef2f2; border:1px solid #fecaca; border-left:4px solid #dc2626;
                border-radius:6px; padding:.55rem 1rem; color:#991b1b; margin:3px 0; font-size:.82rem; }
.alert-normal { background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #16a34a;
                border-radius:6px; padding:.55rem 1rem; color:#14532d; margin:3px 0; font-size:.82rem; }
.alert-info   { background:#eff6ff; border:1px solid #bfdbfe; border-left:4px solid #2563eb;
                border-radius:6px; padding:.55rem 1rem; color:#1e40af; margin:3px 0; font-size:.82rem; }
.attack-banner { background:#450a0a; border:2px solid #dc2626; border-radius:8px;
                 padding:.75rem 1.2rem; color:#fca5a5; font-weight:700;
                 font-size:.88rem; margin-bottom:.8rem; }
.pkt-row   { background:#fff; border:1px solid #e2e8f0; border-radius:6px;
             padding:.4rem .9rem; margin:2px 0; display:flex;
             justify-content:space-between; align-items:center; font-size:.79rem; }
.nav-wrap  { background:#fff; border:1px solid #e2e8f0; border-radius:10px;
             padding:.6rem .8rem .5rem; margin-bottom:.8rem;
             box-shadow:0 1px 4px rgba(0,0,0,.06); }
.nav-wrap .stButton > button {
    background:#f8fafc !important; border:1px solid #e2e8f0 !important;
    border-radius:6px !important; color:#475569 !important;
    font-size:.77rem !important; font-weight:500 !important;
    padding:.3rem .5rem !important; width:100% !important; }
.nav-wrap .stButton > button:hover {
    background:#eff6ff !important; border-color:#93c5fd !important;
    color:#1d4ed8 !important; }
.nav-wrap .nav-active .stButton > button {
    background:#2563eb !important; border-color:#2563eb !important;
    color:#fff !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _pl(**kw):
    base = dict(template="plotly_white", paper_bgcolor="#ffffff",
                plot_bgcolor="#f8fafc", font=dict(color="#334155", size=11),
                margin=dict(l=48, r=20, t=44, b=40))
    base.update(kw)
    return base

def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def kpi(col, label, value, sub, color):
    col.markdown(
        f'<div class="kpi-card" style="border-top-color:{color}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ── Session state ──────────────────────────────────────────────────────────────
if "page_idx"    not in st.session_state: st.session_state["page_idx"]    = 0
if "stream_buf"  not in st.session_state: st.session_state["stream_buf"]  = None
if "eval_result" not in st.session_state: st.session_state["eval_result"] = None
if "atk_result"  not in st.session_state: st.session_state["atk_result"]  = None
if "auto_on"     not in st.session_state: st.session_state["auto_on"]     = False


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div style="font-size:1.05rem;font-weight:700;color:#f1f5f9;padding:.4rem 0 .05rem">'
    '⚛ Quantum IDS</div>'
    '<div style="font-size:.7rem;color:#475569;margin-bottom:.6rem">'
    'Live Attack Detection</div>', unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.72rem;font-weight:600;color:#64748b;'
    'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">'
    'Stream Settings</div>', unsafe_allow_html=True,
)
stream_seed     = st.sidebar.number_input("Seed", 0, 9999, 42)
batch_n         = st.sidebar.slider("Batch size", 2, 16, 4)
eval_n          = st.sidebar.slider("Eval packets", 30, 200, 80, 10)
st.sidebar.markdown("---")

active_attacks = load_active_attacks()
if active_attacks:
    atk_list = ", ".join(active_attacks.keys()).upper()
    st.sidebar.markdown(
        f'<div style="background:#450a0a;border:1px solid #dc2626;border-radius:6px;'
        f'padding:.5rem .75rem;color:#fca5a5;font-size:.75rem;font-weight:700;">'
        f'⚠ ACTIVE: {atk_list}</div>', unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        '<div style="background:#052e16;border:1px solid #166534;border-radius:6px;'
        'padding:.5rem .75rem;color:#86efac;font-size:.75rem;">'
        '✓ No active attacks</div>', unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.72rem;color:#475569;margin-bottom:.4rem;">NETWORK STATUS</div>',
    unsafe_allow_html=True,
)
buf = st.session_state.get("stream_buf")
if buf:
    tot = buf.totals
    acc = buf.accuracy()
    st.sidebar.markdown(
        f'<div style="font-size:.78rem;color:#94a3b8;line-height:1.8;">'
        f'Packets: <b style="color:#f1f5f9">{tot["packets"]}</b><br>'
        f'Attacks detected: <b style="color:#fca5a5">{tot["attacks"]}</b><br>'
        f'Accuracy: <b style="color:#86efac">{acc*100:.1f}%</b></div>',
        unsafe_allow_html=True,
    )


# ── Top navigation ─────────────────────────────────────────────────────────────
PAGE_NAMES = ["Live Monitor", "Architecture", "Evaluation",
              "Quantum Circuits", "Attack Impact", "Research Notes"]
with st.container():
    st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
    nav_cols = st.columns(6)
    for ci, name in enumerate(PAGE_NAMES):
        wrap = "nav-active" if st.session_state["page_idx"] == ci else ""
        with nav_cols[ci]:
            st.markdown(f'<div class="{wrap}">', unsafe_allow_html=True)
            if st.button(name, key=f"nav_{ci}"):
                st.session_state["page_idx"] = ci
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state["page_idx"]


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 0 — Live Monitor
# ══════════════════════════════════════════════════════════════════════════════
if page == 0:
    st.markdown('<div class="pg-title">⚛ Quantum IDS — Live Network Attack Detection</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">Real-time IoMT packet stream classified by the VQC quantum circuit. Each batch runs ANUKF → Q-Flex ViT → BMOCO → HQAN → VQC.</div>',
                unsafe_allow_html=True)

    active = load_active_attacks()
    if active:
        atks = ", ".join(a.upper() for a in active.keys())
        st.markdown(f'<div class="attack-banner">⚠ ACTIVE ATTACKS: {atks} — VQC detection under adversarial noise</div>',
                    unsafe_allow_html=True)

    # Controls
    c1, c2 = st.columns([3, 1])
    with c1:
        auto = st.checkbox("Auto Refresh (3s)", value=st.session_state["auto_on"])
        st.session_state["auto_on"] = auto
    with c2:
        new_batch = st.button("⚡ New Batch")

    if st.session_state["stream_buf"] is None:
        st.session_state["stream_buf"] = PatientStreamBuffer(seed=stream_seed)

    buf = st.session_state["stream_buf"]

    if new_batch or auto:
        batch = buf.tick(n=batch_n)
    else:
        batch = []

    tot = buf.totals
    acc = buf.accuracy()

    # KPIs
    c1,c2,c3,c4,c5 = st.columns(5)
    kpi(c1, "Packets",  str(tot["packets"]),           "processed",       C["primary"])
    kpi(c2, "Attacks",  str(tot["attacks"]),           "detected",        C["red"])
    kpi(c3, "Accuracy", f"{acc*100:.1f}%",             "VQC detection",   C["green"])
    kpi(c4, "Critical", str(tot["critical"]),          "HIGH/CRITICAL",   C["amber"])
    kpi(c5, "Adv Input",str(tot["under_attack"]),      "under attack",    C["purple"])
    st.markdown("")

    c1, c2 = st.columns([2, 1])
    with c1:
        # Recent packet feed
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">RECENT PACKET DETECTIONS</div>', unsafe_allow_html=True)
        recent = buf.recent(12)
        if recent:
            for r in reversed(recent):
                label_txt = "ATTACK" if r["prediction"] == 1 else "NORMAL"
                cls = "alert-attack" if r["prediction"] == 1 else "alert-normal"
                bar_w = int(r["confidence"] * 100)
                bar_c = C["red"] if r["prediction"] == 1 else C["green"]
                st.markdown(f"""
                <div class="{cls}">
                  <b>PKT-{r['packet_id']}</b>
                  [{r['attack_type'].upper()}]
                  → <b>{label_txt}</b>
                  <span style="float:right;font-size:.78rem;">conf: {r['confidence']:.3f}
                    | risk: <b>{r['risk_level']}</b></span>
                  <div style="height:3px;background:#e2e8f0;border-radius:2px;margin-top:.3rem;">
                    <div style="width:{bar_w}%;height:3px;background:{bar_c};border-radius:2px;"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info">Click ⚡ New Batch or enable Auto Refresh to start the quantum IDS stream.</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        # Threat gauge
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">THREAT LEVEL</div>', unsafe_allow_html=True)
        recent_all = buf.all()
        if recent_all:
            atk_rate = sum(1 for r in recent_all[-20:] if r["prediction"]==1) / min(20,len(recent_all))
        else:
            atk_rate = 0.0
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=atk_rate*100,
            number=dict(suffix="%", font=dict(size=24, color="#0f172a")),
            gauge=dict(
                axis=dict(range=[0,100]),
                bar=dict(color=C["red"] if atk_rate>0.5 else C["amber"] if atk_rate>0.25 else C["green"]),
                steps=[
                    dict(range=[0,25],   color="#f0fdf4"),
                    dict(range=[25,50],  color="#fffbeb"),
                    dict(range=[50,100], color="#fef2f2"),
                ],
                threshold=dict(line=dict(color=C["red"],width=3), thickness=0.8, value=50),
            ),
        ))
        gauge.update_layout(**_pl(margin=dict(l=20,r=20,t=20,b=10)), height=200)
        st.plotly_chart(gauge, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Risk distribution
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">RISK DISTRIBUTION</div>', unsafe_allow_html=True)
        rc = buf.risk_counts()
        fig_risk = go.Figure(go.Bar(
            x=list(rc.keys()), y=list(rc.values()),
            marker_color=RISK_COLORS,
            text=list(rc.values()), textposition="outside",
        ))
        fig_risk.update_layout(**_pl(margin=dict(l=10,r=10,t=10,b=20)), height=200,
                               showlegend=False)
        st.plotly_chart(fig_risk, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Confidence trace
    if buf.confidence_trace():
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">VQC CONFIDENCE TRACE</div>', unsafe_allow_html=True)
        trace = buf.confidence_trace()
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(y=trace, mode="lines", line=dict(color=C["primary"],width=1.5)))
        fig_t.add_hline(y=0.5, line_dash="dash", line_color=C["amber"], annotation_text="threshold")
        fig_t.update_layout(**_pl(margin=dict(l=40,r=20,t=10,b=20)), height=160,
                            yaxis=dict(range=[0,1]))
        st.plotly_chart(fig_t, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if auto:
        time.sleep(3)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Architecture
# ══════════════════════════════════════════════════════════════════════════════
elif page == 1:
    st.markdown('<div class="pg-title">Quantum IDS Pipeline Architecture</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">9-stage quantum-enhanced intrusion detection pipeline for IoMT networks.</div>',
                unsafe_allow_html=True)

    stages = [
        ("1", "ANUKF",          "Adaptive Neural Unscented Kalman Filter — denoises IoMT packet streams",     C["teal"]),
        ("2", "Q-Flex ViT",     "Quantum Flexibility Vision Transformer — quantum attention feature extraction", C["purple"]),
        ("3", "BMOCO",          "Binary Multi-Objective Cheetah Optimization — optimal feature subset",        C["amber"]),
        ("4", "HQAN",           "Hybrid Quantum Attention Network — quantum-weighted feature analysis",         C["primary"]),
        ("5", "DQA",            "Dynamic Quantum Attention — adaptive attention weighting",                     C["teal"]),
        ("6", "DRA",            "Dynamic Resource Adaptation — runtime resource management",                    C["green"]),
        ("7", "RBWKA",          "Revamped Black-Winged Kite Algorithm — optimises VQC circuit weights",        C["green"]),
        ("8", "VQC",            "Variational Quantum Circuits (4-qubit) — attack/normal classification",       C["red"]),
        ("9", "Adap. SHARP",    "Adaptive SHAP — forensic feature importance for audit trail",                 C["slate"]),
    ]

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">PIPELINE STAGES</div>', unsafe_allow_html=True)
        for num, name, desc, color in stages:
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:.8rem;margin:.5rem 0;">
              <div style="min-width:2rem;height:2rem;background:{color};border-radius:50%;
                display:flex;align-items:center;justify-content:center;color:#fff;
                font-size:.72rem;font-weight:700;">{num}</div>
              <div>
                <span style="font-weight:700;font-size:.85rem;color:#0f172a;">{name}</span>
                <span style="font-size:.78rem;color:#64748b;margin-left:.4rem;">{desc}</span>
              </div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">ALGORITHM REFERENCE</div>', unsafe_allow_html=True)
        algos = [
            ("ANUKF",        "Adaptive Neural Unscented Kalman Filter"),
            ("Q-Flex ViT",   "Quantum Flexibility Vision Transformer"),
            ("BMOCO",        "Binary Multi-Objective Cheetah Optimization"),
            ("HQAN",         "Hybrid Quantum Attention Network"),
            ("DQA",          "Dynamic Quantum Attention"),
            ("DRA",          "Dynamic Resource Adaptation"),
            ("RBWKA",        "Revamped Black-Winged Kite Algorithm"),
            ("VQC",          "Variational Quantum Circuits"),
            ("Adap. SHARP",  "Adaptive SHAP Explainability"),
        ]
        for abbr, full in algos:
            st.markdown(f"""
            <div style="display:flex;gap:.6rem;margin:.35rem 0;font-size:.8rem;">
              <span style="font-weight:700;color:{C['primary']};min-width:5.5rem;">{abbr}</span>
              <span style="color:#64748b;">{full}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">VQC CIRCUIT FORMULA</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-family:monospace;font-size:.8rem;color:#0f172a;
          background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:.8rem;line-height:1.9;">
          Input: feat[0:4] / ‖feat[0:4]‖ × π<br>
          AngleEmbedding(feat → q[0-3], rotation='Y')<br>
          StronglyEntanglingLayers(weights, wires=[0,1,2,3]) × 3<br>
          Output: (⟨Z₀⊗Z₁⟩ + 1) / 2  →  [0,1] attack probability
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Research gaps
    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.markdown('<div class="sec">RESEARCH GAPS ADDRESSED</div>', unsafe_allow_html=True)
    gaps = [
        ("Noisy IoMT network signals",   "ANUKF adaptive non-linear filtering"),
        ("Feature redundancy in packets","BMOCO multi-objective selection"),
        ("High computational cost",      "DRA dynamic resource allocation + quantum speedup"),
        ("Poor IDS accuracy",            "VQC + HQAN quantum-enhanced classification"),
        ("Lack of forensic explainability","Adaptive SHARP for audit trail"),
        ("Isolated IDS research silos",  "Single integrated quantum pipeline (signal→predict→explain)"),
    ]
    cols = st.columns(2)
    for i, (gap, sol) in enumerate(gaps):
        cols[i%2].markdown(f"""
        <div style="display:flex;gap:.6rem;margin:.3rem 0;font-size:.8rem;">
          <span style="color:{C['red']};font-weight:700;">✗</span>
          <span style="color:#64748b;">{gap}</span>
          <span style="color:#64748b;">→</span>
          <span style="color:{C['green']};font-weight:600;">{sol}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Evaluation
# ══════════════════════════════════════════════════════════════════════════════
elif page == 2:
    st.markdown('<div class="pg-title">Quantum IDS Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">One-shot evaluation of the VQC quantum classifier on synthesised IoMT network traffic.</div>',
                unsafe_allow_html=True)

    if st.button("▶ Run Evaluation"):
        with st.spinner("Running quantum IDS evaluation…"):
            st.session_state["eval_result"] = run_evaluation(n_patients=eval_n, seed=42)

    R = st.session_state["eval_result"]
    if not R:
        st.info("Click Run Evaluation to evaluate the quantum IDS on a batch of network packets.")
    else:
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        kpi(c1, "Accuracy",  f"{R['acc']*100:.1f}%",  "overall",     C["primary"])
        kpi(c2, "Precision", f"{R['prec']*100:.1f}%", "attack prec", C["green"])
        kpi(c3, "Recall",    f"{R['rec']*100:.1f}%",  "attack rec",  C["teal"])
        kpi(c4, "F1",        f"{R['f1']*100:.1f}%",   "f1 score",    C["purple"])
        kpi(c5, "FPR",       f"{R['fpr']*100:.1f}%",  "false pos",   C["red"])
        kpi(c6, "AUC",       f"{R['auc']:.3f}",       "roc-auc",     C["amber"])
        st.markdown("")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">CONFUSION MATRIX</div>', unsafe_allow_html=True)
            cm = [[R['tn'], R['fp']], [R['fn'], R['tp']]]
            fig = go.Figure(go.Heatmap(
                z=cm, x=["Pred Normal","Pred Attack"], y=["True Normal","True Attack"],
                colorscale=[[0,"#f0fdf4"],[0.5,"#bbf7d0"],[1,"#16a34a"]],
                text=cm, texttemplate="%{text}", textfont_size=18,
            ))
            fig.update_layout(**_pl(margin=dict(l=20,r=20,t=10,b=20)), height=260)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">ROC CURVE</div>', unsafe_allow_html=True)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=R['roc_fpr'], y=R['roc_tpr'], mode="lines",
                                      line=dict(color=C["primary"],width=2), name=f"AUC={R['auc']:.3f}"))
            fig2.add_trace(go.Scatter(x=[0,1], y=[0,1], mode="lines",
                                      line=dict(color="#94a3b8",dash="dash"), name="Random"))
            fig2.update_layout(**_pl(margin=dict(l=20,r=20,t=10,b=20)), height=260,
                               xaxis_title="FPR", yaxis_title="TPR")
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">CONFIDENCE DISTRIBUTION</div>', unsafe_allow_html=True)
        confs = R['confs']; y_arr = R['y']
        confs_np = np.array(confs); y_np = np.array(y_arr)
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(x=confs_np[y_np==0], name="Normal",
                                    marker_color=C["green"], opacity=0.7, nbinsx=20))
        fig3.add_trace(go.Histogram(x=confs_np[y_np==1], name="Attack",
                                    marker_color=C["red"], opacity=0.7, nbinsx=20))
        fig3.add_vline(x=0.5, line_dash="dash", line_color=C["amber"], annotation_text="decision threshold")
        fig3.update_layout(**_pl(margin=dict(l=20,r=20,t=10,b=20)), barmode="overlay", height=220)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Quantum Circuits
# ══════════════════════════════════════════════════════════════════════════════
elif page == 3:
    st.markdown('<div class="pg-title">Quantum Circuits</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">VQC (4-qubit Variational Quantum Circuit) and Q-Flex quantum attention implementation details.</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">VQC — 4-QUBIT CIRCUIT</div>', unsafe_allow_html=True)
        layers = [
            ("AngleEmbedding", "Encode feat[0:4] as Y-rotation angles on q[0-3]", C["primary"]),
            ("StronglyEntanglingLayers ×3", "Trainable rotations + CNOT entanglement", C["purple"]),
            ("Measure ⟨Z₀⊗Z₁⟩", "Joint observable → raw score ∈ [-1,+1]", C["red"]),
            ("Scale to [0,1]", "(raw + 1) / 2  →  attack probability", C["green"]),
        ]
        for gate, desc, color in layers:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:.6rem;margin:.4rem 0;">
              <code style="background:{color}22;color:{color};border:1px solid {color}44;
                border-radius:4px;padding:.1rem .4rem;font-size:.75rem;min-width:14rem;">{gate}</code>
              <span style="font-size:.78rem;color:#64748b;">{desc}</span>
            </div>""", unsafe_allow_html=True)

        # VQC qubit diagram
        fig_vqc = go.Figure()
        for q in range(4):
            fig_vqc.add_trace(go.Scatter(x=[0,4], y=[q,q], mode="lines",
                                         line=dict(color="#cbd5e1",width=1.5), showlegend=False))
            fig_vqc.add_annotation(x=-0.1, y=q, text=f"q{q}", showarrow=False,
                                   font=dict(size=11, color="#64748b"), xanchor="right")
        gate_defs = [
            (0.5, [0,1,2,3], "AngleEmbed", C["primary"]),
            (1.5, [0,1,2,3], "SEL Layer 1", C["purple"]),
            (2.5, [0,1,2,3], "SEL Layer 2", C["purple"]),
            (3.5, [0,1,2,3], "SEL Layer 3", C["purple"]),
        ]
        for gx, qubits, gname, gcolor in gate_defs:
            for q in qubits:
                fig_vqc.add_shape(type="rect", x0=gx-0.3, x1=gx+0.3,
                                  y0=q-0.3, y1=q+0.3,
                                  fillcolor=_rgba(gcolor, 0.27), line=dict(color=gcolor, width=1.5))
            fig_vqc.add_annotation(x=gx, y=-0.7, text=gname, showarrow=False,
                                   font=dict(size=9, color=gcolor))
        fig_vqc.add_shape(type="rect", x0=4.1, x1=4.5, y0=-0.3, y1=1.3,
                          fillcolor=_rgba(C["red"], 0.2), line=dict(color=C["red"]))
        fig_vqc.add_annotation(x=4.3, y=0.5, text="Meas\nZ₀Z₁", showarrow=False,
                               font=dict(size=8, color=C["red"]))
        fig_vqc.update_layout(**_pl(margin=dict(l=40,r=20,t=10,b=30)), height=220, showlegend=False,
                              xaxis=dict(range=[-0.3,5], showgrid=False, zeroline=False, showticklabels=False),
                              yaxis=dict(range=[-1,3.5], showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_vqc, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">Q-FLEX ATTENTION CIRCUIT</div>', unsafe_allow_html=True)
        gates_q = [
            ("AngleEmbed q[0,1]",  "Encode query features → wires 0,1",  C["primary"]),
            ("AngleEmbed q[2,3]",  "Encode key features → wires 2,3",    C["teal"]),
            ("H(0) H(2)",          "Superposition (Hadamard)",            C["purple"]),
            ("CNOT(0→2)",          "Cross-entangle query/key",            C["amber"]),
            ("CNOT(1→3)",          "Cross-entangle query/key",            C["amber"]),
            ("CRZ(π/4, 0→1)",      "Controlled-RZ rotation",             C["green"]),
            ("CRZ(π/4, 2→3)",      "Controlled-RZ rotation",             C["green"]),
            ("H(0) H(2)",          "Interference layer",                  C["purple"]),
            ("⟨Z₀⟩⟨Z₁⟩⟨Z₂⟩⟨Z₃⟩", "4 attention weights → [0,1]",        C["red"]),
        ]
        for gate, desc, color in gates_q:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:.6rem;margin:.3rem 0;">
              <code style="background:{color}22;color:{color};border:1px solid {color}44;
                border-radius:4px;padding:.1rem .4rem;font-size:.73rem;min-width:11rem;">{gate}</code>
              <span style="font-size:.77rem;color:#64748b;">{desc}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # VQC weight heatmap
        buf = st.session_state.get("stream_buf")
        if buf is not None:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">VQC WEIGHT HEATMAP (3 LAYERS × 4 QUBITS)</div>', unsafe_allow_html=True)
            w = buf.weights
            fig_w = make_subplots(rows=1, cols=3,
                                  subplot_titles=["Layer 1","Layer 2","Layer 3"])
            for li in range(3):
                fig_w.add_trace(
                    go.Heatmap(z=w[li], colorscale="Viridis",
                               showscale=li==2, zmin=0, zmax=2*np.pi,
                               text=np.round(w[li],2), texttemplate="%{text}"),
                    row=1, col=li+1,
                )
            fig_w.update_layout(**_pl(margin=dict(l=20,r=20,t=30,b=10)), height=200)
            st.plotly_chart(fig_w, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Attack Impact
# ══════════════════════════════════════════════════════════════════════════════
elif page == 4:
    st.markdown('<div class="pg-title">Attack Impact on Quantum IDS</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">Simulates how each IoMT attack type degrades VQC detection accuracy across 10 intensity levels.</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("▶ Run Simulation"):
            with st.spinner("Simulating attack degradation…"):
                st.session_state["atk_result"] = simulate_attack_degradation(n_patients=50, seed=99)

    atk_r = st.session_state["atk_result"]
    if not atk_r:
        st.info("Click Run Simulation to see how each attack type degrades quantum detection accuracy.")
    else:
        # Degradation line chart
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">VQC ACCURACY vs ATTACK INTENSITY</div>', unsafe_allow_html=True)
        intensities = np.linspace(0.1, 1.0, 10)
        fig = go.Figure()
        baseline = list(atk_r.values())[0]["baseline_acc"]
        fig.add_trace(go.Scatter(x=intensities, y=[baseline]*10, mode="lines",
                                 line=dict(color="#94a3b8",dash="dash",width=1.5),
                                 name="Baseline"))
        for atk_key, res in atk_r.items():
            fig.add_trace(go.Scatter(
                x=intensities, y=res["acc_curve"], mode="lines+markers",
                line=dict(color=res["color"],width=2),
                marker=dict(size=5), name=res["label"],
            ))
        fig.update_layout(**_pl(margin=dict(l=40,r=20,t=20,b=40)), height=320,
                          xaxis_title="Attack Intensity", yaxis_title="VQC Accuracy")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Summary table
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">ATTACK IMPACT SUMMARY</div>', unsafe_allow_html=True)
        import pandas as pd
        rows = []
        for atk_key, res in atk_r.items():
            rows.append({
                "Attack": res["label"],
                "Baseline Acc": f"{res['baseline_acc']*100:.1f}%",
                "Final Acc (full intensity)": f"{res['final_acc']*100:.1f}%",
                "Degradation": f"−{res['degradation']*100:.1f}%",
                "Severity": "CRITICAL" if res['degradation']>0.3 else "HIGH" if res['degradation']>0.15 else "MODERATE",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=220)
        st.markdown('</div>', unsafe_allow_html=True)

        # Active attacks from Attack Lab
        active = load_active_attacks()
        if active:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">CURRENT ACTIVE ATTACKS (FROM ATTACK LAB)</div>', unsafe_allow_html=True)
            for atk_key, intensity in active.items():
                color = ATK_COLORS.get(atk_key, "#64748b")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:1rem;
                  margin:.4rem 0;padding:.5rem .8rem;
                  background:{color}11;border:1px solid {color}44;border-radius:6px;">
                  <span style="font-weight:700;color:{color};min-width:7rem;">{atk_key.upper()}</span>
                  <div style="flex:1;background:#e2e8f0;border-radius:4px;height:8px;">
                    <div style="width:{int(float(intensity)*100)}%;height:8px;
                      background:{color};border-radius:4px;"></div>
                  </div>
                  <span style="font-size:.8rem;color:#64748b;">intensity: {float(intensity):.2f}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Research Notes
# ══════════════════════════════════════════════════════════════════════════════
elif page == 5:
    st.markdown('<div class="pg-title">Research Notes & Presenter Guide</div>', unsafe_allow_html=True)
    st.markdown('<div class="pg-desc">Novel contributions, vs literature comparison, and viva/presentation guide for Binu\'s Quantum IDS research.</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Novel Contributions", "vs Literature", "Key Findings", "Presenter Guide"])

    with tab1:
        contribs = [
            ("ANUKF for IoMT IDS",
             "First application of Adaptive Neural UKF to denoise network packet streams in an IoMT IDS context. Prior work applies UKF only to control systems and navigation."),
            ("Q-Flex ViT for Network Traffic",
             "Quantum Vision Transformer adapted for tabular network traffic features. Query/key cross-entanglement via CNOT+CRZ gates captures non-linear feature correlations that classical dot-product attention misses."),
            ("BMOCO Feature Selection",
             "Binary Multi-Objective Cheetah Optimization selects the minimal discriminative feature subset. Three-phase hunting (Scout→Chase→Attack) balances accuracy vs feature count in a Pareto-optimal way."),
            ("HQAN Quantum Attention",
             "Hybrid Quantum Attention Network applies interference-based weighting to selected features without backpropagation. Quantum superposition enables parallel evaluation of all feature combinations."),
            ("VQC Attack Classifier",
             "4-qubit Variational Quantum Circuit with StronglyEntanglingLayers trained by RBWKA. Measures joint observable ⟨Z₀⊗Z₁⟩ — the entangled state captures correlations between pairs of features simultaneously."),
        ]
        for name, desc in contribs:
            with st.expander(f"⚛ {name}"):
                st.markdown(f'<div style="font-size:.83rem;color:#334155;line-height:1.7;">{desc}</div>',
                            unsafe_allow_html=True)

    with tab2:
        import pandas as pd
        lit_compare = pd.DataFrame([
            {"Existing Work": "Classical ML IDS (RF/SVM/DT)", "Gap": "No quantum enhancement, no XAI"},
            {"Existing Work": "Deep Learning IDS (CNN/LSTM)", "Gap": "High compute, black-box, no quantum"},
            {"Existing Work": "Quantum ML (general)",          "Gap": "Not applied to IoMT network traffic"},
            {"Existing Work": "Feature selection (classical)", "Gap": "Single objective, no quantum attention"},
            {"Existing Work": "XAI in IDS",                   "Gap": "No quantum component, no adaptive threshold"},
            {"Existing Work": "This Framework (Quantum IDS)",  "Gap": "First: ANUKF + Q-Flex ViT + BMOCO + HQAN + VQC + Adap.SHARP"},
        ])
        st.dataframe(lit_compare, use_container_width=True, height=260)

    with tab3:
        findings = [
            ("Quantum entanglement improves feature discrimination",
             "CNOT gates between query and key qubits capture correlations between packet_rate, payload_entropy, and ttl_norm that classical attention misses. This is critical for detecting ransomware (high entropy + unusual port) vs normal."),
            ("BMOCO reduces inference cost",
             "Selecting 3-5 out of 10 features reduces VQC input dimensionality. Fewer angle embeddings = fewer gate operations = faster quantum circuit execution."),
            ("RBWKA outperforms random init",
             "Black-winged kite three-phase search (soar→hover→dive) finds better VQC weight initialisation than uniform random, improving baseline accuracy by 3-8%."),
            ("Attack degradation hierarchy",
             "Ransomware causes the most VQC accuracy degradation (high noise + flip), while Replay causes the least (low noise, similar packet structure to normal). This matches the attack mechanics."),
            ("Adaptive SHARP threshold",
             "The adaptive threshold adjusts to the run — if features are equally important, threshold rises; if one dominates (e.g. payload_entropy in ransomware), the threshold falls and that feature is highlighted in the forensic report."),
        ]
        for title, desc in findings:
            with st.expander(f"📊 {title}"):
                st.markdown(f'<div style="font-size:.83rem;color:#334155;line-height:1.7;">{desc}</div>',
                            unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">5-MINUTE DEMO SCRIPT</div>', unsafe_allow_html=True)
        steps = [
            ("0:00", "Open this page (8505) — explain: quantum IDS replaces classical ML for attack detection"),
            ("0:30", "Architecture page — walk through 9 stages, emphasise Q-Flex ViT and VQC"),
            ("1:30", "Go to Attack Lab (8503) — launch RANSOMWARE attack"),
            ("2:00", "Back to Live Monitor — enable Auto Refresh — watch accuracy drop under attack"),
            ("2:30", "Attack Impact page — Run Simulation — show degradation curves"),
            ("3:30", "Open 8504 → Evaluation page — run pipeline — show confusion matrix + SHARP"),
            ("4:30", "Comparison page (8504 page 9) — Quantum vs Classical MedGuard table"),
            ("5:00", "Q&A: emphasise BMOCO feature reduction + VQC quantum advantage"),
        ]
        for ts, step in steps:
            st.markdown(f"""
            <div style="display:flex;gap:.8rem;margin:.4rem 0;font-size:.8rem;">
              <span style="font-weight:700;color:{C['primary']};min-width:2.5rem;">{ts}</span>
              <span style="color:#334155;">{step}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">LIKELY VIVA QUESTIONS</div>', unsafe_allow_html=True)
        qas = [
            ("Why use VQC instead of classical neural network?",
             "VQC uses quantum entanglement to model feature correlations exponentially — a classical NN needs O(2ⁿ) parameters for what a 4-qubit circuit captures natively. Also RBWKA optimises the quantum parameters more efficiently than backprop on noisy hardware."),
            ("Why BMOCO and not PCA for feature selection?",
             "PCA is unsupervised and creates abstract components. BMOCO is supervised (uses label), binary (selects original features for interpretability), and multi-objective (balances accuracy with feature count) — giving forensically auditable feature selections."),
            ("How does ANUKF help versus standard normalisation?",
             "Normalisation only scales static values. ANUKF filters the temporal sequence of packet streams — removing IoMT sensor noise (jitter, dropout) before features are extracted. This is especially important for replay attacks whose temporal patterns are subtle."),
        ]
        for q, a in qas:
            with st.expander(f"Q: {q}"):
                st.markdown(f'<div style="font-size:.83rem;color:#334155;line-height:1.7;"><b>A:</b> {a}</div>',
                            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
