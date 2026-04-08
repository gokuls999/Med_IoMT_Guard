"""Hospital Management System – CSS Theme (Hospital Green + Blue + Red)"""

# ─────────────────────────────────────────────────────────────────
#  Palette
#  Green  (primary / positive / stable): #15803d · #16a34a · #dcfce7
#  Blue   (info / secondary):            #1d4ed8 · #2563eb · #eff6ff
#  Red    (critical / danger / alert):   #b91c1c · #dc2626 · #fef2f2
# ─────────────────────────────────────────────────────────────────

CSS = """
<style>
/* ── Google Font ──────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background-color: #f1f5f9; }
.block-container { padding: 1.5rem 2rem 2rem 2rem !important; }

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0a2416 !important;       /* deep forest green */
    border-right: 2px solid #143521 !important;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #cbd5e1 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f0fdf4 !important; }

/* Radio nav pills */
[data-testid="stSidebar"] .stRadio > div { gap: 2px; }
[data-testid="stSidebar"] .stRadio label {
    padding: 9px 14px !important;
    border-radius: 8px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    color: #c6e6d0 !important;
    display: block !important;
    transition: background 0.15s, color 0.15s !important;
    border: none !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #1a3d24 !important;
    color: #f0fdf4 !important;
}
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] span:first-child {
    display: none !important;
}

/* ── Page header ──────────────────────────────────────────── */
.page-header {
    background: linear-gradient(135deg, #15803d 0%, #1d4ed8 100%);
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
    color: white;
    box-shadow: 0 4px 12px rgba(21,128,61,0.25);
}
.page-header h1 { color: white !important; font-size: 1.6rem; font-weight: 700; margin: 0; }
.page-header p  { color: rgba(255,255,255,0.82) !important; margin: 4px 0 0 0; font-size: 0.9rem; }

/* ── KPI cards ────────────────────────────────────────────── */
.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid #e2e8f0;
    border-top: 3px solid #16a34a;       /* green top accent */
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    text-align: center;
}
.kpi-number {
    font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.1;
}
.kpi-label {
    font-size: 0.8rem; color: #475569; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;
}
.kpi-blue   .kpi-number { color: #1d4ed8; }
.kpi-blue   { border-top-color: #1d4ed8 !important; }
.kpi-green  .kpi-number { color: #15803d; }
.kpi-green  { border-top-color: #15803d !important; }
.kpi-red    .kpi-number { color: #b91c1c; }
.kpi-red    { border-top-color: #b91c1c !important; }
.kpi-orange .kpi-number { color: #c2410c; }
.kpi-orange { border-top-color: #c2410c !important; }
.kpi-teal   .kpi-number { color: #0e7490; }
.kpi-teal   { border-top-color: #0e7490 !important; }

/* ── Status badges ────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
}
.badge-critical   { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-high       { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
.badge-medium     { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.badge-low        { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.badge-active     { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-stable     { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.badge-admitted   { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-discharged { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }
.badge-completed  { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.badge-pending    { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.badge-online     { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.badge-offline    { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-maintenance{ background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }

/* ── Section cards ────────────────────────────────────────── */
.section-card {
    background: white; border-radius: 10px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    padding: 20px;
    margin-bottom: 16px;
}
.section-title {
    font-size: 1rem; font-weight: 600; color: #0f172a; margin-bottom: 12px;
    border-bottom: 2px solid #16a34a;   /* green accent underline */
    padding-bottom: 8px;
}

/* ── Alert banners ────────────────────────────────────────── */
.alert-critical {
    background: #fef2f2; border-left: 4px solid #b91c1c;
    padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 4px 0;
    font-size: 0.85rem; color: #7f1d1d;
}
.alert-warning {
    background: #fffbeb; border-left: 4px solid #d97706;
    padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 4px 0;
    font-size: 0.85rem; color: #78350f;
}
.alert-info {
    background: #f0fdf4; border-left: 4px solid #16a34a;
    padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 4px 0;
    font-size: 0.85rem; color: #14532d;
}

/* ── Streamlit dataframe ──────────────────────────────────── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── Bed grid ─────────────────────────────────────────────── */
.bed-occupied    { background:#fee2e2; border:2px solid #b91c1c; border-radius:8px; padding:8px; text-align:center; font-size:0.75rem; font-weight:600; color:#7f1d1d; }
.bed-available   { background:#dcfce7; border:2px solid #15803d; border-radius:8px; padding:8px; text-align:center; font-size:0.75rem; font-weight:600; color:#14532d; }
.bed-maintenance { background:#fef9c3; border:2px solid #ca8a04; border-radius:8px; padding:8px; text-align:center; font-size:0.75rem; font-weight:600; color:#713f12; }

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
.stButton > button[kind="primary"] {
    background-color: #16a34a !important;   /* hospital green */
    border-color: #16a34a !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #15803d !important;
    border-color: #15803d !important;
}

/* ── Form inputs ──────────────────────────────────────────── */
.stTextInput input, .stSelectbox select, .stNumberInput input {
    border-radius: 8px !important;
    border-color: #cbd5e1 !important;
}
.stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {
    border-color: #16a34a !important;
    box-shadow: 0 0 0 2px rgba(22,163,74,0.15) !important;
}
.stExpander {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── Streamlit metric ─────────────────────────────────────── */
div[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    color: #334155 !important;
    font-weight: 600 !important;
}
div[data-testid="stMetricDelta"] {
    font-weight: 600 !important;
}

/* ── Streamlit tabs ──────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] button {
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    color: #334155 !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #15803d !important;
    font-weight: 700 !important;
}

/* ── Streamlit labels (selectbox, text input, slider, etc.) ─ */
.stSelectbox label, .stTextInput label, .stNumberInput label,
.stSlider label, .stDateInput label, .stTextArea label,
.stMultiSelect label, .stRadio > label, .stCheckbox label {
    color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}

/* ── General body text readability ───────────────────────── */
.stMarkdown p, .stMarkdown li {
    color: #1e293b !important;
}
.stMarkdown h4, .stMarkdown h3, .stMarkdown h2 {
    color: #0f172a !important;
    font-weight: 700 !important;
}

/* ── Sidebar divider / status ─────────────────────────────── */
.sidebar-divider { border-top: 1px solid #143521; margin: 12px 0; }

.sys-status-dot {
    display: inline-block; width: 8px; height: 8px;
    background: #22c55e; border-radius: 50%;
    margin-right: 6px; animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}
</style>
"""


def inject(extra: str = "") -> None:
    """Inject CSS into Streamlit page."""
    import streamlit as st
    st.markdown(CSS + extra, unsafe_allow_html=True)


def kpi_card(value, label: str, color: str = "green") -> str:
    return (
        f'<div class="kpi-card kpi-{color}">'
        f'<div class="kpi-number">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'</div>'
    )


def badge(text: str, level: str = "active") -> str:
    lvl = level.lower().replace(" ", "-").replace("_", "-")
    return f'<span class="badge badge-{lvl}">{text}</span>'


def page_header(title: str, subtitle: str = "") -> str:
    return (
        f'<div class="page-header">'
        f'<h1>{title}</h1>'
        + (f'<p>{subtitle}</p>' if subtitle else "")
        + "</div>"
    )
