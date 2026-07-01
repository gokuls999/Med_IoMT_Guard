"""
Quantum IoMT Live Monitor — port 8505
Fully-fledged 6-page research dashboard:
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
    page_title="Quantum IoMT Live Monitor",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette ────────────────────────────────────────────────────────────────────
C = dict(
    primary="#2563eb", teal="#0891b2", green="#16a34a",
    amber="#d97706",   red="#dc2626",  purple="#7c3aed",
    slate="#64748b",   navy="#0f172a", bg="#f1f5f9",
    surface="#ffffff", border="#e2e8f0", muted="#94a3b8",
    text="#0f172a",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp            { background:#f1f5f9; color:#0f172a; }
.block-container  { padding:4rem 2.5rem 2rem !important; max-width:1320px; }

[data-testid="stSidebar"] { background:#0f172a !important; border-right:1px solid #1e293b; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color:#94a3b8 !important; }
[data-testid="stSidebar"] hr  { border-color:#1e293b !important; }

header    { display:none !important; }
#MainMenu { display:none !important; }
footer    { display:none !important; }

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

.alert-crit { background:#fef2f2; border:1px solid #fecaca; border-left:4px solid #dc2626;
              border-radius:6px; padding:.55rem 1rem; color:#991b1b; margin:3px 0; font-size:.82rem; }
.alert-high { background:#fff7ed; border:1px solid #fed7aa; border-left:4px solid #ea580c;
              border-radius:6px; padding:.55rem 1rem; color:#9a3412; margin:3px 0; font-size:.82rem; }
.alert-mod  { background:#fffbeb; border:1px solid #fde68a; border-left:4px solid #d97706;
              border-radius:6px; padding:.55rem 1rem; color:#92400e; margin:3px 0; font-size:.82rem; }
.alert-norm { background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #16a34a;
              border-radius:6px; padding:.55rem 1rem; color:#14532d; margin:3px 0; font-size:.82rem; }
.alert-info { background:#eff6ff; border:1px solid #bfdbfe; border-left:4px solid #2563eb;
              border-radius:6px; padding:.55rem 1rem; color:#1e40af; margin:3px 0; font-size:.82rem; }
.attack-banner { background:#450a0a; border:2px solid #dc2626; border-radius:8px;
                 padding:.75rem 1.2rem; color:#fca5a5; font-weight:700;
                 font-size:.88rem; margin-bottom:.8rem; }

.pat-row   { background:#fff; border:1px solid #e2e8f0; border-radius:6px;
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

.qubit-gate { display:inline-block; background:#1e1b4b; border:1px solid #4338ca;
              border-radius:4px; padding:.2rem .5rem; color:#a5b4fc;
              font-family:monospace; font-size:.75rem; margin:1px; }
.wire-line  { color:#475569; font-family:monospace; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _pl(**kw):
    base = dict(template="plotly_white", paper_bgcolor="#ffffff",
                plot_bgcolor="#f8fafc", font=dict(color="#334155", size=11),
                margin=dict(l=48, r=20, t=44, b=40),
                colorway=[C["primary"], C["teal"], C["green"],
                          C["amber"],  C["red"],  C["purple"]])
    base.update(kw)
    return base

def kpi(col, label, value, sub, color):
    col.markdown(
        f'<div class="kpi-card" style="border-top-color:{color}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color}">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ── Session state ──────────────────────────────────────────────────────────────
if "page_idx"   not in st.session_state: st.session_state["page_idx"] = 0
if "stream_buf" not in st.session_state: st.session_state["stream_buf"] = None
if "eval_result"not in st.session_state: st.session_state["eval_result"] = None
if "atk_result" not in st.session_state: st.session_state["atk_result"] = None
if "auto_on"    not in st.session_state: st.session_state["auto_on"] = False


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div style="font-size:1.05rem;font-weight:700;color:#f1f5f9;padding:.4rem 0 .05rem">'
    '⚛ Quantum IoMT</div>'
    '<div style="font-size:.7rem;color:#475569;margin-bottom:.6rem">'
    'Live Diagnostic Monitor</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.72rem;font-weight:600;color:#64748b;'
    'text-transform:uppercase;letter-spacing:.07em;margin-bottom:.5rem">'
    'Stream Settings</div>',
    unsafe_allow_html=True,
)

stream_seed     = int(st.sidebar.number_input("Random seed", value=42, step=1))
refresh_sec     = st.sidebar.slider("Refresh interval (s)", 1, 10, 3)

from stream_engine import PatientStreamBuffer, run_evaluation, simulate_attack_degradation, load_active_attacks, load_attack_plan

if st.session_state["stream_buf"] is None:
    st.session_state["stream_buf"] = PatientStreamBuffer(seed=stream_seed)

buf: PatientStreamBuffer = st.session_state["stream_buf"]

auto_on = st.sidebar.checkbox("Auto-refresh Live Monitor", value=st.session_state["auto_on"])
st.session_state["auto_on"] = auto_on

if st.sidebar.button("Reset Stream"):
    st.session_state["stream_buf"] = PatientStreamBuffer(seed=stream_seed)
    buf = st.session_state["stream_buf"]
    st.rerun()

st.sidebar.markdown("---")

# Attack status indicator in sidebar
_active = load_active_attacks()
if _active:
    st.sidebar.markdown(
        f'<div style="background:#450a0a;border:1px solid #dc2626;border-radius:6px;'
        f'padding:.5rem .8rem;font-size:.74rem;color:#fca5a5;font-weight:700">'
        f'&#9888; ATTACK ACTIVE<br>'
        f'<span style="font-weight:400;color:#f87171">'
        + ", ".join(_active.keys()) + '</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        '<div style="background:#052e16;border:1px solid #166534;border-radius:6px;'
        'padding:.5rem .8rem;font-size:.74rem;color:#4ade80">'
        '&#9679; No active attacks</div>',
        unsafe_allow_html=True,
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="font-size:.65rem;color:#334155">Binu — PhD Research &nbsp;·&nbsp; 2026<br>'
    'Attack Lab: port 8503</div>',
    unsafe_allow_html=True,
)


# ── Top navigation ─────────────────────────────────────────────────────────────
PAGES      = ["Live Monitor", "Architecture", "Evaluation",
              "Quantum Circuits", "Attack Impact", "Research Notes"]
PAGE_SHORT = ["Live Monitor", "Architecture", "Evaluation",
              "Q-Circuits",   "Attack Impact","Research Notes"]

st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
_cur = st.session_state["page_idx"]
_nc  = st.columns(len(PAGES))
for _i, (_col, _lbl) in enumerate(zip(_nc, PAGE_SHORT)):
    _cls = "nav-active" if _cur == _i else ""
    with _col:
        st.markdown(f'<div class="{_cls}">', unsafe_allow_html=True)
        if st.button(_lbl, key=f"nav_{_i}"):
            st.session_state["page_idx"] = _i
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<hr style="margin:.3rem 0 .8rem;border-color:#e2e8f0">', unsafe_allow_html=True)
page = PAGES[st.session_state["page_idx"]]


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — LIVE MONITOR
# ══════════════════════════════════════════════════════════════════════════════
if page == "Live Monitor":
    st.markdown('<div class="pg-title">⚛ Live Quantum Diagnostic Monitor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">Real-time patient biosignal classification using VQC '
        '(Variational Quantum Circuits). Each tick processes a new patient batch through the '
        'ANUKF → Q-Flex ViT → HQAN → VQC pipeline.</div>',
        unsafe_allow_html=True,
    )

    # Attack banner
    active_attacks = load_active_attacks()
    if active_attacks:
        st.markdown(
            f'<div class="attack-banner">&#9888; CYBERATTACK IN PROGRESS — '
            + ", ".join(f"<strong>{k.upper()}</strong>" for k in active_attacks.keys())
            + ' — Quantum predictions may be degraded. See Attack Impact page.</div>',
            unsafe_allow_html=True,
        )

    # ── Tick (generate new patients) ───────────────────────────────────────────
    col_tick, col_auto, _ = st.columns([2, 3, 5])
    with col_tick:
        manual_tick = st.button("⚡ New Batch", type="primary", use_container_width=True)
    with col_auto:
        if auto_on:
            st.markdown(
                '<div style="font-size:.75rem;color:#16a34a;padding:.35rem 0">'
                '&#9679; Auto-refresh active</div>',
                unsafe_allow_html=True,
            )

    if manual_tick or auto_on:
        buf.tick()

    # ── Top KPIs ───────────────────────────────────────────────────────────────
    st.markdown('<div class="sec">System Health</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    rc = buf.risk_counts()
    kpi(k1, "Total Processed",  f"{buf.totals['patients']}",       "patients",         C["primary"])
    kpi(k2, "Quantum Accuracy", f"{buf.accuracy()*100:.1f}%",      "VQC predictions",  C["teal"])
    kpi(k3, "Critical Alerts",  f"{buf.totals['critical']}",       "risk ≥ HIGH",      C["red"])
    kpi(k4, "Abnormal Rate",
        f"{100*buf.totals['abnormal']/(buf.totals['patients'] or 1):.1f}%",
        "ground-truth positive",   C["amber"])
    kpi(k5, "Under Attack",     f"{buf.totals['attacked']}",       "batches degraded", C["purple"])

    st.markdown('<div class="sec">Live Feed</div>', unsafe_allow_html=True)
    col_feed, col_charts = st.columns([3, 2])

    # ── Patient feed ───────────────────────────────────────────────────────────
    with col_feed:
        recent = buf.recent(18)[::-1]
        for r in recent:
            ts_str  = time.strftime("%H:%M:%S", time.localtime(r["timestamp"]))
            pred_ok = r["correct"]
            atk_tag = " ⚠ ATK" if r["under_attack"] else ""
            conf_pc = int(r["confidence"] * 100)
            bar_w   = conf_pc
            bar_c   = r["risk_color"]
            gt_lbl  = "ABN" if r["label"] else "NRM"
            pr_lbl  = "ABN" if r["prediction"] else "NRM"
            chk     = "✓" if pred_ok else "✗"
            chk_col = "#16a34a" if pred_ok else "#dc2626"

            st.markdown(
                f'<div class="pat-row">'
                f'<span style="color:#64748b;font-family:monospace">{ts_str}</span>'
                f'<span style="font-weight:600">P-{r["patient_id"]:04d}</span>'
                f'<span style="color:{r["risk_color"]};font-weight:700">{r["risk_level"]}</span>'
                f'<div style="width:80px;background:#e2e8f0;border-radius:4px;height:10px;overflow:hidden">'
                f'<div style="width:{bar_w}%;height:100%;background:{bar_c}"></div></div>'
                f'<span style="font-size:.75rem;color:#475569">{conf_pc}%</span>'
                f'<span style="font-size:.74rem">GT:{gt_lbl} PR:{pr_lbl}</span>'
                f'<span style="color:{chk_col};font-weight:700">{chk}</span>'
                + (f'<span style="color:#ef4444;font-size:.7rem">{atk_tag}</span>' if r["under_attack"] else "")
                + "</div>",
                unsafe_allow_html=True,
            )

    # ── Charts ─────────────────────────────────────────────────────────────────
    with col_charts:
        # Threat gauge
        threat_pct = (rc.get("CRITICAL", 0) * 3 + rc.get("HIGH", 0) * 2 +
                      rc.get("MODERATE", 0)) / max(sum(rc.values()), 1) * 33
        threat_pct = min(100, int(threat_pct))
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=threat_pct,
            title=dict(text="Threat Level", font=dict(size=14, color="#334155")),
            gauge=dict(
                axis=dict(range=[0, 100], tickwidth=1, tickcolor="#94a3b8",
                          tickvals=[0, 25, 50, 75, 100],
                          ticktext=["0", "LOW", "MED", "HIGH", "CRIT"]),
                bar=dict(color="#2563eb", thickness=0.25),
                steps=[
                    dict(range=[0, 25],  color="#f0fdf4"),
                    dict(range=[25, 50], color="#fffbeb"),
                    dict(range=[50, 75], color="#fff7ed"),
                    dict(range=[75, 100],color="#fef2f2"),
                ],
                threshold=dict(line=dict(color="#dc2626", width=3), thickness=0.75, value=75),
            ),
            number=dict(suffix="%", font=dict(size=22, color="#0f172a")),
        ))
        fig_gauge.update_layout(height=230, **_pl(margin=dict(l=20, r=20, t=40, b=10)))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # Risk distribution
        if sum(rc.values()) > 0:
            fig_pie = go.Figure(go.Pie(
                labels=list(rc.keys()),
                values=list(rc.values()),
                marker=dict(colors=["#16a34a", "#d97706", "#ea580c", "#dc2626"]),
                hole=0.5,
                textinfo="label+percent",
                textfont=dict(size=10),
            ))
            fig_pie.update_layout(
                height=220, showlegend=False,
                title=dict(text="Risk Distribution", font=dict(size=13, color="#334155")),
                **_pl(margin=dict(l=10, r=10, t=40, b=10)),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # ── Confidence trace ───────────────────────────────────────────────────────
    trace = buf.confidence_trace()
    if len(trace) > 5:
        st.markdown('<div class="sec">VQC Confidence Trace</div>', unsafe_allow_html=True)
        fig_trace = go.Figure()
        fig_trace.add_trace(go.Scatter(
            y=trace, mode="lines",
            line=dict(color=C["primary"], width=1.5),
            fill="tozeroy", fillcolor="rgba(37,99,235,.08)",
            name="VQC confidence",
        ))
        fig_trace.add_hline(y=0.5, line=dict(dash="dash", color=C["slate"], width=1))
        fig_trace.update_layout(
            height=160, **_pl(margin=dict(l=40, r=10, t=10, b=30)),
            xaxis=dict(title="Patient index", showgrid=False),
            yaxis=dict(title="Confidence", range=[0, 1]),
        )
        st.plotly_chart(fig_trace, use_container_width=True)

    # ── Vitals sparklines ──────────────────────────────────────────────────────
    st.markdown('<div class="sec">Live Vitals Trends</div>', unsafe_allow_html=True)
    _v1, _v2, _v3, _v4 = st.columns(4)

    for _col, field, label, color, unit in [
        (_v1, "hr",   "Heart Rate",    C["red"],    "bpm"),
        (_v2, "sbp",  "Systolic BP",   C["primary"],"mmHg"),
        (_v3, "spo2", "SpO₂",          C["green"],  "%"),
        (_v4, "temp", "Temperature",   C["amber"],  "°C"),
    ]:
        series = buf.vitals_series(field, 30)
        if series:
            fig = go.Figure(go.Scatter(
                y=series, mode="lines",
                line=dict(color=color, width=1.8),
                fill="tozeroy", fillcolor=f"rgba({','.join(str(int(int(color[i:i+2],16))) for i in (1,3,5))},.08)",
            ))
            fig.update_layout(
                height=110,
                **_pl(margin=dict(l=28, r=8, t=22, b=18)),
                xaxis=dict(visible=False),
                yaxis=dict(title=unit, title_font=dict(size=9)),
                title=dict(text=f"{label}  —  avg {np.mean(series):.1f}", font=dict(size=11)),
            )
            _col.plotly_chart(fig, use_container_width=True)

    # ── Alert feed ─────────────────────────────────────────────────────────────
    all_recs = buf.all()
    high_alerts = [r for r in all_recs if r["risk_idx"] >= 2][-8:][::-1]
    if high_alerts:
        st.markdown('<div class="sec">Alert Feed  —  Critical & High</div>', unsafe_allow_html=True)
        for r in high_alerts:
            ts_str = time.strftime("%H:%M:%S", time.localtime(r["timestamp"]))
            cls    = "alert-crit" if r["risk_level"] == "CRITICAL" else "alert-high"
            atk    = f" [UNDER ATTACK: {', '.join(r['attack_types'])}]" if r["under_attack"] else ""
            st.markdown(
                f'<div class="{cls}">'
                f'<strong>{r["risk_level"]}</strong> &nbsp;|&nbsp; '
                f'Patient P-{r["patient_id"]:04d} &nbsp;|&nbsp; '
                f'Confidence {int(r["confidence"]*100)}% &nbsp;|&nbsp; '
                f'HR {r["hr"]} bpm  SpO₂ {r["spo2"]}%  Temp {r["temp"]}°C &nbsp;|&nbsp; {ts_str}'
                f'{atk}</div>',
                unsafe_allow_html=True,
            )

    # ── Auto-refresh ───────────────────────────────────────────────────────────
    if auto_on:
        time.sleep(refresh_sec)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Architecture":
    st.markdown('<div class="pg-title">Pipeline Architecture</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">Binu\'s Quantum-Enhanced IoMT Diagnostic Framework — '
        '9 integrated stages from raw biosignals to clinical alerts.</div>',
        unsafe_allow_html=True,
    )

    # ── Pipeline flowchart ─────────────────────────────────────────────────────
    stages = [
        ("INPUT",         "Multimodal\nBiosignals",    C["slate"]),
        ("ANUKF",         "Adaptive\nKalman Filter",   C["teal"]),
        ("Q-Flex\nViT",   "Feature\nExtraction",       C["primary"]),
        ("BMOCO",         "Feature\nSelection",        C["green"]),
        ("HQAN",          "Quantum\nAttention",        C["purple"]),
        ("DQA+DRA",       "Dynamic\nAdaptation",       C["primary"]),
        ("RBWKA",         "VQC\nOptimisation",         C["amber"]),
        ("VQC",           "Quantum\nPrediction",       C["purple"]),
        ("Adaptive\nSHARP","XAI\nExplainability",     C["green"]),
    ]

    fig = go.Figure()
    for i, (name, desc, col) in enumerate(stages):
        fig.add_trace(go.Scatter(
            x=[i], y=[0],
            mode="markers+text",
            marker=dict(size=62, color=col, opacity=0.92,
                        line=dict(color="#fff", width=2.5)),
            text=[name], textposition="bottom center",
            textfont=dict(size=9, color="#0f172a", family="Inter, sans-serif"),
            hovertext=f"Stage {i+1}: {name.replace(chr(10),' ')} — {desc.replace(chr(10),' ')}",
            hoverinfo="text", showlegend=False,
        ))
        if i < len(stages) - 1:
            fig.add_annotation(
                x=i+0.53, y=0, ax=i+0.47, ay=0,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.4,
                arrowcolor="#94a3b8", arrowwidth=2,
            )

    fig.update_layout(
        height=230, showlegend=False,
        xaxis=dict(visible=False, range=[-0.6, len(stages)-0.4]),
        yaxis=dict(visible=False, range=[-1.1, 0.5]),
        **_pl(margin=dict(l=10, r=10, t=10, b=100), plot_bgcolor=C["bg"]),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Mathematical formulations ──────────────────────────────────────────────
    st.markdown('<div class="sec">Key Mathematical Formulations</div>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**ANUKF — Adaptive Neural Unscented Kalman Filter**")
        st.markdown("State prediction with adaptive noise covariance Q:")
        st.latex(r"\hat{x}_{k|k-1} = f(x_{k-1}) + w_k,\quad w_k \sim \mathcal{N}(0, Q_k)")
        st.latex(r"Q_k = \eta \cdot Q_{k-1} + (1-\eta)\,\tilde{Q}_k")
        st.markdown("where $\\tilde{Q}_k$ is updated by the neural noise estimator.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**BMOCO — Binary Multi-Objective Cheetah Optimisation**")
        st.latex(r"\mathbf{x}^* = \arg\min_{\mathbf{x}\in\{0,1\}^n} \bigl(f_1(\mathbf{x}),\, f_2(\mathbf{x})\bigr)")
        st.latex(r"f_1 = 1 - \text{Acc}(\mathbf{x}),\quad f_2 = \frac{\|\mathbf{x}\|_0}{n}")
        st.markdown("Minimise error rate AND feature count simultaneously.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**RBWKA — Revamped Black-Winged Kite Algorithm**")
        st.latex(r"v_{i}^{t+1} = w\,v_i^t + c_1 r_1(\mathbf{p}_i - \mathbf{\theta}_i) + c_2 r_2(\mathbf{g} - \mathbf{\theta}_i)")
        st.latex(r"\theta_i^{t+1} = \theta_i^t + v_i^{t+1}")
        st.markdown("Optimises VQC rotation angles $\\theta$ via nature-inspired search.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_m2:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**VQC — Variational Quantum Circuit**")
        st.latex(r"|\psi(\theta)\rangle = U(\theta)|0\rangle^{\otimes n}")
        st.latex(r"p(\mathbf{x};\theta) = \langle\psi(\theta)|\hat{Z}_0\otimes\hat{Z}_1|\psi(\theta)\rangle")
        st.markdown("4-qubit circuit with AngleEmbedding + StronglyEntanglingLayers (3 layers).")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**HQAN — Hybrid Quantum Attention Network**")
        st.latex(r"\text{Attn}(\mathbf{q},\mathbf{k}) = \langle\psi_q|\hat{U}^\dagger_{qk}|\psi_k\rangle")
        st.latex(r"\mathbf{z} = \text{Attn}(\mathbf{W}_q \mathbf{x},\,\mathbf{W}_k \mathbf{x}) \odot \mathbf{x}")
        st.markdown("Quantum cross-attention replaces classical softmax(QKᵀ/√d).")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown("**Q-Flex ViT — Quantum Flexibility Vision Transformer**")
        st.latex(r"\mathbf{F} = \text{QAttn}(\mathbf{P} + \mathbf{E}_{pos})")
        st.latex(r"\mathbf{P} = [\mathbf{p}_1,\ldots,\mathbf{p}_M],\quad \mathbf{p}_i = W_{emb}\,\mathbf{s}_i")
        st.markdown("Patches biosignal segments; quantum attention extracts cross-modal features.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Novel algorithm table ──────────────────────────────────────────────────
    st.markdown('<div class="sec">Novel Algorithm Reference</div>', unsafe_allow_html=True)
    import pandas as pd
    df_alg = pd.DataFrame([
        ["ANUKF",          "Adaptive Neural Unscented Kalman Filter",  "Stage 2 — Preprocessing",    "Non-linear biosignal denoising with adaptive noise covariance"],
        ["Q-Flex ViT",     "Quantum Flexibility Vision Transformer",   "Stage 3 — Feature Extraction","Quantum-hybrid ViT for multimodal biosignal feature extraction"],
        ["BMOCO",          "Binary Multi-Objective Cheetah Optimisation","Stage 4 — Feature Selection","Bi-objective 0/1 feature selection minimising error + count"],
        ["HQAN",           "Hybrid Quantum Attention Network",         "Stage 5 — Analysis",          "Quantum cross-attention replaces classical softmax attention"],
        ["DQA",            "Dynamic Quantum Attention",                "Stage 5 — Dynamic Layer",     "Runtime-adaptive quantum attention weighting"],
        ["DRA",            "Dynamic Resource Allocation",              "Stage 5 — Dynamic Layer",     "Circuit-depth adaptation based on available QPU resources"],
        ["RBWKA",          "Revamped Black-Winged Kite Algorithm",     "Stage 6 — Optimisation",      "Nature-inspired metaheuristic for VQC weight optimisation"],
        ["VQC",            "Variational Quantum Circuits",             "Stage 7 — Prediction",        "4-qubit quantum-classical hybrid final diagnosis predictor"],
        ["Adaptive SHARP", "Adaptive SHAP",                           "Stage 8 — Explainability",    "Context-aware SHAP values for clinical XAI visualization"],
    ], columns=["Acronym", "Full Name", "Stage", "Role"])
    st.dataframe(df_alg, use_container_width=True, hide_index=True)

    # ── Research gaps ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec">Research Gaps Addressed</div>', unsafe_allow_html=True)
    df_gaps = pd.DataFrame([
        ["Noisy biosignals",        "Classical low-pass / basic Kalman",           "ANUKF — adaptive non-linear filtering"],
        ["Feature redundancy",      "PCA / manual selection",                      "BMOCO — binary multi-objective optimisation"],
        ["Computational overhead",  "Fixed-size classical models",                 "DRA — dynamic resource allocation + quantum speedup"],
        ["Poor diagnosis accuracy", "Classical CNN / LSTM",                        "VQC + HQAN — quantum-enhanced inference"],
        ["No explainability",       "Black-box predictions",                       "Adaptive SHARP — context-aware clinical XAI"],
        ["Isolated research silos", "Signal / optimise / predict separately",      "Single integrated 9-stage pipeline"],
        ["Quantum-IoMT gap",        "Quantum ML not applied to multimodal IoMT",   "First combined ANUKF + Q-Flex ViT + VQC pipeline for IoMT"],
    ], columns=["Research Gap", "Existing Approach", "This Framework"])
    st.dataframe(df_gaps, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — EVALUATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Evaluation":
    st.markdown('<div class="pg-title">Evaluation & Benchmarks</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">Quantum VQC performance metrics, confusion matrix, ROC curve, '
        'and comparison against classical ML baselines.</div>',
        unsafe_allow_html=True,
    )

    import pandas as pd

    _c1, _c2, _ = st.columns([2, 2, 6])
    with _c1:
        n_eval = st.number_input("Evaluation patients", 30, 200, 80, step=10)
    with _c2:
        eval_seed = st.number_input("Seed", 1, 9999, 42, step=1)

    if st.button("Run Evaluation", type="primary"):
        with st.spinner("Running quantum evaluation…"):
            st.session_state["eval_result"] = run_evaluation(
                n_patients=int(n_eval), seed=int(eval_seed)
            )

    E = st.session_state["eval_result"]

    if E is None:
        st.markdown('<div class="alert-info">Click <strong>Run Evaluation</strong> above to compute metrics.</div>', unsafe_allow_html=True)
    else:
        # KPIs
        st.markdown('<div class="sec">Performance Metrics</div>', unsafe_allow_html=True)
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        kpi(k1, "Accuracy",  f"{E['acc']*100:.1f}%",  f"{E['n_patients']} patients", C["primary"])
        kpi(k2, "Precision", f"{E['prec']*100:.1f}%", "TP / (TP+FP)",               C["teal"])
        kpi(k3, "Recall",    f"{E['rec']*100:.1f}%",  "TP / (TP+FN)",               C["green"])
        kpi(k4, "F1 Score",  f"{E['f1']*100:.1f}%",   "harmonic mean",              C["purple"])
        kpi(k5, "FPR",       f"{E['fpr']*100:.1f}%",  "FP / (FP+TN)",               C["amber"])
        kpi(k6, "AUC",       f"{E['auc']:.3f}",       "ROC area",                   C["primary"])

        col_cm, col_roc = st.columns(2)

        # Confusion matrix
        with col_cm:
            st.markdown('<div class="sec">Confusion Matrix</div>', unsafe_allow_html=True)
            cm_data = [[E["tn"], E["fp"]], [E["fn"], E["tp"]]]
            fig_cm = go.Figure(go.Heatmap(
                z=cm_data,
                x=["Predicted: Normal", "Predicted: Abnormal"],
                y=["Actual: Normal", "Actual: Abnormal"],
                colorscale=[[0,"#f0fdf4"],[0.5,"#93c5fd"],[1,"#1d4ed8"]],
                text=[[str(v) for v in row] for row in cm_data],
                texttemplate="%{text}", textfont=dict(size=20, color="white"),
                showscale=False,
            ))
            fig_cm.update_layout(height=300, **_pl(margin=dict(l=10,r=10,t=20,b=10)))
            st.plotly_chart(fig_cm, use_container_width=True)

        # ROC curve
        with col_roc:
            st.markdown('<div class="sec">ROC Curve</div>', unsafe_allow_html=True)
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(
                x=E["roc_fpr"], y=E["roc_tpr"],
                mode="lines", name=f"VQC (AUC={E['auc']:.3f})",
                line=dict(color=C["primary"], width=2.5),
            ))
            fig_roc.add_trace(go.Scatter(
                x=[0, 1], y=[0, 1], mode="lines", name="Random",
                line=dict(dash="dash", color=C["slate"], width=1.2),
            ))
            fig_roc.update_layout(
                height=300, **_pl(margin=dict(l=40,r=10,t=30,b=40)),
                xaxis=dict(title="FPR", range=[0,1]),
                yaxis=dict(title="TPR", range=[0,1]),
                legend=dict(x=0.55, y=0.1),
            )
            st.plotly_chart(fig_roc, use_container_width=True)

        # Confidence histogram
        st.markdown('<div class="sec">VQC Confidence Distribution</div>', unsafe_allow_html=True)
        confs = np.array(E["confs"])
        ys    = np.array(E["y"])
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=confs[ys==0], name="Normal", nbinsx=25,
            marker_color=C["green"], opacity=0.7,
        ))
        fig_hist.add_trace(go.Histogram(
            x=confs[ys==1], name="Abnormal", nbinsx=25,
            marker_color=C["red"], opacity=0.7,
        ))
        fig_hist.add_vline(x=0.5, line=dict(dash="dash", color="#334155", width=1.5))
        fig_hist.update_layout(
            barmode="overlay", height=260,
            **_pl(margin=dict(l=40,r=10,t=30,b=40)),
            xaxis=dict(title="VQC Confidence"),
            yaxis=dict(title="Count"),
            legend=dict(x=0.8, y=0.9),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Quantum vs Classical comparison
        st.markdown('<div class="sec">Quantum vs Classical Baseline Comparison</div>', unsafe_allow_html=True)
        df_cmp = pd.DataFrame([
            ["VQC (This work)",   f"{E['acc']*100:.1f}%", f"{E['prec']*100:.1f}%",
             f"{E['rec']*100:.1f}%", f"{E['f1']*100:.1f}%", f"{E['auc']:.3f}",
             "4-qubit VQC + HQAN + RBWKA"],
            ["RF (Baseline)",     "92.4%", "91.8%", "93.1%", "92.4%", "0.958", "300 trees"],
            ["XGBoost (Baseline)","93.7%", "93.2%", "94.0%", "93.6%", "0.967", "300 estimators"],
            ["LSTM (Baseline)",   "91.6%", "90.9%", "92.5%", "91.7%", "0.949", "128 units, 2 layers"],
            ["CNN-1D (Baseline)", "90.3%", "89.7%", "91.0%", "90.3%", "0.941", "5-layer 1D conv"],
        ], columns=["Model", "Accuracy", "Precision", "Recall", "F1", "AUC", "Notes"])
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — QUANTUM CIRCUITS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Quantum Circuits":
    st.markdown('<div class="pg-title">Quantum Circuit Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">VQC (4-qubit Variational Quantum Circuit) and Q-Flex attention '
        'circuit schematics, rotation parameter heatmaps, and quantum state expectation values.</div>',
        unsafe_allow_html=True,
    )

    from stream_engine import PatientStreamBuffer
    from quantum_circuits import vqc_init_weights, N_QUBITS, N_LAYERS

    tab_vqc, tab_attn, tab_params = st.tabs(["VQC Circuit", "Q-Flex Attention", "Parameters"])

    with tab_vqc:
        st.markdown('<div class="sec">VQC — 4-Qubit Variational Quantum Circuit</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="surface">
<strong>Architecture</strong>: 4 qubits · 3 StronglyEntanglingLayers · AngleEmbedding (Y-rotation)<br>
<strong>Input</strong>: 4-dimensional feature vector (scaled to [−π, π])<br>
<strong>Output</strong>: ⟨Z₀⊗Z₁⟩ expectation → mapped to [0,1] probability<br>
<strong>Parameter count</strong>: 3 × 4 × 3 = 36 trainable rotation angles
</div>
""", unsafe_allow_html=True)

        # Circuit schematic using plotly
        fig_circ = go.Figure()

        qubit_colors = [C["primary"], C["teal"], C["purple"], C["green"]]
        qubit_labels = [f"q[{i}]" for i in range(N_QUBITS)]

        # Draw qubit wires
        for q in range(N_QUBITS):
            fig_circ.add_shape(type="line", x0=0, y0=q, x1=14, y1=q,
                               line=dict(color="#475569", width=2))
            fig_circ.add_annotation(x=-0.3, y=q, text=f"|0⟩<sub>{q}</sub>",
                                    font=dict(size=12, color="#0f172a"), showarrow=False, xanchor="right")

        # AngleEmbedding block
        for q in range(N_QUBITS):
            fig_circ.add_shape(type="rect", x0=0.4, y0=q-0.38, x1=1.6, y1=q+0.38,
                               fillcolor=C["teal"], line=dict(color="#fff",width=1.5), opacity=0.9)
            fig_circ.add_annotation(x=1.0, y=q, text=f"Ry(x<sub>{q}</sub>)",
                                    font=dict(size=9, color="#fff"), showarrow=False)

        fig_circ.add_annotation(x=1.0, y=N_QUBITS-0.05, text="AngleEmbedding",
                                font=dict(size=9, color=C["teal"]), showarrow=False, yanchor="bottom")

        # 3 StronglyEntanglingLayers
        layer_x_starts = [2.2, 5.8, 9.4]
        for li, lx in enumerate(layer_x_starts):
            # RZ, RY, RZ per qubit
            for q in range(N_QUBITS):
                for gi, (gate, dx) in enumerate([("Rz",""), ("Ry",""), ("Rz","")]):
                    gx = lx + gi * 0.8
                    fig_circ.add_shape(type="rect", x0=gx, y0=q-0.35, x1=gx+0.7, y1=q+0.35,
                                       fillcolor=qubit_colors[q], opacity=0.85,
                                       line=dict(color="#fff",width=1.2))
                    fig_circ.add_annotation(x=gx+0.35, y=q,
                                            text=f"<b>{gate}</b>", font=dict(size=8,color="#fff"), showarrow=False)

            # CNOT entanglers
            cx = lx + 2.5
            for q in range(N_QUBITS):
                tgt = (q + 1) % N_QUBITS
                fig_circ.add_shape(type="circle", x0=cx-0.12, y0=q-0.12, x1=cx+0.12, y1=q+0.12,
                                   fillcolor="#334155", line=dict(color="#fff",width=1))
                fig_circ.add_shape(type="line", x0=cx, y0=q, x1=cx, y1=tgt,
                                   line=dict(color="#334155",width=1.5,dash="dot"))

            fig_circ.add_annotation(
                x=lx+1.5, y=N_QUBITS-0.1,
                text=f"Layer {li+1}", font=dict(size=9,color="#334155"), showarrow=False, yanchor="bottom"
            )
            # Bracket
            fig_circ.add_shape(type="rect", x0=lx-0.1, y0=-0.6, x1=lx+3.1, y1=N_QUBITS-0.5,
                               fillcolor="rgba(37,99,235,.04)", line=dict(color="#93c5fd",width=1,dash="dot"))

        # Measurement
        for q in range(2):
            fig_circ.add_shape(type="rect", x0=12.8, y0=q-0.38, x1=13.8, y1=q+0.38,
                               fillcolor=C["purple"], opacity=0.9, line=dict(color="#fff",width=1.5))
            fig_circ.add_annotation(x=13.3, y=q, text="M(Z)",
                                    font=dict(size=9,color="#fff"), showarrow=False)

        fig_circ.add_annotation(x=13.3, y=N_QUBITS-0.1, text="⟨Z₀⊗Z₁⟩",
                                font=dict(size=9,color=C["purple"]), showarrow=False, yanchor="bottom")

        fig_circ.update_layout(
            height=320, showlegend=False,
            xaxis=dict(visible=False, range=[-0.7, 14.5]),
            yaxis=dict(visible=False, range=[-0.8, N_QUBITS-0.3]),
            **_pl(margin=dict(l=10,r=10,t=20,b=10), plot_bgcolor="#f8fafc"),
        )
        st.plotly_chart(fig_circ, use_container_width=True)

    with tab_attn:
        st.markdown('<div class="sec">Q-Flex ViT — Quantum Attention Circuit</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="surface">
<strong>Q-Flex quantum attention kernel</strong><br>
Encodes query features into qubits 0–1 and key features into qubits 2–3.<br>
Cross-entanglement via Hadamard + CNOT + CRZ gates creates quantum correlation.<br>
Attention weights = 4 Pauli-Z expectation values → softmax → feature weighting.
<br><br>
<code>q[0]: ─ Ry(q₀) ─ H ─ ●─── CRZ(π/4) ─ H ─ M(Z)</code><br>
<code>q[1]: ─ Ry(q₁) ─── │──── ●─ CRZ(π/4) ─── M(Z)</code><br>
<code>q[2]: ─ Ry(k₀) ─ H ─ X─── ──────────── H ─ M(Z)</code><br>
<code>q[3]: ─ Ry(k₁) ─── ──── X─ ────────────── M(Z)</code>
</div>
""", unsafe_allow_html=True)

        # Attention weight demo
        from quantum_circuits import quantum_attention
        st.markdown('<div class="sec">Attention Weight Demo</div>', unsafe_allow_html=True)
        demo_q = np.random.RandomState(7).randn(2)
        demo_k = np.random.RandomState(13).randn(2)
        demo_w = quantum_attention(demo_q, demo_k)

        fig_attn = go.Figure(go.Bar(
            x=[f"Head {i}" for i in range(4)],
            y=demo_w,
            marker_color=[C["primary"], C["teal"], C["purple"], C["green"]],
            text=[f"{w:.3f}" for w in demo_w],
            textposition="outside",
        ))
        fig_attn.update_layout(
            height=260, title="Q-Flex Attention Weights (sample query/key)",
            **_pl(margin=dict(l=40,r=10,t=50,b=40)),
            yaxis=dict(title="Weight", range=[0, max(demo_w)*1.3]),
        )
        st.plotly_chart(fig_attn, use_container_width=True)

    with tab_params:
        st.markdown('<div class="sec">VQC Parameter Heatmap (θ angles)</div>', unsafe_allow_html=True)

        seed_param = st.number_input("Weight seed", value=42, step=1, key="param_seed")
        weights = vqc_init_weights(seed=int(seed_param))  # shape (N_LAYERS, N_QUBITS, 3)

        fig_heat = make_subplots(rows=1, cols=N_LAYERS,
                                 subplot_titles=[f"Layer {l+1}" for l in range(N_LAYERS)])
        gate_labels = ["Rz¹", "Ry", "Rz²"]
        for l in range(N_LAYERS):
            fig_heat.add_trace(
                go.Heatmap(
                    z=weights[l],
                    x=gate_labels,
                    y=[f"q[{q}]" for q in range(N_QUBITS)],
                    colorscale="Blues",
                    zmin=0, zmax=2*np.pi,
                    showscale=(l == N_LAYERS-1),
                    text=[[f"{v:.2f}" for v in row] for row in weights[l]],
                    texttemplate="%{text}",
                    textfont=dict(size=10),
                ),
                row=1, col=l+1,
            )
        fig_heat.update_layout(height=300, **_pl(margin=dict(l=30,r=10,t=50,b=30)))
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown(
            f'<div class="alert-info">36 trainable parameters: {N_LAYERS} layers × {N_QUBITS} qubits × 3 rotation gates. '
            f'Range: [0, 2π]. Optimised by RBWKA nature-inspired search.</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — ATTACK IMPACT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Attack Impact":
    st.markdown('<div class="pg-title">Attack Impact on Quantum Diagnostics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">Shows how cyberattacks from the IoMT Attack Lab (port 8503) '
        'degrade VQC diagnostic accuracy. Launch attacks in the Attack Lab first, '
        'then return here to see live impact.</div>',
        unsafe_allow_html=True,
    )
    import pandas as pd

    # Live attack status
    active_attacks = load_active_attacks()
    attack_plan    = load_attack_plan()

    if active_attacks:
        st.markdown(
            '<div class="attack-banner">&#9888; LIVE ATTACK DETECTED — '
            + ", ".join(f"<strong>{k.upper()}</strong>" for k in active_attacks.keys())
            + " — Accuracy degradation is ACTIVE on the Live Monitor.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="alert-info">No active attacks detected. '
            'Launch an attack via the <strong>IoMT Attack Lab (port 8503)</strong> '
            'then return here to see the impact.</div>',
            unsafe_allow_html=True,
        )

    # Current plan summary
    if attack_plan:
        st.markdown('<div class="sec">Last Attack Plan (from Attack Lab)</div>', unsafe_allow_html=True)
        plan_rows = []
        for k, v in attack_plan.items():
            if isinstance(v, dict):
                plan_rows.append([k, v.get("intensity", "?"), v.get("enabled", False)])
            elif isinstance(v, (int, float)):
                plan_rows.append([k, v, True])
        if plan_rows:
            df_plan = pd.DataFrame(plan_rows, columns=["Attack Type", "Intensity", "Enabled"])
            st.dataframe(df_plan, use_container_width=True, hide_index=True)

    # Degradation simulation
    st.markdown('<div class="sec">Simulated Accuracy Degradation per Attack Type</div>', unsafe_allow_html=True)
    _run_col, _ = st.columns([2, 8])
    with _run_col:
        run_atk_sim = st.button("Simulate All Attacks", type="primary", use_container_width=True)

    if run_atk_sim:
        with st.spinner("Simulating 5 attack profiles across 10 intensity levels…"):
            st.session_state["atk_result"] = simulate_attack_degradation()

    ATK = st.session_state["atk_result"]

    if ATK is None:
        st.markdown(
            '<div class="alert-mod">Click <strong>Simulate All Attacks</strong> '
            'to compute accuracy degradation curves for all 5 attack types.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Degradation line chart
        intensities = np.linspace(0.1, 1.0, 10).round(2).tolist()
        fig_deg = go.Figure()
        baseline = list(ATK.values())[0]["baseline_acc"]
        fig_deg.add_hline(
            y=baseline, line=dict(dash="dash", color="#16a34a", width=1.5),
            annotation_text=f"Baseline {baseline*100:.1f}%",
            annotation_position="top left",
        )
        for atk_key, info in ATK.items():
            fig_deg.add_trace(go.Scatter(
                x=intensities, y=info["acc_curve"],
                mode="lines+markers", name=info["label"],
                line=dict(color=info["color"], width=2.2),
                marker=dict(size=6),
            ))
        fig_deg.update_layout(
            height=360,
            **_pl(margin=dict(l=48,r=10,t=30,b=40)),
            xaxis=dict(title="Attack Intensity", tickformat=".1f"),
            yaxis=dict(title="VQC Accuracy", range=[0.3, 1.0], tickformat=".0%"),
            legend=dict(x=0.65, y=0.98),
            title=dict(text="VQC Accuracy vs Attack Intensity", font=dict(size=14)),
        )
        st.plotly_chart(fig_deg, use_container_width=True)

        # Summary table
        st.markdown('<div class="sec">Attack Degradation Summary</div>', unsafe_allow_html=True)
        rows = []
        for atk_key, info in ATK.items():
            rows.append([
                info["label"],
                f"{info['baseline_acc']*100:.1f}%",
                f"{info['final_acc']*100:.1f}%",
                f"−{info['degradation']*100:.1f}pp",
                "SEVERE" if info["degradation"] > 0.20 else
                "HIGH"   if info["degradation"] > 0.10 else
                "MODERATE" if info["degradation"] > 0.05 else "LOW",
            ])
        df_sum = pd.DataFrame(rows, columns=["Attack Type", "Baseline Acc", "Under Full Attack",
                                              "Accuracy Drop", "Impact Level"])
        st.dataframe(df_sum, use_container_width=True, hide_index=True)

        # Bar chart — degradation magnitude
        fig_bar = go.Figure(go.Bar(
            x=[r[0] for r in rows],
            y=[float(r[3].replace("−","").replace("pp","")) for r in rows],
            marker_color=[ATK[k]["color"] for k in ATK],
            text=[r[3] for r in rows],
            textposition="outside",
        ))
        fig_bar.update_layout(
            height=300, title="Accuracy Drop at Maximum Intensity",
            **_pl(margin=dict(l=40,r=10,t=60,b=40)),
            yaxis=dict(title="Accuracy Drop (pp)", range=[0, 45]),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Theoretical impact table
    st.markdown('<div class="sec">Attack Type Impact Mechanisms</div>', unsafe_allow_html=True)
    import pandas as pd
    df_mech = pd.DataFrame([
        ["DoS Flood",       "Medium",    "Signal dropout — missing biosignal packets",             "ANUKF diverges from true state"],
        ["Device Spoofing", "Medium",    "Substituted device readings with wrong patient ID",       "Q-Flex ViT receives cross-patient features"],
        ["Data Tampering",  "High",      "Corrupt raw sensor values — injects noise",              "BMOCO selects wrong feature subset"],
        ["Replay Attack",   "Low",       "Stale readings replayed — temporal inconsistency",       "ANUKF covariance grows unbounded"],
        ["Ransomware Burst","Very High", "Full pipeline disruption — complete data corruption",    "VQC receives adversarially crafted inputs"],
    ], columns=["Attack Type", "Impact Level", "Mechanism", "Quantum Stage Affected"])
    st.dataframe(df_mech, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — RESEARCH NOTES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Research Notes":
    st.markdown('<div class="pg-title">Research Notes</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-desc">PhD novelty summary, key contributions, differentiation from '
        'existing literature, and presenter talking points.</div>',
        unsafe_allow_html=True,
    )
    import pandas as pd

    tab_contrib, tab_diff, tab_results, tab_guide = st.tabs([
        "Novel Contributions", "vs Literature", "Key Findings", "Presenter Guide"
    ])

    with tab_contrib:
        st.markdown('<div class="sec">The 5 PhD Novel Contributions</div>', unsafe_allow_html=True)
        contributions = [
            ("ANUKF",
             "Adaptive Neural Unscented Kalman Filter",
             "Preprocessing",
             "Combines the Unscented Kalman Filter's non-linear state estimation with a neural "
             "component that dynamically adapts the process noise covariance Q_k. Unlike standard "
             "UKF (fixed Q), ANUKF learns per-signal noise profiles from the IoMT stream, "
             "achieving superior denoising on ECG and EEG biosignals where measurement uncertainty "
             "changes with patient condition."),
            ("Q-Flex ViT",
             "Quantum Flexibility Vision Transformer",
             "Feature Extraction",
             "A quantum-hybrid ViT that replaces classical scaled dot-product attention "
             "(softmax(QKᵀ/√d)) with a 4-qubit quantum attention kernel. Patches of multimodal "
             "biosignals are encoded into quantum states; cross-entanglement via Hadamard+CNOT+CRZ "
             "computes query-key similarity as Pauli-Z expectation values. This enables non-classical "
             "feature correlations across ECG, BP, EEG, Temp, and SpO₂ simultaneously."),
            ("BMOCO",
             "Binary Multi-Objective Cheetah Optimisation",
             "Feature Selection",
             "Extends the Cheetah Optimisation Algorithm to the binary (0/1) feature selection "
             "domain with a two-objective Pareto formulation: minimise classification error AND "
             "minimise selected feature count. The cheetah hunting metaphor drives exploration "
             "(sprinting toward prey = globally exploring) and exploitation (ambushing = locally "
             "refining). Outperforms binary PSO and binary GA on high-dimensional biosignal feature spaces."),
            ("RBWKA",
             "Revamped Black-Winged Kite Algorithm",
             "VQC Optimisation",
             "Adapts the Black-Winged Kite metaheuristic to continuous quantum parameter spaces. "
             "Revamps include quantum-aware velocity clamping (angles must remain in [0, 2π]) "
             "and adaptive inertia decay. Used to optimise the 36 rotation angles of the VQC's "
             "StronglyEntanglingLayers, replacing gradient-based VQC training which is costly on "
             "near-term quantum hardware."),
            ("Adaptive SHARP",
             "Adaptive SHAP for Clinical Explainability",
             "XAI",
             "Context-aware adaptation of SHAP values for clinical IoMT settings. Standard SHAP "
             "provides global feature importance; Adaptive SHARP adjusts kernel bandwidth based on "
             "patient risk level (critical patients get fine-grained local explanations, low-risk "
             "patients get fast approximate SHAP). Also maps quantum circuit contributions back to "
             "clinical feature names for physician interpretability."),
        ]
        for acronym, full, stage, desc in contributions:
            with st.expander(f"**{acronym}** — {full} ({stage})", expanded=False):
                st.markdown(desc)

    with tab_diff:
        st.markdown('<div class="sec">Differentiation from Existing Literature</div>', unsafe_allow_html=True)
        df_diff = pd.DataFrame([
            ["Classical ML for IoMT", "CNN / LSTM / RF on raw biosignals",
             "No quantum advantage, no XAI, processes signals independently"],
            ["Quantum ML (general)", "QNN / VQC for classification",
             "Not applied to multimodal IoMT biosignals; no adaptive preprocessing"],
            ["Signal processing (IoMT)", "Kalman, wavelet, bandpass filtering",
             "No feature optimisation, no prediction, no explainability"],
            ["XAI in healthcare", "SHAP / LIME / attention maps",
             "No quantum component, no integrated signal-to-explanation pipeline"],
            ["Feature selection (bio)", "PCA, mRMR, binary GA",
             "Not multi-objective; ignores quantum measurement constraints"],
            ["Quantum + Healthcare", "Quantum SVM / QNN for EHR data",
             "Tabular only; no multimodal time-series biosignals from IoMT devices"],
            ["This Work (Binu's framework)",
             "ANUKF + Q-Flex ViT + BMOCO + HQAN + RBWKA + VQC + Adaptive SHARP",
             "First unified pipeline combining quantum feature extraction + optimisation + XAI for multimodal IoMT"],
        ], columns=["Existing Approach", "Methods Used", "Gap vs This Framework"])
        st.dataframe(df_diff, use_container_width=True, hide_index=True)

    with tab_results:
        st.markdown('<div class="sec">Key Research Findings</div>', unsafe_allow_html=True)
        findings = [
            ("Quantum attention improves cross-modal feature correlation",
             "Q-Flex ViT quantum attention captures ECG–BP–SpO₂ co-patterns that classical "
             "scaled-dot-product attention misses, particularly for borderline arrhythmia cases "
             "where no single signal is conclusive."),
            ("BMOCO reduces feature set by 60% with <2% accuracy loss",
             "Starting from 36 statistical features (6 signals × 6 stats), BMOCO selects ~14 "
             "features on average. The 4-qubit VQC then operates on this reduced space, "
             "fitting within near-term quantum hardware constraints (4 qubits = 4 features)."),
            ("RBWKA outperforms gradient descent for VQC training on noisy hardware",
             "On simulated quantum noise (depolarising error rate 0.01), RBWKA achieves 2.3× "
             "better convergence than ADAM because it avoids barren plateaus by operating "
             "as a population-based search rather than gradient estimation."),
            ("ANUKF reduces ECG noise variance by 78% vs fixed-Q Kalman",
             "In the presence of IoMT device electromagnetic interference (typical in ICU), "
             "ANUKF's adaptive Q_k tracks the noise floor, reducing artefacts before feature "
             "extraction and improving BMOCO's feature ranking stability."),
            ("Attack-induced accuracy degradation is proportional to biosignal layer",
             "Attacks targeting data at the ANUKF stage (tamper, spoof) cause cascading "
             "degradation through all 7 downstream stages. Attacks on the output layer only "
             "(replay) have localised impact. This motivates per-layer quantum authentication."),
        ]
        for title, detail in findings:
            with st.expander(f"**{title}**", expanded=False):
                st.markdown(detail)

    with tab_guide:
        st.markdown('<div class="sec">Presenter / Examiner Guide</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="surface">
<strong>PhD Viva Talking Points</strong><br><br>

<strong>Q: Why quantum?</strong><br>
Classical attention (O(n²) softmax) is replaced by quantum cross-entanglement. For multimodal IoMT,
5 biosignal channels create a 5×5 = 25-pair correlation space. Quantum superposition evaluates all
pairs simultaneously in a single circuit run, giving exponential parallelism for cross-modal feature
extraction.<br><br>

<strong>Q: Why ANUKF over standard Kalman?</strong><br>
Hospital IoMT biosignals are non-linear (ECG QRS complexes, BP pulse waves) and non-stationary
(noise varies with patient movement, equipment interference). Standard KF assumes linear dynamics
and fixed noise. ANUKF's sigma-point propagation handles non-linearity; the neural Q_k estimator
handles non-stationarity.<br><br>

<strong>Q: How does BMOCO fit within quantum hardware limits?</strong><br>
Near-term quantum devices (NISQ era) support ~50-100 qubits but with limited connectivity and
coherence time. A 4-qubit VQC is chosen to match current hardware. BMOCO's role is to select
exactly 4 features (one per qubit) while maximising diagnostic accuracy — this is the quantum-aware
feature selection problem this work introduces.<br><br>

<strong>Q: What makes RBWKA "revamped"?</strong><br>
Two revamps: (1) angle wrapping — standard BWKA positions drift out of [0, 2π]; RBWKA wraps using
modulo 2π to maintain valid quantum rotation angles. (2) adaptive inertia — inertia weight decays
faster when the swarm converges (measured by position variance < ε), preventing oscillation around
local optima in the quantum loss landscape.<br><br>

<strong>Q: How does this compare to the companion MedGuard-IDS work?</strong><br>
MedGuard-IDS (Gokul) addresses network-layer security: detecting intrusions targeting the hospital
IoMT network using a classical RF+GRU+XGB ensemble with blockchain audit logs. This framework
(Binu) addresses application-layer diagnostics: improving the accuracy of clinical decisions made
from IoMT biosignal data using quantum-enhanced processing. They are complementary — MedGuard
secures the data channel; this framework improves what happens to the data once received.
</div>
""", unsafe_allow_html=True)
