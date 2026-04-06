import streamlit as st
from data import load_all_data
from logic import run_engine

st.set_page_config(
    page_title="Ginesys One · Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.main .block-container { background: #F4F6FB; padding: 1.5rem 2rem 3rem 2rem !important; max-width: 1400px; }
[data-testid="stAppViewContainer"] { background: #F4F6FB; }
[data-testid="stSidebar"] { background: #1B2B5E !important; border-right: none; min-width: 240px !important; }
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stRadio label { color: #CBD5E1 !important; font-size: 13px !important; padding: 7px 12px !important; border-radius: 6px; cursor: pointer; }
[data-testid="stSidebar"] .stRadio label:hover { color: #fff !important; background: rgba(244,121,32,0.15) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }
[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; opacity: 1 !important; background: #1B2B5E !important; border-radius: 0 8px 8px 0 !important; top: 14px !important; z-index: 9999 !important; border: 1px solid rgba(244,121,32,0.4) !important; border-left: none !important; }
[data-testid="collapsedControl"] svg { fill: #F47920 !important; }
#MainMenu, footer, header { visibility: hidden; }
.kpi-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 24px; position: relative; overflow: hidden; box-shadow: 0 1px 4px rgba(27,43,94,0.06); }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
.kpi-card.red::before { background: #DC2626; } .kpi-card.amber::before { background: #F47920; }
.kpi-card.green::before { background: #16A34A; } .kpi-card.blue::before { background: #2563EB; } .kpi-card.navy::before { background: #1B2B5E; }
.kpi-label { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #64748B; margin-bottom: 8px; }
.kpi-value { font-size: 32px; font-weight: 700; color: #1B2B5E; line-height: 1; font-family: 'DM Mono', monospace; }
.kpi-sub { font-size: 12px; color: #94A3B8; margin-top: 6px; }
.action-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(27,43,94,0.05); }
.action-card.critical { border-left: 3px solid #DC2626; } .action-card.warning { border-left: 3px solid #F47920; } .action-card.healthy { border-left: 3px solid #16A34A; }
.badge { display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; letter-spacing: 0.05em; text-transform: uppercase; }
.badge-red { background: rgba(220,38,38,0.10); color: #DC2626; border: 1px solid rgba(220,38,38,0.25); }
.badge-amber { background: rgba(244,121,32,0.10); color: #C2540A; border: 1px solid rgba(244,121,32,0.25); }
.badge-green { background: rgba(22,163,74,0.10); color: #15803D; border: 1px solid rgba(22,163,74,0.25); }
.badge-blue { background: rgba(37,99,235,0.10); color: #1D4ED8; border: 1px solid rgba(37,99,235,0.25); }
.badge-grey { background: rgba(100,116,139,0.10); color: #475569; border: 1px solid rgba(100,116,139,0.25); }
.badge-navy { background: rgba(27,43,94,0.10); color: #1B2B5E; border: 1px solid rgba(27,43,94,0.25); }
.alert-banner { background: #FFF7ED; border: 1px solid #FDBA74; border-radius: 10px; padding: 14px 20px; margin-bottom: 16px; color: #9A3412; font-size: 13px; font-weight: 500; }
.alert-banner.red { background: #FEF2F2; border-color: #FCA5A5; color: #991B1B; }
.section-header { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #64748B; margin: 24px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #F47920; }
.page-title { font-size: 22px; font-weight: 700; color: #1B2B5E; margin-bottom: 4px; }
.page-subtitle { font-size: 13px; color: #64748B; margin-bottom: 24px; }
.stButton > button { border-radius: 6px !important; font-size: 12px !important; font-weight: 600 !important; padding: 4px 14px !important; height: 32px !important; color: #1B2B5E !important; border-color: #CBD5E1 !important; background: #FFFFFF !important; }
.stButton > button[kind="primary"] { background: #1B2B5E !important; border-color: #1B2B5E !important; color: #FFFFFF !important; }
.stButton > button[kind="primary"]:hover { background: #F47920 !important; border-color: #F47920 !important; }
[data-testid="stExpander"] { border: 1px solid #E2E8F0 !important; border-radius: 8px !important; background: #FFFFFF !important; }
[data-testid="stDataFrame"] { border: 1px solid #E2E8F0 !important; border-radius: 8px !important; background: #FFFFFF !important; }
.js-plotly-plot .plotly, .plot-container { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_data():
    raw = load_all_data()
    return run_engine(raw)

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
if "rules" not in st.session_state:
    st.session_state.rules = {
        "doh_stockout_critical": 3, "doh_stockout_warning": 7, "doh_overstock": 30,
        "dead_stock_days": 21, "velocity_spike_mult": 2.0, "returns_spike_mult": 2.5,
        "transfer_min_qty": 10, "logistics_express": 45, "logistics_surface": 18,
        "markdown_pct_overstock": 30, "markdown_pct_dead": 40,
        "priority_revenue_w": 0.40, "priority_urgency_w": 0.40, "priority_tier_w": 0.20,
        "auto_approve_low_risk": False,
    }

data    = st.session_state.data
summary = data["summary"]

with st.sidebar:
    st.markdown("""
    <div style="padding:12px 0 20px 0;border-bottom:1px solid rgba(255,255,255,0.12);margin-bottom:16px;">
        <div style="font-size:20px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;">Ginesys <span style="color:#F47920;">One</span></div>
        <div style="font-size:10px;color:#94A3B8;letter-spacing:0.08em;text-transform:uppercase;margin-top:3px;">Inventory Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("nav", [
        "🌅  Morning Briefing", "⚡  Action Feed", "🏪  Store Analytics",
        "🔍  SKU Drill Down", "🚨  Signals & Alerts", "⚙️  Rules Engine", "🤖  AI Copilot",
    ], label_visibility="collapsed")

    st.markdown("---")
    health_color = "#DC2626" if summary["network_health_pct"] < 60 else ("#F47920" if summary["network_health_pct"] < 80 else "#16A34A")
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">Network Health</div>
        <div style="font-size:30px;font-weight:700;color:{health_color};font-family:'DM Mono',monospace;">{summary['network_health_pct']}%</div>
    </div>
    <div style="display:flex;flex-direction:column;gap:5px;font-size:12px;">
        <div style="color:#FCA5A5;">🔴 {summary['stockout_critical_count']} critical stockouts</div>
        <div style="color:#FDBA74;">🟡 {summary['stockout_warning_count']} at warning</div>
        <div style="color:#94A3B8;">📋 {summary['pending_actions']} pending actions</div>
    </div>
    """, unsafe_allow_html=True)

    approved_count = len(st.session_state.approved_actions)
    if approved_count > 0:
        st.markdown(f"""
        <div style="background:rgba(22,163,74,0.15);border:1px solid rgba(22,163,74,0.3);border-radius:8px;padding:10px 14px;margin-top:12px;font-size:12px;color:#86EFAC;">
            ✅ {approved_count} action{"s" if approved_count > 1 else ""} approved today
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f'<div style="margin-top:16px;font-size:11px;color:#475569;">Data as of {data["today"]}</div>', unsafe_allow_html=True)

if "Morning Briefing" in page:
    from pages.morning_briefing import render; render(data)
elif "Action Feed" in page:
    from pages.action_feed import render; render(data)
elif "Store Analytics" in page:
    from pages.store_analytics import render; render(data)
elif "SKU Drill Down" in page:
    from pages.sku_detail import render; render(data)
elif "Signals" in page:
    from pages.signals import render; render(data)
elif "Rules Engine" in page:
    from pages.rules_engine import render; render(data)
elif "AI Copilot" in page:
    from pages.ai_copilot import render; render(data)
