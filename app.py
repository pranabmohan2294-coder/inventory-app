import streamlit as st
import pandas as pd
from data import generate_data
from logic import compute_signals, classify_network_imbalance, generate_actions, get_risk_summary

st.set_page_config(
    page_title="Ginesys One | Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Ginesys brand CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar always visible, never disappears */
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] {
    min-width: 240px !important;
    max-width: 240px !important;
    background: #0F2040 !important;
}
section[data-testid="stSidebar"] * { color: #E8EDF5 !important; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(242,101,34,0.15) !important;
}

/* Main background */
.stApp { background: #0A1628 !important; }
.main .block-container { padding-top: 1.5rem !important; }

/* Metric cards */
.metric-card {
    background: #0F2040;
    border: 1px solid #1A3060;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
}
.metric-card .label { font-size: 12px; color: #8A9BC0; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-card .value { font-size: 28px; font-weight: 700; color: #E8EDF5; margin: 4px 0; }
.metric-card .delta { font-size: 12px; }
.metric-card.danger .value { color: #FF4444; }
.metric-card.warning .value { color: #F26522; }
.metric-card.success .value { color: #22C55E; }
.metric-card.info .value { color: #4488FF; }

/* Action cards */
.action-card {
    background: #0F2040;
    border: 1px solid #1A3060;
    border-left: 4px solid #F26522;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.action-card.approved { border-left-color: #22C55E; opacity: 0.7; }
.action-card.rejected { border-left-color: #FF4444; opacity: 0.5; }

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin: 2px;
}
.badge-high { background: #1A3D1A; color: #22C55E; }
.badge-medium { background: #3D2A00; color: #FFD700; }
.badge-low { background: #3D1A1A; color: #FF6666; }
.badge-transfer { background: #0D2B4A; color: #4488FF; }
.badge-markdown { background: #2D1A00; color: #F26522; }
.badge-replenish { background: #1A2D1A; color: #66CC66; }
.badge-wait { background: #2D2D2D; color: #AAAAAA; }

/* Ginesys header */
.ginesys-header {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 0 20px 0;
    border-bottom: 1px solid #1A3060;
    margin-bottom: 20px;
}
.ginesys-header h1 { margin: 0; font-size: 22px; color: #E8EDF5; }
.ginesys-header span { font-size: 12px; color: #F26522; font-weight: 600; }

/* Alert banners */
.alert-banner {
    background: rgba(242,101,34,0.1);
    border: 1px solid rgba(242,101,34,0.4);
    border-radius: 8px;
    padding: 10px 16px;
    margin: 8px 0;
    color: #F26522;
    font-size: 13px;
}

/* Tables */
.stDataFrame { background: #0F2040 !important; }

/* Store health bars */
.store-health-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 0; border-bottom: 1px solid #1A3060;
}

/* Sidebar logo area */
.sidebar-logo {
    padding: 16px;
    border-bottom: 1px solid #1A3060;
    margin-bottom: 12px;
}
.sidebar-logo h2 { color: #F26522 !important; margin: 0; font-size: 18px; }
.sidebar-logo p { color: #8A9BC0 !important; margin: 0; font-size: 11px; }

/* Override streamlit buttons */
.stButton button {
    border-radius: 6px !important;
    font-size: 12px !important;
    padding: 4px 12px !important;
}
div[data-testid="stHorizontalBlock"] { gap: 8px; }

/* Rules page */
.rule-card {
    background: #0F2040;
    border: 1px solid #1A3060;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}
.rule-card h4 { color: #F26522; margin: 0 0 8px 0; }
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    inv, sales, transit, returns, stores, skus = generate_data()
    signals = compute_signals(inv, sales)
    signals = classify_network_imbalance(signals)
    actions = generate_actions(signals, inv, transit)
    summary = get_risk_summary(signals, actions, returns, transit)
    return inv, sales, transit, returns, signals, actions, summary, stores, skus

if "action_states" not in st.session_state:
    st.session_state.action_states = {}
if "rules" not in st.session_state:
    st.session_state.rules = [
        {"id": 1, "name": "Auto-flag Stockout", "condition": "DOH < 3 AND demand = high",
         "action": "Flag for Transfer/Replenish", "active": True, "category": "Stockout"},
        {"id": 2, "name": "Overstock Markdown", "condition": "DOH > 30 AND velocity < 0.5",
         "action": "Recommend 20% Markdown", "active": True, "category": "Overstock"},
        {"id": 3, "name": "Dead Stock Aggressive MD", "condition": "No sale for 14 days",
         "action": "Recommend 30% Markdown", "active": True, "category": "Dead Stock"},
        {"id": 4, "name": "Size Gap Alert", "condition": "Pivotal size DOH < 3 while XL DOH > 20",
         "action": "Flag Size-Level Transfer", "active": True, "category": "Size Gap"},
        {"id": 5, "name": "Network Imbalance", "condition": "DOH std > 10 across stores",
         "action": "Recommend Store-to-Store Transfer", "active": True, "category": "Transfer"},
        {"id": 6, "name": "In-Transit Wait", "condition": "Stockout + confirmed shipment arriving ≤3d",
         "action": "WAIT — no duplicate action", "active": True, "category": "Stockout"},
        {"id": 7, "name": "Transfer Cost Guard", "condition": "Transfer cost > 60% of prevented loss",
         "action": "Suggest Markdown instead", "active": False, "category": "Markdown"},
    ]
if "next_rule_id" not in st.session_state:
    st.session_state.next_rule_id = 8

inv, sales, transit, returns, signals, actions, summary, stores, skus = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h2>🔷 Ginesys One</h2>
        <p>Inventory Intelligence · Beta</p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        options=[
            "🌅 Morning Briefing",
            "⚡ Action Feed",
            "📊 Store Analytics",
            "🔍 SKU Drill-Down",
            "📡 Signals & Alerts",
            "⚙️ Rules Engine",
            "🤖 AI Copilot",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='font-size:11px; color:#8A9BC0; padding: 0 4px;'>
    <b style='color:#F26522;'>{summary['stockout_count']}</b> SKUs at risk<br>
    <b style='color:#F26522;'>₹{summary['overstock_value']:,}</b> idle stock<br>
    <b style='color:#22C55E;'>{summary['health_score']}%</b> network health<br>
    <b style='color:#FFD700;'>{summary['pending_actions']}</b> pending actions
    </div>
    """, unsafe_allow_html=True)

# ── Page routing ───────────────────────────────────────────────────────────────
if page == "🌅 Morning Briefing":
    from pages.morning_briefing import show
    show(inv, sales, transit, returns, signals, actions, summary, stores)

elif page == "⚡ Action Feed":
    from pages.action_feed import show
    show(signals, actions, inv)

elif page == "📊 Store Analytics":
    from pages.store_analytics import show
    show(inv, sales, signals, stores)

elif page == "🔍 SKU Drill-Down":
    from pages.sku_detail import show
    show(inv, sales, signals, actions, skus)

elif page == "📡 Signals & Alerts":
    from pages.signals import show
    show(signals, returns, transit)

elif page == "⚙️ Rules Engine":
    from pages.rules_engine import show
    show()

elif page == "🤖 AI Copilot":
    from pages.ai_copilot import show
    show(inv, signals, actions, summary, transit, returns)
