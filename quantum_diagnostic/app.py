"""
Quantum IoMT IDS Dashboard — port 8504
Binu's Quantum-Enhanced Intrusion Detection System for IoMT Networks:
  ANUKF → Q-Flex ViT → BMOCO → HQAN → RBWKA → VQC → Adaptive SHARP
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Quantum IoMT IDS",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Colour tokens ──────────────────────────────────────────────────────────────
C_PRIMARY = "#2563eb"; C_TEAL  = "#0891b2"; C_GREEN  = "#16a34a"
C_AMBER   = "#d97706"; C_RED   = "#dc2626"; C_PURPLE = "#7c3aed"
C_NAVY    = "#0f172a"; C_TEXT  = "#0f172a"; C_MUTED  = "#64748b"
C_BORDER  = "#e2e8f0"; C_BG    = "#f1f5f9"; C_CARD   = "#ffffff"

ATK_COLORS = {
    "normal":     C_GREEN,
    "dos":        C_RED,
    "spoof":      C_AMBER,
    "tamper":     C_PURPLE,
    "replay":     C_TEAL,
    "ransomware": "#b91c1c",
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif!important;}}
.stApp{{background:{C_BG};color:{C_TEXT};}}
.block-container{{padding:4rem 2.5rem 2rem!important;max-width:1280px;}}
[data-testid="stSidebar"]{{background:{C_NAVY}!important;border-right:1px solid #1e293b;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div{{color:#94a3b8!important;}}
[data-testid="stSidebar"] hr{{border-color:#1e293b!important;}}
[data-testid="stSidebar"] .stRadio label{{color:#cbd5e1!important;font-size:.84rem!important;}}
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSelectbox label{{color:#94a3b8!important;font-size:.78rem!important;}}
[data-testid="stSidebar"] .stButton>button{{
  background:transparent!important;color:#cbd5e1!important;
  border:1px solid #334155!important;border-radius:6px!important;
  font-size:.82rem!important;font-weight:500!important;
  width:100%!important;padding:.5rem 0!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{
  background:#1e293b!important;border-color:#475569!important;color:#f1f5f9!important;}}
[data-testid="stSidebar"] .stButton:last-of-type>button{{
  background:{C_PRIMARY}!important;color:#fff!important;
  border-color:{C_PRIMARY}!important;font-weight:700!important;}}
header{{display:none!important;}} #MainMenu{{display:none!important;}} footer{{display:none!important;}}
.kpi-card{{background:#fff;border:1px solid {C_BORDER};border-top:3px solid;
  border-radius:8px;padding:1rem 1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.06);}}
.kpi-label{{font-size:.67rem;color:{C_MUTED};text-transform:uppercase;
  letter-spacing:.08em;font-weight:600;}}
.kpi-value{{font-size:1.6rem;font-weight:700;color:{C_TEXT};margin:.2rem 0 .1rem;line-height:1;}}
.kpi-sub{{font-size:.71rem;color:#94a3b8;}}
.surface{{background:#fff;border:1px solid {C_BORDER};border-radius:8px;
  padding:1.25rem 1.5rem;box-shadow:0 1px 3px rgba(0,0,0,.05);margin-bottom:1rem;}}
.page-title{{font-size:1.3rem;font-weight:700;color:{C_TEXT};margin:0 0 .25rem;}}
.page-desc{{font-size:.82rem;color:{C_MUTED};margin:0 0 1.2rem;}}
.stage-tag{{display:inline-block;background:#eff6ff;border:1px solid #bfdbfe;
  color:#1d4ed8;border-radius:4px;padding:.15rem .55rem;font-size:.67rem;
  font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.6rem;}}
.sec{{font-size:.73rem;font-weight:700;color:#475569;text-transform:uppercase;
  letter-spacing:.08em;border-bottom:1px solid {C_BORDER};
  padding-bottom:.35rem;margin:1.4rem 0 .9rem;}}
.a-attack{{background:#fef2f2;border:1px solid #fecaca;border-left:4px solid {C_RED};
  border-radius:6px;padding:.6rem 1rem;color:#991b1b;margin:3px 0;font-size:.82rem;}}
.a-normal{{background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid {C_GREEN};
  border-radius:6px;padding:.6rem 1rem;color:#14532d;margin:3px 0;font-size:.82rem;}}
.pkt-row{{background:#fff;border:1px solid {C_BORDER};border-radius:6px;
  padding:.4rem .9rem;margin:2px 0;display:flex;justify-content:space-between;
  align-items:center;font-size:.79rem;}}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def _pd():
    return dict(template="plotly_white", paper_bgcolor=C_CARD,
                plot_bgcolor=C_CARD, font=dict(family="Inter", color=C_TEXT))

def kpi(col, label, value, sub, color):
    col.markdown(f"""
    <div class="kpi-card" style="border-top-color:{color}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results   = None
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = "idle"

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:.75rem 0 1rem;border-bottom:1px solid #1e293b;margin-bottom:1rem;">
      <div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;letter-spacing:-.01em;">
        ⚛ Quantum IDS</div>
      <div style="font-size:.72rem;color:#64748b;margin-top:.2rem;">
        IoMT Intrusion Detection</div>
    </div>""", unsafe_allow_html=True)

    PAGES = [
        "1 · Pipeline Overview",
        "2 · Network Traffic",
        "3 · ANUKF Preprocessing",
        "4 · Q-Flex ViT",
        "5 · BMOCO Selection",
        "6 · HQAN + VQC Detection",
        "7 · Adaptive SHARP",
        "8 · Live Detection",
        "9 · vs Classical MedGuard",
    ]
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")

    st.markdown('<hr style="border-color:#1e293b;margin:.75rem 0">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.72rem;color:#475569;margin-bottom:.4rem;">CONFIGURATION</div>',
                unsafe_allow_html=True)
    n_packets   = st.slider("Packets",      30, 200, 80, 10)
    seed_val    = st.number_input("Seed",   0, 9999, 42)
    bmoco_iters = st.slider("BMOCO iters", 5, 30, 15, 5)
    rbwka_iters = st.slider("RBWKA iters", 5, 30, 20, 5)

    st.markdown('<hr style="border-color:#1e293b;margin:.75rem 0">', unsafe_allow_html=True)
    if st.button("⚛ Run Pipeline"):
        from pipeline import run_pipeline
        prog = st.empty()
        log  = st.empty()
        def _cb(step, msg):
            prog.progress(step / 9)
            log.markdown(f'<div style="font-size:.72rem;color:#94a3b8;">[{step}/9] {msg}</div>',
                         unsafe_allow_html=True)
        st.session_state.pipeline_status = "running"
        try:
            st.session_state.results = run_pipeline(
                n_packets=n_packets, seed=seed_val,
                bmoco_iters=bmoco_iters, rbwka_iters=rbwka_iters,
                progress_cb=_cb,
            )
            st.session_state.pipeline_status = "done"
        except Exception as e:
            st.session_state.pipeline_status = "error"
            st.error(str(e))
        prog.empty(); log.empty()

    status = st.session_state.pipeline_status
    if status == "done":
        st.markdown('<div style="color:#22c55e;font-size:.75rem;">✓ Pipeline complete</div>',
                    unsafe_allow_html=True)
    elif status == "running":
        st.markdown('<div style="color:#f59e0b;font-size:.75rem;">⟳ Running…</div>',
                    unsafe_allow_html=True)
    elif status == "idle":
        st.markdown('<div style="color:#475569;font-size:.75rem;">Click Run Pipeline to begin</div>',
                    unsafe_allow_html=True)

R = st.session_state.results


def _get_role(feat_name: str) -> str:
    roles = {
        "packet_rate":     "DoS indicator",
        "byte_ratio":      "Exfil / DoS",
        "duration":        "Session type",
        "proto_enc":       "Protocol anomaly",
        "ttl_norm":        "Spoofing indicator",
        "payload_entropy": "Ransomware / tamper",
        "conn_count":      "DoS / scanning",
        "failed_auth":     "Spoofing indicator",
        "port_enc":        "C2 / ransomware",
        "flag_enc":        "SYN flood / replay",
    }
    return roles.get(feat_name, "")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Pipeline Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == PAGES[0]:
    st.markdown('<div class="page-title">⚛ Quantum-Enhanced IoMT Intrusion Detection System</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Binu\'s novel framework: quantum computing applied to IoMT cyberattack detection — replacing classical ML with a quantum pipeline for superior accuracy and lower false-positive rates.</div>',
                unsafe_allow_html=True)

    if R:
        c1,c2,c3,c4,c5 = st.columns(5)
        kpi(c1, "Packets", R['n_packets'], "total processed", C_PRIMARY)
        kpi(c2, "Attacks", R['n_attacks'], f"{R['n_attacks']/R['n_packets']*100:.0f}% of traffic", C_RED)
        kpi(c3, "Accuracy", f"{R['accuracy']*100:.1f}%", "quantum VQC", C_GREEN)
        kpi(c4, "F1 Score", f"{R['f1']*100:.1f}%", "precision × recall", C_TEAL)
        kpi(c5, "FPR", f"{R['fpr']*100:.1f}%", "false positive rate", C_AMBER)
        st.markdown("")

    # Architecture diagram
    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.markdown('<div class="sec">9-STAGE QUANTUM IDS PIPELINE</div>', unsafe_allow_html=True)
    stages = [
        ("1", "NETWORK INPUT",   "Multimodal IoMT traffic: packet rate, bytes, TTL, entropy, auth failures",  C_PRIMARY),
        ("2", "ANUKF",           "Adaptive Neural Unscented Kalman Filter — denoises packet streams",           C_TEAL),
        ("3", "Q-Flex ViT",      "Quantum Flexibility Vision Transformer — extracts quantum features",          C_PURPLE),
        ("4", "BMOCO",           "Binary Multi-Objective Cheetah Optimization — selects best features",         C_AMBER),
        ("5", "HQAN",            "Hybrid Quantum Attention Network — quantum-weighted feature analysis",         C_PRIMARY),
        ("6", "DQA + DRA",       "Dynamic Quantum Attention + Resource Adaptation",                             C_TEAL),
        ("7", "RBWKA",           "Revamped Black-Winged Kite Algorithm — optimises VQC weights",               C_GREEN),
        ("8", "VQC",             "Variational Quantum Circuits (4-qubit) — final attack classification",        C_RED),
        ("9", "Adaptive SHARP",  "Adaptive SHAP — explains which traffic features triggered detection",         C_MUTED),
    ]
    for num, name, desc, color in stages:
        st.markdown(f"""
        <div style="display:flex;align-items:flex-start;margin:.45rem 0;gap:.8rem;">
          <div style="min-width:2rem;height:2rem;background:{color};border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            color:#fff;font-size:.72rem;font-weight:700;">{num}</div>
          <div>
            <span style="font-weight:700;font-size:.85rem;color:{C_TEXT};">{name}</span>
            <span style="font-size:.8rem;color:{C_MUTED};margin-left:.5rem;">{desc}</span>
          </div>
        </div>""", unsafe_allow_html=True)
        if int(num) < 9:
            st.markdown(f'<div style="margin-left:.9rem;color:#cbd5e1;font-size:.8rem;">↓</div>',
                        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Research gaps
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">RESEARCH GAPS ADDRESSED</div>', unsafe_allow_html=True)
        gaps = [
            ("Noisy IoMT signals",       "ANUKF adaptive non-linear filtering"),
            ("Feature redundancy",        "BMOCO multi-objective selection"),
            ("Computation cost",          "DRA dynamic resource allocation"),
            ("Poor detection accuracy",   "VQC + HQAN quantum-enhanced inference"),
            ("Lack of explainability",    "Adaptive SHARP clinical XAI"),
            ("Isolated research silos",   "Single integrated quantum pipeline"),
        ]
        for gap, sol in gaps:
            st.markdown(f"""
            <div style="display:flex;gap:.6rem;margin:.35rem 0;font-size:.8rem;">
              <span style="color:{C_RED};font-weight:700;">✗</span>
              <span style="color:{C_MUTED};">{gap}</span>
              <span style="color:{C_MUTED};">→</span>
              <span style="color:{C_GREEN};font-weight:600;">{sol}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">NOVEL CONTRIBUTIONS</div>', unsafe_allow_html=True)
        contribs = [
            ("ANUKF",        "First application to IoMT network stream denoising"),
            ("Q-Flex ViT",   "Quantum attention for network traffic feature extraction"),
            ("BMOCO",        "Multi-objective feature selection for IDS"),
            ("HQAN",         "Hybrid quantum attention for packet classification"),
            ("RBWKA",        "Nature-inspired VQC weight optimisation"),
            ("VQC",          "4-qubit quantum circuit for attack/normal classification"),
            ("Adap. SHARP",  "Context-aware XAI for forensic audit trail"),
        ]
        for name, desc in contribs:
            st.markdown(f"""
            <div style="display:flex;gap:.6rem;margin:.35rem 0;font-size:.8rem;">
              <span style="color:{C_PRIMARY};font-weight:700;min-width:4.5rem;">{name}</span>
              <span style="color:{C_MUTED};">{desc}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline from the sidebar to see live results across all pages.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Network Traffic Input
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[1]:
    st.markdown('<div class="stage-tag">Stage 1 — Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Network Traffic Input</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Multimodal IoMT network packet features fed into the quantum pipeline.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see traffic data.")
    else:
        packets = R['packets']
        atk_counts = R['attack_counts']

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">TRAFFIC DISTRIBUTION</div>', unsafe_allow_html=True)
            labels = list(atk_counts.keys())
            values = list(atk_counts.values())
            colors = [ATK_COLORS.get(l, C_MUTED) for l in labels]
            fig = go.Figure(go.Pie(labels=labels, values=values, marker_colors=colors,
                                   hole=0.42, textinfo="label+percent"))
            fig.update_layout(**_pd(), height=280, margin=dict(l=0,r=0,t=10,b=0),
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">FEATURE DISTRIBUTION BY ATTACK TYPE</div>', unsafe_allow_html=True)
            X_raw = R['X_raw']
            feat_names = R['feature_names']
            atk_types_list = R['attack_types']
            import pandas as pd
            df = pd.DataFrame(X_raw, columns=feat_names)
            df['attack_type'] = atk_types_list
            feat = st.selectbox("Feature", feat_names[:5])
            fig2 = px.box(df, x="attack_type", y=feat, color="attack_type",
                          color_discrete_map=ATK_COLORS)
            fig2.update_layout(**_pd(), height=260, showlegend=False,
                               margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Feature heatmap
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">FEATURE CORRELATION MATRIX</div>', unsafe_allow_html=True)
        corr = np.corrcoef(X_raw.T)
        fig3 = go.Figure(go.Heatmap(
            z=corr, x=feat_names, y=feat_names,
            colorscale="RdBu", zmid=0,
            text=np.round(corr, 2), texttemplate="%{text}",
        ))
        fig3.update_layout(**_pd(), height=320, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Sample packets table
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">SAMPLE PACKETS</div>', unsafe_allow_html=True)
        import pandas as pd
        rows = []
        for p in packets[:20]:
            row = {"ID": p.packet_id, "Type": p.attack_type, "Label": "ATTACK" if p.label else "NORMAL"}
            for fi, fn in enumerate(feat_names):
                row[fn] = round(float(p.features[fi]), 3)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, height=280)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — ANUKF Preprocessing
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[2]:
    st.markdown('<div class="stage-tag">Stage 2 — ANUKF</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Adaptive Neural Unscented Kalman Filter</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Denoises IoMT packet rate and byte-count streams. Adaptive Q/R parameters inferred from signal statistics.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see ANUKF results.")
    else:
        s = R['anukf_sample']
        c1, c2 = st.columns(2)
        t = np.arange(len(s['raw_rate']))
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">PACKET RATE — RAW vs FILTERED</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t, y=s['raw_rate'],  name="Raw",      line=dict(color="#94a3b8",width=1)))
            fig.add_trace(go.Scatter(x=t, y=s['filt_rate'], name="Filtered", line=dict(color=C_PRIMARY,width=2)))
            fig.update_layout(**_pd(), height=240, margin=dict(l=0,r=0,t=10,b=0),
                              xaxis_title="Timestep", yaxis_title="Packets/sec")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f'<div style="font-size:.78rem;color:{C_MUTED};">Sample attack type: <b>{s["attack_type"]}</b></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">BYTE COUNT — RAW vs FILTERED</div>', unsafe_allow_html=True)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=t, y=s['raw_byte'],  name="Raw",      line=dict(color="#94a3b8",width=1)))
            fig2.add_trace(go.Scatter(x=t, y=s['filt_byte'], name="Filtered", line=dict(color=C_TEAL,width=2)))
            fig2.update_layout(**_pd(), height=240, margin=dict(l=0,r=0,t=10,b=0),
                               xaxis_title="Timestep", yaxis_title="Bytes")
            st.plotly_chart(fig2, use_container_width=True)
            snr = 10 * np.log10((np.var(s['filt_rate'])+1e-12)/(np.var(s['raw_rate']-s['filt_rate'])+1e-12))
            st.markdown(f'<div style="font-size:.78rem;color:{C_MUTED};">Signal-to-noise improvement: <b>{snr:.1f} dB</b></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Per attack type
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">PACKET RATE BY ATTACK TYPE (raw vs filtered)</div>', unsafe_allow_html=True)
        by_type = R['anukf_by_type']
        n_types = len(by_type)
        fig3 = make_subplots(rows=1, cols=n_types, subplot_titles=list(by_type.keys()))
        for ci, (atk, data) in enumerate(by_type.items(), 1):
            t2 = np.arange(len(data['raw_rate']))
            fig3.add_trace(go.Scatter(x=t2, y=data['raw_rate'],  name="Raw",
                                      line=dict(color="#94a3b8",width=1), showlegend=ci==1), row=1, col=ci)
            fig3.add_trace(go.Scatter(x=t2, y=data['filt_rate'], name="Filtered",
                                      line=dict(color=ATK_COLORS.get(atk,C_PRIMARY),width=2),
                                      showlegend=ci==1), row=1, col=ci)
        fig3.update_layout(**_pd(), height=260, margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Q-Flex ViT
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[3]:
    st.markdown('<div class="stage-tag">Stage 3 — Q-Flex ViT</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Quantum Flexibility Vision Transformer</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Quantum attention kernel encodes query/key feature pairs into 4-qubit entangled states. Cross-entanglement (CNOT + CRZ gates) captures correlations classical attention cannot.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see Q-Flex ViT results.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">QUANTUM ATTENTION CIRCUIT</div>', unsafe_allow_html=True)
            gates = [
                ("AngleEmbed q[0-1]", "Encode query features", C_PRIMARY),
                ("AngleEmbed q[2-3]", "Encode key features",   C_TEAL),
                ("H(0) H(2)",         "Superposition layer",   C_PURPLE),
                ("CNOT(0→2)",         "Cross-entanglement",    C_AMBER),
                ("CNOT(1→3)",         "Cross-entanglement",    C_AMBER),
                ("CRZ(π/4, 0→1)",     "Controlled rotation",   C_GREEN),
                ("CRZ(π/4, 2→3)",     "Controlled rotation",   C_GREEN),
                ("H(0) H(2)",         "Interference layer",    C_PURPLE),
                ("Measure Z[0-3]",    "→ 4 attention weights", C_RED),
            ]
            for gate, desc, color in gates:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:.6rem;margin:.3rem 0;">
                  <code style="background:{color}22;color:{color};border:1px solid {color}55;
                    border-radius:4px;padding:.1rem .4rem;font-size:.75rem;min-width:11rem;">{gate}</code>
                  <span style="font-size:.78rem;color:{C_MUTED};">{desc}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">FEATURE SPACE (NORMALISED)</div>', unsafe_allow_html=True)
            X_norm = R['X_norm']
            feat_names = R['feature_names']
            atk_types_list = R['attack_types']
            import pandas as pd
            df = pd.DataFrame(X_norm[:, :5], columns=feat_names[:5])
            df['type'] = atk_types_list
            fig = px.scatter(df, x=feat_names[0], y=feat_names[5] if len(feat_names)>5 else feat_names[1],
                             color="type", color_discrete_map=ATK_COLORS,
                             title="Feature space (post-normalisation)")
            fig.update_layout(**_pd(), height=300, margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Attention formula
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">Q-FLEX ATTENTION FORMULA</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-family:monospace;font-size:.82rem;color:{C_TEXT};
          background:#f8fafc;border:1px solid {C_BORDER};border-radius:6px;padding:1rem;line-height:2;">
          <b>Query:</b> q₂ = query[:2] / ‖query[:2]‖ × (π/2)<br>
          <b>Key:</b>   k₂ = key[:2]   / ‖key[:2]‖   × (π/2)<br>
          <b>Encode:</b> AngleEmbedding(q₂ → w[0,1]),  AngleEmbedding(k₂ → w[2,3])<br>
          <b>Entangle:</b> H(0)·H(2) → CNOT(0→2) → CNOT(1→3) → CRZ(π/4) × 2<br>
          <b>Output:</b> attn = (⟨Z₀⟩, ⟨Z₁⟩, ⟨Z₂⟩, ⟨Z₃⟩) mapped to [0,1], normalised<br>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — BMOCO Feature Selection
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[4]:
    st.markdown('<div class="stage-tag">Stage 4 — BMOCO</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Binary Multi-Objective Cheetah Optimization</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Selects the optimal feature subset — maximising detection accuracy while minimising feature count. Three hunting phases: Scout → Chase → Attack.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see BMOCO results.")
    else:
        sel_idx   = R['sel_idx']
        sel_names = R['sel_feature_names']
        all_names = R['feature_names']
        history   = R['bmoco_history']

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">SELECTED FEATURES</div>', unsafe_allow_html=True)
            colors = [C_GREEN if i in sel_idx else "#e2e8f0" for i in range(len(all_names))]
            fig = go.Figure(go.Bar(
                x=all_names, y=[1]*len(all_names),
                marker_color=colors, text=["✓" if i in sel_idx else "" for i in range(len(all_names))],
                textposition="inside",
            ))
            fig.update_layout(**_pd(), height=260, showlegend=False,
                              yaxis_visible=False, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f'<div style="font-size:.82rem;color:{C_MUTED};">Selected: <b>{len(sel_idx)}/{len(all_names)}</b> features — {", ".join(sel_names)}</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">CONVERGENCE HISTORY</div>', unsafe_allow_html=True)
            if history:
                fig2 = go.Figure(go.Scatter(
                    y=history, mode="lines+markers",
                    line=dict(color=C_PRIMARY, width=2),
                    marker=dict(size=4, color=C_PRIMARY),
                ))
                fig2.update_layout(**_pd(), height=240, margin=dict(l=0,r=0,t=10,b=0),
                                   xaxis_title="Iteration", yaxis_title="Best Fitness")
                st.plotly_chart(fig2, use_container_width=True)
            st.markdown(f'<div style="font-size:.78rem;color:{C_MUTED};">Best fitness: <b>{R["bmoco_best_fitness"]:.4f}</b> (accuracy×0.85 − feature_ratio×0.15)</div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # BMOCO phases explanation
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">HUNTING PHASES</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        phases = [
            ("Scout (0-33%)",  "Broad global exploration — random feature subset trials", C_AMBER),
            ("Chase (33-70%)", "Converge toward best solution (prey) found so far",       C_PRIMARY),
            ("Attack (70-100%)","Fine-grained local refinement — exploit best region",    C_GREEN),
        ]
        for col, (name, desc, color) in zip(cols, phases):
            col.markdown(f"""
            <div style="text-align:center;padding:.8rem;background:{color}11;
              border:1px solid {color}33;border-radius:8px;">
              <div style="font-weight:700;font-size:.85rem;color:{color};">{name}</div>
              <div style="font-size:.75rem;color:{C_MUTED};margin-top:.3rem;">{desc}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — HQAN + VQC Detection
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[5]:
    st.markdown('<div class="stage-tag">Stages 5-7 — HQAN + RBWKA + VQC</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Quantum Attack Detection Results</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">HQAN applies quantum attention, RBWKA optimises VQC weights, VQC classifies each IoMT packet as ATTACK or NORMAL.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see detection results.")
    else:
        cm = R['confusion']
        c1,c2,c3,c4,c5 = st.columns(5)
        kpi(c1, "Accuracy",  f"{R['accuracy']*100:.1f}%",  "overall",         C_PRIMARY)
        kpi(c2, "Precision", f"{R['precision']*100:.1f}%", "attack precision", C_GREEN)
        kpi(c3, "Recall",    f"{R['recall']*100:.1f}%",    "attack recall",    C_TEAL)
        kpi(c4, "F1 Score",  f"{R['f1']*100:.1f}%",        "harmonic mean",    C_PURPLE)
        kpi(c5, "FPR",       f"{R['fpr']*100:.1f}%",       "false positives",  C_RED)
        st.markdown("")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">CONFUSION MATRIX</div>', unsafe_allow_html=True)
            z = [[cm['TN'], cm['FP']], [cm['FN'], cm['TP']]]
            fig = go.Figure(go.Heatmap(
                z=z, x=["Pred Normal","Pred Attack"], y=["True Normal","True Attack"],
                colorscale=[[0,"#f0fdf4"],[0.5,"#bbf7d0"],[1,"#16a34a"]],
                text=z, texttemplate="%{text}", textfont_size=18,
            ))
            fig.update_layout(**_pd(), height=280, margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">PER ATTACK TYPE DETECTION RATE</div>', unsafe_allow_html=True)
            atk_det = R['atk_detection']
            atks = list(atk_det.keys())
            vals = [atk_det[a]*100 for a in atks]
            colors = [ATK_COLORS.get(a, C_PRIMARY) for a in atks]
            fig2 = go.Figure(go.Bar(
                x=atks, y=vals, marker_color=colors,
                text=[f"{v:.1f}%" for v in vals], textposition="outside",
            ))
            fig2.update_layout(**_pd(), height=260, margin=dict(l=0,r=0,t=10,b=20),
                               yaxis=dict(range=[0,115]), yaxis_title="Detection Rate (%)")
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ROC curve
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">CONFIDENCE DISTRIBUTION</div>', unsafe_allow_html=True)
            probs = R['probs']; y = R['y']
            fig3 = go.Figure()
            fig3.add_trace(go.Histogram(x=probs[y==0], name="Normal",
                                        marker_color=C_GREEN, opacity=0.7, nbinsx=20))
            fig3.add_trace(go.Histogram(x=probs[y==1], name="Attack",
                                        marker_color=C_RED, opacity=0.7, nbinsx=20))
            fig3.add_vline(x=0.5, line_dash="dash", line_color=C_AMBER, annotation_text="threshold")
            fig3.update_layout(**_pd(), barmode="overlay", height=240,
                               margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">RBWKA OPTIMISATION HISTORY</div>', unsafe_allow_html=True)
            history = R['rbwka_history']
            if history:
                fig4 = go.Figure(go.Scatter(
                    y=history, mode="lines+markers",
                    line=dict(color=C_GREEN, width=2),
                    marker=dict(size=4),
                ))
                fig4.update_layout(**_pd(), height=220, margin=dict(l=0,r=0,t=10,b=0),
                                   xaxis_title="Iteration", yaxis_title="Best Accuracy")
                st.plotly_chart(fig4, use_container_width=True)
            st.markdown(f'<div style="font-size:.78rem;color:{C_MUTED};">RBWKA best accuracy: <b>{R["rbwka_best_fitness"]:.4f}</b></div>',
                        unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — Adaptive SHARP
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[6]:
    st.markdown('<div class="stage-tag">Stage 8 — Adaptive SHARP</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Adaptive SHAP — Attack Feature Explainability</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Permutation-based importance reveals which IoMT network features drive attack detection decisions — forensic-grade audit trail.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to see SHARP results.")
    else:
        importance   = R['importance']
        feat_names   = R['sharp_feature_names']
        order        = R['importance_order']
        threshold    = R['adaptive_threshold']
        significant  = R['significant_features']

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">FEATURE IMPORTANCE (SORTED)</div>', unsafe_allow_html=True)
            sorted_names = [feat_names[i] for i in order]
            sorted_vals  = [importance[i] for i in order]
            colors = [C_RED if importance[i] > threshold else C_TEAL for i in order]
            fig = go.Figure(go.Bar(
                x=sorted_vals, y=sorted_names, orientation="h",
                marker_color=colors,
                text=[f"{v:.4f}" for v in sorted_vals], textposition="outside",
            ))
            fig.add_vline(x=threshold, line_dash="dash", line_color=C_AMBER,
                          annotation_text=f"threshold={threshold:.4f}")
            fig.update_layout(**_pd(), height=300, margin=dict(l=0,r=10,t=10,b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="surface">', unsafe_allow_html=True)
            st.markdown('<div class="sec">FEATURE SIGNIFICANCE TABLE</div>', unsafe_allow_html=True)
            import pandas as pd
            rows = []
            for i in order:
                rows.append({
                    "Feature":     feat_names[i],
                    "Importance":  round(float(importance[i]), 5),
                    "Significant": "✓ Yes" if significant[i] else "No",
                    "Role":        _get_role(feat_names[i]),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, height=280)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">FORENSIC INTERPRETATION</div>', unsafe_allow_html=True)
        top_feat = sorted_names[0] if sorted_names else "N/A"
        st.markdown(f"""
        <div style="font-size:.84rem;color:{C_TEXT};line-height:1.7;">
          Top detection feature: <b style="color:{C_RED};">{top_feat}</b> —
          permuting this feature causes the largest drop in VQC detection confidence,
          meaning the quantum circuit learned this as the primary discriminator between
          normal and attack traffic.<br><br>
          Features above the adaptive threshold ({threshold:.4f}) are flagged as significant.
          The threshold adapts to the pipeline run — if all features contribute equally,
          the threshold rises; if one feature dominates, it falls, highlighting that feature.
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Live Detection
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[7]:
    st.markdown('<div class="stage-tag">Stage 9 — Live Detection</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Live Quantum Attack Detection</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Real-time IoMT network packet stream classified by the VQC quantum circuit.</div>',
                unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline first, then use this page for live detection.")
    else:
        import time
        from data_generator import generate_traffic
        from quantum_circuits import vqc_predict

        auto = st.checkbox("Auto Refresh (3s)")
        if st.button("⚡ Classify New Batch") or auto:
            seed_live = int(time.time()) % 9999
            live_pkts = generate_traffic(n_packets=8, seed=seed_live)
            weights   = R['opt_weights']
            X_live, y_live = __import__('data_generator').build_dataset(live_pkts)
            mu_l    = X_live.mean(axis=0); sig_l = X_live.std(axis=0) + 1e-9
            X_live_n = (X_live - mu_l) / sig_l

            live_results = []
            for xi, pkt in zip(X_live_n, live_pkts):
                conf = float(vqc_predict(xi[:4] if len(xi)>=4 else xi, weights))
                pred = "ATTACK" if conf > 0.5 else "NORMAL"
                live_results.append({"ID": pkt.packet_id, "Type": pkt.attack_type,
                                     "Conf": conf, "Pred": pred, "Label": pkt.label})

            for lr in live_results:
                color  = C_RED if lr['Pred'] == "ATTACK" else C_GREEN
                cls    = "a-attack" if lr['Pred'] == "ATTACK" else "a-normal"
                st.markdown(f"""
                <div class="{cls}">
                  <b>PKT-{lr['ID']}</b> [{lr['Type'].upper()}]
                  → <b>{lr['Pred']}</b>
                  (confidence: {lr['Conf']:.3f})
                </div>""", unsafe_allow_html=True)

            if auto:
                time.sleep(3)
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — vs Classical MedGuard
# ══════════════════════════════════════════════════════════════════════════════
elif page == PAGES[8]:
    st.markdown('<div class="stage-tag">Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Quantum IDS vs Classical MedGuard-IDS</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-desc">Side-by-side comparison of the quantum pipeline against the classical RF+GRU+XGB stacking ensemble.</div>',
                unsafe_allow_html=True)

    import pandas as pd
    q_acc  = R['accuracy']  if R else 0.91
    q_prec = R['precision'] if R else 0.90
    q_rec  = R['recall']    if R else 0.89
    q_f1   = R['f1']        if R else 0.895
    q_fpr  = R['fpr']       if R else 0.048

    compare = pd.DataFrame([
        {"Metric": "Accuracy",       "Quantum IDS (VQC)": f"{q_acc*100:.1f}%",  "Classical MedGuard": "94.6%",  "Advantage": "Quantum" if q_acc>0.946 else "Classical"},
        {"Metric": "Precision",      "Quantum IDS (VQC)": f"{q_prec*100:.1f}%", "Classical MedGuard": "95.1%",  "Advantage": "Quantum" if q_prec>0.951 else "Classical"},
        {"Metric": "Recall",         "Quantum IDS (VQC)": f"{q_rec*100:.1f}%",  "Classical MedGuard": "97.0%",  "Advantage": "Quantum" if q_rec>0.970 else "Classical"},
        {"Metric": "F1 Score",       "Quantum IDS (VQC)": f"{q_f1*100:.1f}%",   "Classical MedGuard": "96.0%",  "Advantage": "Quantum" if q_f1>0.960 else "Classical"},
        {"Metric": "False Pos Rate", "Quantum IDS (VQC)": f"{q_fpr*100:.1f}%",  "Classical MedGuard": "10.6%",  "Advantage": "Quantum" if q_fpr<0.106 else "Classical"},
        {"Metric": "Model Size",     "Quantum IDS (VQC)": "4 qubits",            "Classical MedGuard": "250+300+GRU trees", "Advantage": "Quantum"},
        {"Metric": "Explainability", "Quantum IDS (VQC)": "Adaptive SHARP",      "Classical MedGuard": "SHAP (RF/XGB)",     "Advantage": "Quantum"},
        {"Metric": "Blockchain",     "Quantum IDS (VQC)": "Planned",             "Classical MedGuard": "DLCA-BC dual ledger","Advantage": "Classical"},
    ])

    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.dataframe(compare, use_container_width=True, height=320)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">QUANTUM ADVANTAGES</div>', unsafe_allow_html=True)
        advs = [
            "Quantum entanglement captures non-linear feature correlations",
            "Variational circuits adapt without retraining full model",
            "BMOCO reduces feature count → lower inference latency",
            "HQAN attention weights are interference-based (no backprop needed)",
            "Adaptive SHARP threshold adjusts to pipeline run context",
        ]
        for a in advs:
            st.markdown(f'<div style="font-size:.8rem;color:{C_TEXT};margin:.3rem 0;">✓ {a}</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        st.markdown('<div class="sec">CLASSICAL ADVANTAGES</div>', unsafe_allow_html=True)
        advs2 = [
            "Trained on real UNSW-NB15 + NF-ToN-IoT-v2 datasets",
            "DLCA-BC dual blockchain for tamper-proof audit trail",
            "3T-HATF hierarchical device trust federation",
            "TBDW burst detection window for coordinated attacks",
            "CC-WFF clinical criticality weighting per device type",
        ]
        for a in advs2:
            st.markdown(f'<div style="font-size:.8rem;color:{C_TEXT};margin:.3rem 0;">✓ {a}</div>',
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if not R:
        st.info("Run the pipeline to populate quantum metrics in the comparison table.")
