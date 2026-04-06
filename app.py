import streamlit as st
from data import load_all_data
from logic import run_engine

st.set_page_config(
    page_title="Ginesys One · Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f1117 !important;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * {
    color: #c9d1d9 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #8b949e !important;
    font-size: 13px !important;
    padding: 6px 10px !important;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    color: #fff !important;
    background: #1e2130 !important;
}

/* Main area */
.main .block-container {
    padding: 1.5rem 2rem 3rem 2rem !important;
    max-width: 1400px;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* KPI Cards */
.kpi-card {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.kpi-card.red::before   { background: #f85149; }
.kpi-card.amber::before { background: #e3b341; }
.kpi-card.green::before { background: #3fb950; }
.kpi-card.blue::before  { background: #58a6ff; }

.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #f0f6fc;
    line-height: 1;
    font-family: 'DM Mono', monospace;
}
.kpi-sub {
    font-size: 12px;
    color: #8b949e;
    margin-top: 6px;
}

/* Action cards */
.action-card {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color 0.15s;
}
.action-card:hover {
    border-color: #30363d;
}
.action-card.critical { border-left: 3px solid #f85149; }
.action-card.warning  { border-left: 3px solid #e3b341; }
.action-card.healthy  { border-left: 3px solid #3fb950; }

/* Badges */
.badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.badge-red    { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.badge-amber  { background: rgba(227,179,65,0.15); color: #e3b341; border: 1px solid rgba(227,179,65,0.3); }
.badge-green  { background: rgba(63,185,80,0.15);  color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.badge-blue   { background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.3); }
.badge-grey   { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid rgba(139,148,158,0.3); }

/* Alert banner */
.alert-banner {
    background: rgba(227,179,65,0.08);
    border: 1px solid rgba(227,179,65,0.3);
    border-radius: 10px;
    padding: 14px 20px;
    margin-bottom: 16px;
    color: #e3b341;
    font-size: 13px;
    font-weight: 500;
}
.alert-banner.red {
    background: rgba(248,81,73,0.08);
    border-color: rgba(248,81,73,0.3);
    color: #f85149;
}

/* Section headers */
.section-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8b949e;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e2130;
}

/* Page title */
.page-title {
    font-size: 22px;
    font-weight: 700;
    color: #f0f6fc;
    margin-bottom: 4px;
}
.page-subtitle {
    font-size: 13px;
    color: #8b949e;
    margin-bottom: 24px;
}

/* Streamlit button overrides */
.stButton > button {
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 4px 14px !important;
    height: 32px !important;
}
.stButton > button[kind="primary"] {
    background: #238636 !important;
    border-color: #238636 !important;
}

/* Plotly chart bg */
.js-plotly-plot .plotly, .plot-container {
    background: transparent !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 10px;
    padding: 16px !important;
}
</style>
""", unsafe_allow_html=True)


# ── LOAD & CACHE DATA ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data():
    raw = load_all_data()
    return run_engine(raw)


# ── SESSION STATE INIT ────────────────────────────────────────────────────────
if "data" not in st.session_state:
    with st.spinner("Running inventory engine..."):
        st.session_state.data = get_data()

if "approved_actions" not in st.session_state:
    st.session_state.approved_actions = set()
if "rejected_actions" not in st.session_state:
    st.session_state.rejected_actions = set()
if "modified_actions" not in st.session_state:
    st.session_state.modified_actions = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "event_flags" not in st.session_state:
    st.session_state.event_flags = {}

data = st.session_state.data
summary = data["summary"]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 16px 0;">
        <div style="font-size:18px;font-weight:700;color:#f0f6fc;letter-spacing:-0.3px;">Ginesys One</div>
        <div style="font-size:11px;color:#8b949e;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;">Inventory Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["🌅  Morning Briefing", "⚡  Action Feed", "🔍  SKU Drill Down", "🚨  Signals & Alerts", "🤖  AI Copilot"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    health_color = "#f85149" if summary["network_health_pct"] < 60 else ("#e3b341" if summary["network_health_pct"] < 80 else "#3fb950")
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Network Health</div>
        <div style="font-size:28px;font-weight:700;color:{health_color};font-family:'DM Mono',monospace;">{summary['network_health_pct']}%</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:4px;font-size:12px;">
        <div style="color:#f85149;">🔴 {summary['stockout_critical_count']} critical stockouts</div>
        <div style="color:#e3b341;">🟡 {summary['stockout_warning_count']} at warning</div>
        <div style="color:#8b949e;">📋 {summary['pending_actions']} pending actions</div>
    </div>
    """, unsafe_allow_html=True)

    approved_count = len(st.session_state.approved_actions)
    if approved_count > 0:
        st.markdown(f"""
        <div style="background:rgba(63,185,80,0.1);border:1px solid rgba(63,185,80,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;font-size:12px;color:#3fb950;">
            ✅ {approved_count} action{"s" if approved_count > 1 else ""} approved today
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:16px;font-size:11px;color:#484f58;">Data as of {data['today']}</div>
    """, unsafe_allow_html=True)


# ── PAGE ROUTING ──────────────────────────────────────────────────────────────
if "Morning Briefing" in page:
    from pages.morning_briefing import render
    render(data)
elif "Action Feed" in page:
    from pages.action_feed import render
    render(data)
elif "SKU Drill Down" in page:
    from pages.sku_detail import render
    render(data)
elif "Signals" in page:
    from pages.signals import render
    render(data)
elif "AI Copilot" in page:
    from pages.ai_copilot import render
    render(data)
