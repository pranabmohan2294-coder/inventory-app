#!/bin/bash
set -e
echo "Writing files..."

# ── config.toml ──────────────────────────────────────────────────────────────
mkdir -p .streamlit
cat > .streamlit/config.toml << 'EOF'
[theme]
base = "light"
primaryColor = "#F47920"
backgroundColor = "#F4F6FB"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#1B2B5E"
font = "sans serif"

[server]
headless = true
enableCORS = false
EOF
echo "✅ .streamlit/config.toml"

# ── app.py ─────────────────────────────────────────────────────────────────
cat > app.py << 'EOF'
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
EOF
echo "✅ app.py"

# ── morning_briefing.py ────────────────────────────────────────────────────
cat > pages/morning_briefing.py << 'EOF'
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def show(inv, sales, transit, returns, signals, actions, summary, stores):
    from datetime import date
    today_str = date.today().strftime("%A, %d %B %Y")

    st.markdown(f"""
    <div class="ginesys-header">
        <div>
            <h1>📦 Morning Briefing</h1>
            <span>{today_str} · Network: 6 Stores · {len(inv['sku_id'].unique())} SKUs</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Anomaly Banner ──────────────────────────────────────────────────────────
    anomalies = []
    if summary["velocity_anomalies"] > 0:
        anomalies.append(f"🔥 Demand spike on {summary['velocity_anomalies']} SKUs — sale event or trend shift?")
    if summary["return_spikes"] > 0:
        anomalies.append(f"⚠️ Returns spike detected at {summary['return_spikes']} locations — QC check needed")
    if summary["data_gaps"] > 0:
        anomalies.append(f"🔌 {summary['data_gaps']} in-transit shipments have unknown status — decisions may lag")

    if anomalies:
        for a in anomalies:
            st.markdown(f'<div class="alert-banner">{a}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI Cards ───────────────────────────────────────────────────────────────
    cols = st.columns(4)
    kpis = [
        ("SKUs at Stockout Risk", summary["stockout_count"], "danger",
         f"Highest urgency: {summary['top_risk_sku'][:25]}"),
        ("Idle Overstock Value", f"₹{summary['overstock_value']:,}", "warning",
         "Capital locked in slow-moving stock"),
        ("Network Health Score", f"{summary['health_score']}%", "success" if summary['health_score'] > 70 else "warning",
         "% SKUs in healthy DOH range"),
        ("Pending Actions", summary["pending_actions"], "info",
         "Actions awaiting your approval today"),
    ]
    for col, (label, val, cls, sub) in zip(cols, kpis):
        with col:
            st.markdown(f"""
            <div class="metric-card {cls}">
                <div class="label">{label}</div>
                <div class="value">{val}</div>
                <div class="delta" style="color:#8A9BC0">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Top 5 Priority Actions + Store Health ───────────────────────────────────
    col_l, col_r = st.columns([1.1, 0.9])

    with col_l:
        st.markdown("#### ⚡ Top 5 Actions Today")
        st.markdown("<small style='color:#8A9BC0'>Approve directly here or go to Action Feed for full detail</small>", unsafe_allow_html=True)
        top5 = [a for a in actions if a.status == "Pending"][:5]

        if not top5:
            st.success("✅ All critical actions resolved. Great work!")
        else:
            for action in top5:
                state = st.session_state.action_states.get(action.action_id, "Pending")
                risk_colors = {
                    "stockout": "#FF4444", "size_gap": "#FFD700",
                    "imbalance": "#4488FF", "overstock": "#FF8C00",
                    "dead_stock": "#888888",
                }
                risk_color = risk_colors.get(action.risk_type, "#F26522")
                badge_map = {
                    "TRANSFER": "badge-transfer", "MARKDOWN": "badge-markdown",
                    "REPLENISH": "badge-replenish", "WAIT": "badge-wait"
                }
                conf_map = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}

                border = {"Approved": "#22C55E", "Rejected": "#FF4444"}.get(state, risk_color)
                opacity = "opacity:0.6;" if state != "Pending" else ""

                st.markdown(f"""
                <div class="action-card" style="border-left-color:{border}; {opacity}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <b style="color:#E8EDF5">{action.sku_name}</b> &nbsp;
                            <span class="badge {badge_map.get(action.action_type,'badge-transfer')}">{action.action_type}</span>
                            <span class="badge {conf_map.get(action.confidence,'badge-medium')}">{action.confidence}</span><br>
                            <small style="color:#8A9BC0">Size: {action.size} · {action.from_location} → {action.to_location}</small><br>
                            <small style="color:#8A9BC0">Qty: {action.quantity} · ₹{int(action.cost_inr):,} cost · Saves ₹{int(action.prevented_loss_inr):,}</small>
                        </div>
                        <div style="text-align:right; min-width:80px;">
                            <div style="font-size:11px; color:#8A9BC0">Priority</div>
                            <div style="font-size:18px; font-weight:700; color:{risk_color}">{action.priority_score:.1f}</div>
                        </div>
                    </div>
                    <div style="font-size:12px; color:#8A9BC0; margin-top:6px;">💡 {action.notes}</div>
                </div>
                """, unsafe_allow_html=True)

                if state == "Pending":
                    b1, b2, b3 = st.columns([1, 1, 3])
                    with b1:
                        if st.button("✅ Approve", key=f"mb_app_{action.action_id}"):
                            st.session_state.action_states[action.action_id] = "Approved"
                            st.rerun()
                    with b2:
                        if st.button("❌ Reject", key=f"mb_rej_{action.action_id}"):
                            st.session_state.action_states[action.action_id] = "Rejected"
                            st.rerun()
                else:
                    st.markdown(f"<div style='color:#8A9BC0; font-size:12px; padding: 2px 0 8px;'>Status: <b>{state}</b></div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("#### 🏪 Store Health At a Glance")
        store_signals = signals[signals["store_id"] != "WH"].copy()
        store_health = []
        for store_id in store_signals["store_id"].unique():
            s_df = store_signals[store_signals["store_id"] == store_id]
            total = len(s_df)
            stockouts = len(s_df[s_df["risk_type"] == "stockout"])
            overstocked = len(s_df[s_df["risk_type"].isin(["overstock", "dead_stock"])])
            healthy = total - stockouts - overstocked
            health_pct = round(healthy / total * 100) if total > 0 else 0
            store_name = s_df.iloc[0]["store_name"] if len(s_df) > 0 else store_id
            tier = s_df.iloc[0]["store_tier"] if len(s_df) > 0 else "B"
            store_health.append({
                "store_id": store_id, "store_name": store_name, "tier": tier,
                "health_pct": health_pct, "stockouts": stockouts,
                "overstocked": overstocked, "total_skus": total,
            })

        sh_df = pd.DataFrame(store_health).sort_values("health_pct")

        fig = go.Figure()
        colors = ["#FF4444" if h < 50 else "#F26522" if h < 75 else "#22C55E"
                  for h in sh_df["health_pct"]]
        fig.add_trace(go.Bar(
            x=sh_df["health_pct"], y=sh_df["store_name"],
            orientation="h", marker_color=colors,
            text=[f"{h}%" for h in sh_df["health_pct"]],
            textposition="outside",
            customdata=sh_df[["stockouts", "overstocked", "tier"]].values,
            hovertemplate="<b>%{y}</b><br>Health: %{x}%<br>Stockouts: %{customdata[0]}<br>Overstock: %{customdata[1]}<br>Tier: %{customdata[2]}<extra></extra>",
        ))
        fig.update_layout(
            plot_bgcolor="#0F2040", paper_bgcolor="#0F2040",
            font_color="#E8EDF5", margin=dict(l=0, r=40, t=10, b=10),
            xaxis=dict(range=[0, 115], showgrid=False, zeroline=False, color="#8A9BC0"),
            yaxis=dict(showgrid=False, color="#E8EDF5"),
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Wins panel
        approved_count = sum(1 for v in st.session_state.action_states.values() if v == "Approved")
        if approved_count > 0:
            st.markdown(f"""
            <div style="background:#0A2010; border:1px solid #22C55E33; border-radius:8px; padding:12px; margin-top:12px;">
                <div style="color:#22C55E; font-weight:600; font-size:13px;">✅ Session Wins</div>
                <div style="color:#8A9BC0; font-size:12px; margin-top:4px;">
                {approved_count} action(s) approved this session
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── DOH Distribution ────────────────────────────────────────────────────────
    st.markdown("#### 📊 Network DOH Distribution")
    store_only = signals[signals["store_id"] != "WH"].copy()
    bins = pd.cut(store_only["doh"], bins=[0, 3, 7, 15, 30, 999],
                  labels=["Critical (0-3d)", "Low (3-7d)", "Healthy (7-15d)", "Good (15-30d)", "Overstock (30d+)"])
    dist = bins.value_counts().reindex(["Critical (0-3d)", "Low (3-7d)", "Healthy (7-15d)", "Good (15-30d)", "Overstock (30d+)"])
    colors_doh = ["#FF4444", "#F26522", "#22C55E", "#4488FF", "#888888"]

    fig2 = go.Figure(go.Bar(
        x=dist.index, y=dist.values,
        marker_color=colors_doh,
        text=dist.values, textposition="outside",
        hovertemplate="%{x}: %{y} SKU×Store combinations<extra></extra>",
    ))
    fig2.update_layout(
        plot_bgcolor="#0F2040", paper_bgcolor="#0F2040",
        font_color="#E8EDF5", margin=dict(l=0, r=0, t=10, b=10),
        xaxis=dict(showgrid=False, color="#8A9BC0"),
        yaxis=dict(showgrid=True, gridcolor="#1A3060", color="#8A9BC0"),
        height=220,
    )
    st.plotly_chart(fig2, use_container_width=True)
EOF
echo "✅ pages/morning_briefing.py"

cat > pages/action_feed.py << 'EOF'
import streamlit as st
import pandas as pd

def show(signals, actions, inv):
    st.markdown("""
    <div class="ginesys-header">
        <div><h1>⚡ Action Feed</h1>
        <span>Full prioritised action list · Approve, modify or reject</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        risk_filter = st.selectbox("Risk Type", ["All", "stockout", "size_gap", "imbalance", "overstock", "dead_stock"])
    with col_f2:
        action_filter = st.selectbox("Action Type", ["All", "TRANSFER", "REPLENISH", "MARKDOWN", "WAIT"])
    with col_f3:
        conf_filter = st.selectbox("Confidence", ["All", "High", "Medium", "Low"])
    with col_f4:
        status_filter = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"])

    filtered_actions = actions[:]
    if risk_filter != "All":
        filtered_actions = [a for a in filtered_actions if a.risk_type == risk_filter]
    if action_filter != "All":
        filtered_actions = [a for a in filtered_actions if a.action_type == action_filter]
    if conf_filter != "All":
        filtered_actions = [a for a in filtered_actions if a.confidence == conf_filter]
    if status_filter != "All":
        filtered_actions = [a for a in filtered_actions if
                            st.session_state.action_states.get(a.action_id, "Pending") == status_filter]

    pending = [a for a in filtered_actions if st.session_state.action_states.get(a.action_id, "Pending") == "Pending"]
    approved = [a for a in filtered_actions if st.session_state.action_states.get(a.action_id, "Pending") == "Approved"]
    rejected = [a for a in filtered_actions if st.session_state.action_states.get(a.action_id, "Pending") == "Rejected"]

    tab_pending, tab_approved, tab_rejected = st.tabs([
        f"⏳ Pending ({len(pending)})",
        f"✅ Approved ({len(approved)})",
        f"❌ Rejected ({len(rejected)})"
    ])

    def render_action_card(action, tab="pending"):
        state = st.session_state.action_states.get(action.action_id, "Pending")
        risk_colors = {
            "stockout": "#FF4444", "size_gap": "#FFD700",
            "imbalance": "#4488FF", "overstock": "#FF8C00", "dead_stock": "#888888",
        }
        risk_labels = {
            "stockout": "🔴 Stockout", "size_gap": "🟡 Size Gap",
            "imbalance": "🔵 Imbalance", "overstock": "🟠 Overstock", "dead_stock": "⚪ Dead Stock",
        }
        badge_map = {"TRANSFER": "badge-transfer", "MARKDOWN": "badge-markdown",
                     "REPLENISH": "badge-replenish", "WAIT": "badge-wait"}
        conf_map = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}
        risk_color = risk_colors.get(action.risk_type, "#F26522")

        with st.expander(f"[#{action.action_id}] {action.sku_name} · Size {action.size} · {action.action_type} → {action.to_location}", expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"""
                <div style="padding:8px 0">
                    <span class="badge {badge_map.get(action.action_type,'badge-transfer')}">{action.action_type}</span>
                    <span class="badge {conf_map.get(action.confidence,'badge-medium')}">{action.confidence} confidence</span>
                    <span style="font-size:11px; color:{risk_color}; margin-left:6px;">{risk_labels.get(action.risk_type,'Risk')}</span>
                </div>
                <table style="width:100%; color:#E8EDF5; font-size:13px; border-collapse:collapse;">
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">From</td><td>{action.from_location}</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">To</td><td>{action.to_location}</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">Quantity</td><td>{action.quantity} units</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">Mode</td><td>{action.mode} · ETA {action.eta_days}d</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">Cost</td><td>₹{int(action.cost_inr):,}</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">Prevented Loss</td><td style="color:#22C55E">₹{int(action.prevented_loss_inr):,}</td></tr>
                    <tr><td style="color:#8A9BC0; padding:3px 8px 3px 0">Priority Score</td><td style="color:{risk_color}">{action.priority_score:.2f}</td></tr>
                </table>
                <div style="margin-top:10px; padding:8px; background:#0A1628; border-radius:6px; font-size:12px; color:#8A9BC0;">
                    💡 {action.notes}
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if action.action_type == "TRANSFER" and action.cost_inr > 0:
                    st.markdown("**Transfer vs Markdown**")
                    roi = action.prevented_loss_inr / max(action.cost_inr, 1)
                    st.markdown(f"""
                    <div style="background:#0A1628; border-radius:6px; padding:10px; font-size:12px;">
                        <div style="color:#4488FF">Transfer</div>
                        <div>Cost: ₹{int(action.cost_inr):,}</div>
                        <div>ROI: {roi:.1f}x</div>
                        <div style="color:#F26522; margin-top:8px">Markdown (alt)</div>
                        <div>Revenue: ₹{int(action.prevented_loss_inr * 0.7):,}</div>
                        <div>Discount: 20%</div>
                        <div style="margin-top:8px; color:{'#22C55E' if roi > 1.5 else '#F26522'}">
                        {'✅ Transfer preferred' if roi > 1.5 else '⚠️ Consider markdown'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            if state == "Pending":
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("✅ Approve", key=f"af_app_{action.action_id}_{tab}"):
                        st.session_state.action_states[action.action_id] = "Approved"
                        st.rerun()
                with b2:
                    if st.button("❌ Reject", key=f"af_rej_{action.action_id}_{tab}"):
                        st.session_state.action_states[action.action_id] = "Rejected"
                        st.rerun()
            else:
                st.markdown(f"**Status:** {state}")

    with tab_pending:
        if not pending:
            st.success("No pending actions in this filter.")
        for action in pending:
            render_action_card(action, "pending")

    with tab_approved:
        if not approved:
            st.info("No approved actions yet.")
        for action in approved:
            render_action_card(action, "approved")

    with tab_rejected:
        if not rejected:
            st.info("No rejected actions.")
        for action in rejected:
            render_action_card(action, "rejected")
EOF
echo "✅ pages/action_feed.py"

cat > pages/sku_detail.py << 'EOF'
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

def show(inv, sales, signals, actions, skus):
    st.markdown("""
    <div class="ginesys-header">
        <div><h1>🔍 SKU Drill-Down</h1>
        <span>Deep-dive into any SKU across the network</span></div>
    </div>
    """, unsafe_allow_html=True)

    sku_options = {f"{s['sku_id']} · {s['name']}": s['sku_id'] for s in skus}
    selected_label = st.selectbox("Search SKU", list(sku_options.keys()))
    selected_sku = sku_options[selected_label]

    sku_info = next(s for s in skus if s["sku_id"] == selected_sku)
    sku_signals = signals[(signals["sku_id"] == selected_sku) & (signals["store_id"] != "WH")]
    sku_sales = sales[sales["sku_id"] == selected_sku]
    sku_inv = inv[inv["sku_id"] == selected_sku]

    st.markdown(f"""
    <div style="background:#0F2040; border:1px solid #1A3060; border-radius:8px; padding:14px; margin-bottom:16px; display:flex; justify-content:space-between;">
        <div>
            <div style="font-size:16px; font-weight:700; color:#E8EDF5">{sku_info['name']}</div>
            <div style="font-size:12px; color:#8A9BC0">Category: {sku_info['category']} · MRP: ₹{sku_info['price']:,}</div>
        </div>
        <div style="text-align:right">
            <div style="font-size:12px; color:#8A9BC0">Total Network Stock</div>
            <div style="font-size:20px; font-weight:700; color:#4488FF">{sku_inv['available'].sum()} units</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.5, 1])

    with col1:
        # DOH trend: pick one size to show trend
        st.markdown("#### DOH Trend — Network Average (30 Days)")
        sizes_avail = sku_signals["size"].unique().tolist()
        sel_size = st.selectbox("Size", sizes_avail)

        today = date.today()
        # Simulate DOH trend from sales history
        size_sales = sku_sales[sku_sales["size"] == sel_size] if "size" in sku_sales.columns else sku_sales
        daily_units = size_sales.groupby(["date", "store_id"])["units_sold"].sum().reset_index()

        # Reconstruct approximate DOH over time from total network
        daily_network = daily_units.groupby("date")["units_sold"].sum().reset_index()
        daily_network = daily_network.sort_values("date")

        if len(daily_network) > 0:
            # Starting stock estimate
            current_stock = sku_inv[sku_inv["size"] == sel_size]["available"].sum() if sel_size else sku_inv["available"].sum()
            vel_avg = daily_network["units_sold"].mean().clip(lower=0.01)

            doh_trend = []
            stock = current_stock + daily_network["units_sold"].sum()
            for _, row in daily_network.iterrows():
                stock -= row["units_sold"]
                doh = round(stock / vel_avg, 1) if vel_avg > 0 else 999
                doh_trend.append({"date": row["date"], "doh": max(0, doh)})
            doh_df = pd.DataFrame(doh_trend)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=doh_df["date"], y=doh_df["doh"],
                mode="lines+markers", line=dict(color="#4488FF", width=2),
                marker=dict(size=4), name="DOH",
                hovertemplate="%{x}: %{y:.1f} days<extra></extra>",
            ))
            # Threshold lines
            fig.add_hline(y=3, line_dash="dash", line_color="#FF4444",
                          annotation_text="Stockout threshold (3d)", annotation_font_color="#FF4444")
            fig.add_hline(y=30, line_dash="dash", line_color="#F26522",
                          annotation_text="Overstock threshold (30d)", annotation_font_color="#F26522")
            fig.update_layout(
                plot_bgcolor="#0F2040", paper_bgcolor="#0F2040",
                font_color="#E8EDF5", margin=dict(l=0, r=0, t=10, b=10),
                xaxis=dict(showgrid=False, color="#8A9BC0"),
                yaxis=dict(showgrid=True, gridcolor="#1A3060", color="#8A9BC0", title="DOH (days)"),
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Size Breakdown")
        size_table = sku_signals.groupby("size").agg(
            total_stock=("available", "sum"),
            avg_doh=("doh", "mean"),
            avg_velocity=("velocity_30d", "mean"),
            risk=("risk_type", lambda x: x.mode()[0] if len(x) > 0 else "healthy"),
        ).reset_index()
        size_table.columns = ["Size", "Stock", "Avg DOH", "Vel/day", "Risk"]
        size_table["Avg DOH"] = size_table["Avg DOH"].round(1)
        size_table["Vel/day"] = size_table["Vel/day"].round(2)

        def highlight_risk(val):
            c = {"stockout": "#FF4444", "overstock": "#F26522", "dead_stock": "#888888",
                 "size_gap": "#FFD700", "healthy": "#22C55E"}.get(val, "#8A9BC0")
            return f"color: {c}"

        st.dataframe(size_table.style.applymap(highlight_risk, subset=["Risk"]),
                     use_container_width=True, hide_index=True, height=200)

    # ── Store Network View ──────────────────────────────────────────────────────
    st.markdown("#### Network View — Which Stores Have Excess, Which Are Short")
    net_data = sku_signals.groupby(["store_name", "store_tier"]).agg(
        total_stock=("available", "sum"),
        avg_doh=("doh", "mean"),
        risk=("risk_type", lambda x: x.mode()[0] if len(x) > 0 else "healthy"),
    ).reset_index().sort_values("avg_doh")

    risk_color_map = {
        "stockout": "#FF4444", "overstock": "#F26522", "dead_stock": "#888888",
        "size_gap": "#FFD700", "imbalance": "#4488FF", "healthy": "#22C55E",
    }
    colors = [risk_color_map.get(r, "#8A9BC0") for r in net_data["risk"]]

    fig2 = go.Figure(go.Bar(
        x=net_data["store_name"], y=net_data["avg_doh"],
        marker_color=colors,
        text=[f"{d:.0f}d" for d in net_data["avg_doh"]], textposition="outside",
        customdata=net_data[["total_stock", "risk"]].values,
        hovertemplate="<b>%{x}</b><br>DOH: %{y:.1f}d<br>Stock: %{customdata[0]} units<br>Risk: %{customdata[1]}<extra></extra>",
    ))
    fig2.add_hline(y=3, line_dash="dash", line_color="#FF4444")
    fig2.add_hline(y=30, line_dash="dash", line_color="#F26522")
    fig2.update_layout(
        plot_bgcolor="#0F2040", paper_bgcolor="#0F2040",
        font_color="#E8EDF5", margin=dict(l=0, r=0, t=10, b=30),
        xaxis=dict(showgrid=False, color="#8A9BC0"),
        yaxis=dict(showgrid=True, gridcolor="#1A3060", color="#8A9BC0", title="Avg DOH"),
        height=280,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Action History for this SKU ─────────────────────────────────────────────
    st.markdown("#### Recommended Actions for This SKU")
    sku_actions = [a for a in actions if a.sku_id == selected_sku]
    if not sku_actions:
        st.info("No actions generated for this SKU in current run.")
    else:
        rows = []
        for a in sku_actions:
            state = st.session_state.action_states.get(a.action_id, "Pending")
            rows.append({
                "ID": a.action_id, "Size": a.size, "Action": a.action_type,
                "From": a.from_location, "To": a.to_location,
                "Qty": a.quantity, "Cost": f"₹{int(a.cost_inr):,}",
                "Saves": f"₹{int(a.prevented_loss_inr):,}",
                "Confidence": a.confidence, "Status": state,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
EOF
echo "✅ pages/sku_detail.py"

cat > pages/signals.py << 'EOF'
import streamlit as st
import pandas as pd

def show(signals, returns, transit):
    st.markdown("""
    <div class="ginesys-header">
        <div><h1>📡 Signals & Alerts</h1>
        <span>Anomaly detection · Returns spikes · Data gaps</span></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔥 Velocity Anomalies", "🔶 Returns Spikes", "⚠️ Data Gaps"])

    with tab1:
        anomalies = signals[signals["velocity_anomaly"] == True].copy()
        if anomalies.empty:
            st.success("No velocity anomalies detected.")
        else:
            st.markdown(f"**{len(anomalies)} SKU×Store combinations showing unusual demand spike**")
            for _, row in anomalies.iterrows():
                ratio = row.get("velocity_ratio", 0)
                st.markdown(f"""
                <div class="action-card">
                    <b style="color:#FFD700">{row['sku_name']}</b> · Size {row['size']} · {row['store_name']}<br>
                    <small style="color:#8A9BC0">
                        Velocity jumped <b style="color:#F26522">{ratio:.1f}x</b> vs prior 7-day baseline ·
                        Current: {row['velocity_7d']:.1f}/day vs Prior: {row['velocity_prior7d']:.1f}/day
                    </small><br>
                    <small style="color:#8A9BC0">💡 Check for unplanned sale event, markdown, or viral demand. Confirm before pre-positioning stock.</small>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.button("✅ Confirm Event", key=f"ev_{row['sku_id']}_{row['size']}_{row['store_id']}")

    with tab2:
        spikes = returns[returns["spike"] == True].copy()
        if spikes.empty:
            st.success("No returns spikes detected.")
        else:
            st.markdown(f"**{len(spikes)} locations with unusual returns volume**")
            for _, row in spikes.iterrows():
                st.markdown(f"""
                <div class="action-card" style="border-left-color:#FF6600">
                    <b style="color:#FF6600">{row['sku_name']}</b> · Size {row['size']} · Store {row['store_id']}<br>
                    <small style="color:#8A9BC0">
                        <b style="color:#FF4444">{row['returns_last_7d']}</b> returns in last 7d ·
                        Avg baseline: {row['avg_daily_returns']:.1f}/day
                    </small><br>
                    <small style="color:#8A9BC0">⚠️ Available stock may be overstated until QC confirms units are resaleable.</small>
                </div>
                """, unsafe_allow_html=True)

    with tab3:
        gaps = transit[transit["status"] == "Unknown"].copy()
        if gaps.empty:
            st.success("All shipments have confirmed status.")
        else:
            st.markdown(f"**{len(gaps)} shipments with unknown tracking status**")
            for _, row in gaps.iterrows():
                st.markdown(f"""
                <div class="action-card" style="border-left-color:#FFCC00">
                    <b style="color:#FFCC00">Shipment {row['shipment_id']}</b> · {row['sku_id']} Size {row['size']}<br>
                    <small style="color:#8A9BC0">
                        To: {row['to_name']} · Qty: {row['quantity']} units · ETA: {row['eta_days']}d
                    </small><br>
                    <small style="color:#8A9BC0">⚠️ Status unknown — recommendations for this route may be inaccurate. Contact logistics to confirm.</small>
                </div>
                """, unsafe_allow_html=True)
EOF
echo "✅ pages/signals.py"

cat > pages/ai_copilot.py << 'EOF'
import streamlit as st
import json
import os

SUGGESTED_QUESTIONS = [
    "Which stores will stock out this weekend?",
    "Why is Connaught Place flagged as high risk?",
    "Should I transfer or markdown the Sherwani Set?",
    "What's driving the velocity spike on Linen Kurta?",
    "Which SKUs should I pre-position before Diwali?",
    "Show me overstock items I can liquidate quickly",
]


def build_context(data):
    summary      = data["summary"]
    risk_df      = data["risk_df"]
    actions_df   = data["actions_df"]
    store_health = data["store_health"]
    events       = data["events"]
    today        = data["today"]

    # Top critical items
    critical = risk_df[risk_df["risk_severity"] == "critical"][
        ["sku_name", "size", "store_name", "risk_type", "doh", "daily_velocity_7d", "effective_stock"]
    ].head(15)

    # Top actions
    top_actions = actions_df[["sku_name", "size", "store_name", "risk_type", "recommended_action",
                               "transfer_qty", "from_location", "to_location", "prevented_loss",
                               "confidence", "priority_score"]].head(15) if actions_df is not None and not actions_df.empty else None

    # Store health
    store_h = store_health[["store_name", "city", "tier", "critical_count", "warning_count", "health_pct", "status"]]

    # Events
    ev_list = []
    for _, ev in events.iterrows():
        days_away = (ev["start_date"] - today).days
        ev_list.append(f"{ev['event_name']} in {days_away} days, affects {ev['affected_categories']}, {ev['expected_demand_multiplier']}x demand")

    context = f"""
TODAY: {today}
NETWORK SNAPSHOT:
- Total SKU-locations: {summary['total_sku_locations']}
- Critical stockouts: {summary['stockout_critical_count']}
- At-risk (warning): {summary['stockout_warning_count']}
- Overstock locations: {summary['overstock_count']}
- Overstock value: ₹{summary['overstock_value']:,}
- Network health: {summary['network_health_pct']}%
- Pending actions: {summary['pending_actions']}
- Velocity anomalies: {summary['anomaly_count']}
- Data gaps: {summary['data_gap_count']}
- Capital at risk (stockout): ₹{summary['capital_at_risk']:,}

UPCOMING EVENTS:
{chr(10).join(ev_list)}

STORE HEALTH:
{store_h.to_string(index=False)}

CRITICAL ITEMS (top 15):
{critical.to_string(index=False)}

TOP RECOMMENDED ACTIONS (top 15):
{top_actions.to_string(index=False) if top_actions is not None else "No actions available"}
"""
    return context


def call_groq(messages, context):
    try:
        from groq import Groq

        # Try Streamlit secrets first, then env var
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            api_key = os.environ.get("GROQ_API_KEY", "")

        if not api_key:
            return None, "no_key"

        client = Groq(api_key=api_key)

        system_prompt = f"""You are an expert inventory copilot for a multi-store Indian apparel retail ops manager.
You have real-time access to their network inventory data. Answer questions specifically using this data.
Be direct, specific, and operational. Reference actual SKU names, store names, and numbers.
Do NOT make up data not present in the context. Format responses clearly with bullet points where helpful.
Use ₹ for currency. Keep responses concise — this is an ops tool, not a report.

LIVE INVENTORY CONTEXT:
{context}"""

        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=api_messages,
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content, "ok"

    except ImportError:
        return None, "no_groq"
    except Exception as e:
        return None, str(e)


def render(data):
    st.markdown("""
    <div class="page-title">AI Inventory Copilot</div>
    <div class="page-subtitle">Ask anything about your inventory · Answers grounded in live network data</div>
    """, unsafe_allow_html=True)

    # ── API KEY CHECK ─────────────────────────────────────────────────────────
    has_key = False
    try:
        k = st.secrets.get("GROQ_API_KEY", "")
        has_key = bool(k)
    except Exception:
        has_key = bool(os.environ.get("GROQ_API_KEY", ""))

    if not has_key:
        st.markdown("""
        <div class="alert-banner">
            🔑 Add your Groq API key to enable the AI Copilot.<br>
            In Streamlit Cloud → App Settings → Secrets → add: <code>GROQ_API_KEY = "your-key"</code><br>
            Get a free key at <strong>console.groq.com</strong>
        </div>
        """, unsafe_allow_html=True)

        # Show demo mode
        st.markdown("""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:20px 24px;margin-top:16px;">
            <div style="font-size:14px;font-weight:600;color:#1B2B5E;margin-bottom:12px;">💡 What you can ask the copilot:</div>
        </div>
        """, unsafe_allow_html=True)

        for q in SUGGESTED_QUESTIONS:
            st.markdown(f"""
            <div style="background:#F4F6FB;border:1px solid #E2E8F0;border-radius:8px;padding:10px 16px;margin-bottom:8px;font-size:13px;color:#475569;">
                💬 "{q}"
            </div>
            """, unsafe_allow_html=True)
        return

    # ── CONTEXT BUILDER ───────────────────────────────────────────────────────
    context = build_context(data)

    # ── CHAT UI ───────────────────────────────────────────────────────────────
    col_chat, col_suggest = st.columns([7, 3])

    with col_suggest:
        st.markdown("<div class='section-header'>Quick Questions</div>", unsafe_allow_html=True)
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, key=f"sq_{q[:20]}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                response, status = call_groq(st.session_state.chat_history, context)
                if response:
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

    with col_chat:
        # Chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div style="text-align:center;padding:48px 24px;color:#64748B;">
                    <div style="font-size:32px;margin-bottom:12px;">🤖</div>
                    <div style="font-size:16px;font-weight:600;color:#1B2B5E;margin-bottom:8px;">Inventory Copilot Ready</div>
                    <div style="font-size:13px;">Ask me anything about your network — stockouts, transfers, markdowns, Diwali prep.</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-end;margin-bottom:12px;">
                            <div style="background:#F1F5F9;border:1px solid #CBD5E1;border-radius:12px 12px 2px 12px;padding:12px 16px;max-width:75%;font-size:13px;color:#1B2B5E;">
                                {msg['content']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="display:flex;justify-content:flex-start;margin-bottom:12px;">
                            <div style="margin-right:8px;font-size:18px;margin-top:4px;">🤖</div>
                            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:2px 12px 12px 12px;padding:12px 16px;max-width:85%;font-size:13px;color:#475569;line-height:1.6;">
                                {msg['content'].replace(chr(10), '<br>')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        # Input
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        user_input = st.chat_input("Ask about inventory, risks, transfers, or Diwali prep...")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("Analysing inventory data..."):
                response, status = call_groq(st.session_state.chat_history, context)

            if response:
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            elif status == "no_key":
                st.error("API key not found. Check Streamlit secrets.")
            elif status == "no_groq":
                st.error("Groq library not installed. Add `groq>=0.4.0` to requirements.txt")
            else:
                st.error(f"API error: {status}")

            st.rerun()

        # Clear chat
        if st.session_state.chat_history:
            if st.button("🗑 Clear conversation", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

    # ── CONTEXT PREVIEW ───────────────────────────────────────────────────────
    with st.expander("🔍 View data context sent to AI"):
        st.code(context, language="text")
EOF
echo "✅ pages/ai_copilot.py"

cat > pages/store_analytics.py << 'EOF'
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


TIER_COLORS = {"A": "#1B2B5E", "B": "#F47920", "C": "#94A3B8"}
RISK_COLORS = {
    "stockout":        "#DC2626",
    "stockout_warning":"#F47920",
    "size_gap":        "#DC2626",
    "overstock":       "#2563EB",
    "dead_stock":      "#64748B",
    "velocity_anomaly":"#7C3AED",
    "returns_spike":   "#F59E0B",
    "data_gap":        "#94A3B8",
    "healthy":         "#16A34A",
}


def render(data):
    risk_df      = data["risk_df"]
    actions_df   = data["actions_df"]
    store_health = data["store_health"]
    sales        = data["sales"]
    inventory    = data["inventory"]
    today        = data["today"]

    st.markdown("""
    <div class="page-title">Store Analytics</div>
    <div class="page-subtitle">Per-store health, risk breakdown, and revenue at risk · Select a store to drill in</div>
    """, unsafe_allow_html=True)

    store_names = store_health["store_name"].tolist()
    selected_store = st.selectbox("Select Store", ["All Stores"] + store_names, key="store_analytics_select")

    if selected_store == "All Stores":
        _render_all_stores(store_health, risk_df, actions_df, sales)
    else:
        store_row = store_health[store_health["store_name"] == selected_store].iloc[0]
        _render_single_store(store_row, risk_df, actions_df, sales, inventory, today)


def _render_all_stores(store_health, risk_df, actions_df, sales):
    total_stores    = len(store_health)
    critical_stores = len(store_health[store_health["status"] == "critical"])
    avg_health      = round(store_health["health_pct"].mean(), 1)
    worst_store     = store_health.sort_values("health_pct").iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        (c1, "Stores Monitored",  str(total_stores),          "navy"),
        (c2, "Critical Stores",   str(critical_stores),        "red"),
        (c3, "Avg Network Health", f"{avg_health}%",           "green" if avg_health >= 70 else "amber"),
        (c4, "Needs Attention",   worst_store["store_name"],   "red"),
    ]
    for col, label, val, color in kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card {color}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:{'18px' if len(val)>8 else '26px'};">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    left, right = st.columns([5, 5], gap="large")

    with left:
        st.markdown("<div class='section-header'>Store Health Ranking</div>", unsafe_allow_html=True)
        for _, store in store_health.sort_values("health_pct", ascending=False).iterrows():
            pct = store["health_pct"]
            bar_color = "#DC2626" if pct < 50 else ("#F47920" if pct < 75 else "#16A34A")
            tc = TIER_COLORS.get(store["tier"], "#94A3B8")
            st.markdown(f"""
            <div style="margin-bottom:14px;background:#FFFFFF;padding:12px 16px;border-radius:8px;
                        border:1px solid #E2E8F0;box-shadow:0 1px 3px rgba(27,43,94,0.05);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div>
                        <span style="font-size:13px;font-weight:700;color:#1B2B5E;">{store['store_name']}</span>
                        <span style="font-size:11px;color:#64748B;margin-left:6px;">{store['city']}</span>
                        <span style="font-size:10px;font-weight:700;color:{tc};background:rgba(27,43,94,0.06);
                              padding:1px 6px;border-radius:4px;margin-left:6px;">Tier {store['tier']}</span>
                    </div>
                    <div style="font-size:15px;font-weight:700;color:{bar_color};">{pct}%</div>
                </div>
                <div style="background:#F1F5F9;border-radius:4px;height:6px;overflow:hidden;">
                    <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:4px;"></div>
                </div>
                <div style="display:flex;gap:14px;margin-top:5px;font-size:11px;">
                    <span style="color:#DC2626;">🔴 {store['critical_count']} critical</span>
                    <span style="color:#F47920;">🟠 {store['warning_count']} warning</span>
                    <span style="color:#16A34A;">✓ {store['healthy_count']} healthy</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-header'>Risk Mix by Store</div>", unsafe_allow_html=True)
        risk_mix = risk_df.groupby(["store_name", "risk_type"]).size().reset_index(name="count")
        stores_order = store_health.sort_values("health_pct", ascending=False)["store_name"].tolist()
        fig = px.bar(risk_mix, x="count", y="store_name", color="risk_type", orientation="h",
                     color_discrete_map=RISK_COLORS, category_orders={"store_name": stores_order})
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=340,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="left", x=0,
                        font=dict(size=10, color="#64748B"), title=None),
            xaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", showline=False, title=None),
            yaxis=dict(tickfont=dict(color="#1B2B5E", size=11), showgrid=False, title=None),
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-header'>30-Day Revenue by Store</div>", unsafe_allow_html=True)
    rev = sales.groupby(["store_name", "date"])["revenue"].sum().reset_index()
    fig2 = px.line(rev, x="date", y="revenue", color="store_name",
                   labels={"revenue": "Revenue (₹)", "date": "", "store_name": "Store"})
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", showline=False),
        yaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", showline=False,
                   tickprefix="₹", tickformat=",.0f"),
        legend=dict(font=dict(size=10, color="#64748B"), title=None),
        hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-header'>Overstock Capital Tied by Store</div>", unsafe_allow_html=True)
    overstock = risk_df[risk_df["risk_type"].isin(["overstock","dead_stock"])].copy()
    if not overstock.empty:
        overstock["value"] = overstock["effective_stock"] * overstock["mrp"]
        ov_by_store = overstock.groupby(["store_name","city","tier"]).agg(
            overstock_value=("value","sum"), sku_count=("sku_id","nunique"),
        ).reset_index().sort_values("overstock_value", ascending=False)
        ov_by_store["Overstock Value"] = ov_by_store["overstock_value"].apply(lambda v: f"₹{v/100000:.1f}L")
        st.dataframe(ov_by_store[["store_name","city","tier","Overstock Value","sku_count"]].rename(columns={
            "store_name":"Store","city":"City","tier":"Tier","sku_count":"SKUs Affected"}),
            use_container_width=True, hide_index=True)
    else:
        st.success("No overstock detected across the network.")


def _render_single_store(store_row, risk_df, actions_df, sales, inventory, today):
    store_id   = store_row["store_id"]
    store_name = store_row["store_name"]
    pct        = store_row["health_pct"]
    bar_color  = "#DC2626" if pct < 50 else ("#F47920" if pct < 75 else "#16A34A")
    tc         = TIER_COLORS.get(store_row["tier"], "#94A3B8")

    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
                padding:18px 24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(27,43,94,0.06);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div style="font-size:20px;font-weight:700;color:#1B2B5E;">{store_name}</div>
                <div style="font-size:13px;color:#64748B;margin-top:4px;">
                    {store_row['city']} ·
                    <span style="color:{tc};font-weight:600;">Tier {store_row['tier']}</span> ·
                    {store_row['total_skus']} SKU-size combinations tracked
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:30px;font-weight:700;color:{bar_color};">{pct}%</div>
                <div style="font-size:11px;color:#64748B;">health score</div>
            </div>
        </div>
        <div style="background:#F1F5F9;border-radius:4px;height:7px;margin-top:12px;overflow:hidden;">
            <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    store_risk  = risk_df[risk_df["store_id"] == store_id].copy()
    store_sales = sales[sales["store_id"] == store_id].copy()

    total_revenue = store_sales["revenue"].sum()
    last7_rev     = store_sales[store_sales["date"] >= (today - pd.Timedelta(days=6))]["revenue"].sum()
    ov_mask       = store_risk["risk_type"].isin(["overstock","dead_stock"])
    overstock_val = (store_risk[ov_mask]["effective_stock"] * store_risk[ov_mask]["mrp"]).sum()
    critical_skus = len(store_risk[store_risk["risk_severity"] == "critical"])
    store_actions = actions_df[actions_df["store_id"] == store_id] if actions_df is not None and not actions_df.empty else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        (c1, "30-Day Revenue",  f"₹{total_revenue/100000:.1f}L", "navy"),
        (c2, "Last 7 Days",     f"₹{last7_rev/1000:.0f}K",       "blue"),
        (c3, "Critical SKUs",   str(critical_skus),               "red" if critical_skus > 0 else "green"),
        (c4, "Overstock Value", f"₹{overstock_val/1000:.0f}K",    "amber" if overstock_val > 50000 else "green"),
    ]
    for col, label, val, color in kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card {color}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:24px;">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    left, right = st.columns([5, 5], gap="large")

    with left:
        st.markdown("<div class='section-header'>Risk Breakdown</div>", unsafe_allow_html=True)
        risk_counts = store_risk["risk_type"].value_counts().reset_index()
        risk_counts.columns = ["risk_type", "count"]
        risk_counts["color"] = risk_counts["risk_type"].map(RISK_COLORS)
        fig = go.Figure(go.Bar(
            x=risk_counts["risk_type"].str.replace("_"," ").str.title(),
            y=risk_counts["count"],
            marker_color=risk_counts["color"],
            marker_line_width=0,
            text=risk_counts["count"], textposition="outside",
            textfont=dict(color="#1B2B5E", size=11),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=220,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(tickfont=dict(color="#64748B", size=10), showgrid=False),
            yaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", title=None),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        st.markdown("<div class='section-header'>Daily Revenue Trend</div>", unsafe_allow_html=True)
        daily = store_sales.groupby("date")["revenue"].sum().reset_index()
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=daily["date"], y=daily["revenue"], mode="lines",
            line=dict(color="#1B2B5E", width=2, shape="spline"),
            fill="tozeroy", fillcolor="rgba(27,43,94,0.07)",
            hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=220,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", showline=False),
            yaxis=dict(tickfont=dict(color="#64748B", size=10), gridcolor="#F1F5F9", showline=False,
                       tickprefix="₹", tickformat=",.0f"),
            showlegend=False, hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='section-header'>SKU-Level Risk Detail</div>", unsafe_allow_html=True)
    at_risk = store_risk[store_risk["risk_type"] != "healthy"].copy()
    if at_risk.empty:
        st.success(f"✅ {store_name} has no at-risk SKUs.")
    else:
        display = at_risk[["sku_name","size","category","risk_type","risk_severity","doh","effective_stock","daily_velocity_7d"]].copy()
        display.columns = ["SKU","Size","Category","Risk","Severity","DOH (days)","Available","Velocity (u/day)"]
        display["DOH (days)"] = display["DOH (days)"].apply(lambda d: f"{d:.1f}" if d < 999 else "N/A")
        display["Velocity (u/day)"] = display["Velocity (u/day)"].apply(lambda v: f"{v:.1f}")
        display = display.sort_values("Severity", ascending=False)
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header'>Pending Actions for This Store</div>", unsafe_allow_html=True)
    if store_actions.empty:
        st.info("No pending actions for this store.")
    else:
        for _, row in store_actions.head(8).iterrows():
            action_key = f"{row['sku_id']}_{row['size']}_{row['store_id']}"
            is_approved = action_key in st.session_state.approved_actions
            is_rejected = action_key in st.session_state.rejected_actions
            sev_class   = "critical" if row.get("risk_severity") == "critical" else "warning"
            prevented   = f"₹{row.get('prevented_loss',0):,.0f}" if row.get("prevented_loss",0) > 0 else "—"
            status_tag  = ""
            if is_approved:
                status_tag = '<span style="color:#16A34A;font-weight:600;font-size:12px;">✅ Approved</span>'
            elif is_rejected:
                status_tag = '<span style="color:#64748B;font-size:12px;">✗ Rejected</span>'

            st.markdown(f"""
            <div class="action-card {sev_class}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-size:13px;font-weight:700;color:#1B2B5E;">{row['sku_name']}</span>
                        <span style="font-size:11px;color:#64748B;margin-left:8px;">Size {row['size']}</span>
                    </div>
                    {status_tag}
                </div>
                <div style="font-size:12px;color:#475569;margin-top:6px;">
                    <strong>{str(row.get('recommended_action','—')).replace('_',' ').title()}:</strong>
                    {row.get('action_detail','—')}
                    <span style="color:#16A34A;margin-left:12px;">Save: {prevented}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not is_approved and not is_rejected:
                b1, b2, _ = st.columns([1,1,6])
                with b1:
                    if st.button("✓ Approve", key=f"sa_approve_{action_key}", type="primary"):
                        st.session_state.approved_actions.add(action_key)
                        st.rerun()
                with b2:
                    if st.button("✗ Reject", key=f"sa_reject_{action_key}"):
                        st.session_state.rejected_actions.add(action_key)
                        st.rerun()

    st.markdown("<div class='section-header'>Size × Category DOH Heatmap</div>", unsafe_allow_html=True)
    size_cat = store_risk.groupby(["category","size"])["doh"].mean().reset_index()
    size_cat["doh_plot"] = size_cat["doh"].clip(upper=60)
    if not size_cat.empty:
        pivot = size_cat.pivot(index="category", columns="size", values="doh_plot").fillna(0)
        ann   = size_cat.pivot(index="category", columns="size", values="doh").fillna(0)
        fig3  = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=[[0,"#DC2626"],[0.15,"#F47920"],[0.5,"#16A34A"],[1.0,"#2563EB"]],
            text=ann.values,
            texttemplate="%{text:.1f}d",
            showscale=True,
            hovertemplate="Category: %{y}<br>Size: %{x}<br>Avg DOH: %{z:.1f}d<extra></extra>",
        ))
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=200,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(tickfont=dict(color="#1B2B5E", size=11)),
            yaxis=dict(tickfont=dict(color="#1B2B5E", size=11)),
        )
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
EOF
echo "✅ pages/store_analytics.py"

cat > pages/rules_engine.py << 'EOF'
import streamlit as st

RULE_GROUPS = {
    "Risk Thresholds": {
        "description": "Define when inventory is flagged as critical, warning, or dead.",
        "rules": [
            {
                "key": "doh_stockout_critical",
                "label": "Stockout Critical Threshold (days)",
                "desc": "DOH below this = 🔴 Critical Stockout. Triggers immediate transfer or replenish action.",
                "type": "int",
                "min": 1, "max": 14, "default": 3,
                "unit": "days",
            },
            {
                "key": "doh_stockout_warning",
                "label": "Stockout Warning Threshold (days)",
                "desc": "DOH below this = 🟡 At Risk. Triggers monitoring and pre-positioning.",
                "type": "int",
                "min": 3, "max": 21, "default": 7,
                "unit": "days",
            },
            {
                "key": "doh_overstock",
                "label": "Overstock Threshold (days)",
                "desc": "DOH above this with low velocity = 🔵 Overstock. Triggers markdown suggestion.",
                "type": "int",
                "min": 15, "max": 90, "default": 30,
                "unit": "days",
            },
            {
                "key": "dead_stock_days",
                "label": "Dead Stock — No Sales For (days)",
                "desc": "SKU with zero sales for this many days = ⚪ Dead Stock. Triggers aggressive markdown.",
                "type": "int",
                "min": 7, "max": 60, "default": 21,
                "unit": "days",
            },
        ],
    },
    "Anomaly Detection": {
        "description": "Control sensitivity for velocity spikes and returns spikes.",
        "rules": [
            {
                "key": "velocity_spike_mult",
                "label": "Velocity Spike Multiplier",
                "desc": "7-day velocity / 30-day baseline above this = Velocity Anomaly flag. E.g. 2.0 = velocity doubled.",
                "type": "float",
                "min": 1.2, "max": 5.0, "step": 0.1, "default": 2.0,
                "unit": "x baseline",
            },
            {
                "key": "returns_spike_mult",
                "label": "Returns Spike Multiplier",
                "desc": "Returns in last 2 days / 7-day avg above this = Returns Spike flag.",
                "type": "float",
                "min": 1.5, "max": 10.0, "step": 0.5, "default": 2.5,
                "unit": "x avg",
            },
        ],
    },
    "Transfer Rules": {
        "description": "Control when and how inventory transfers are recommended.",
        "rules": [
            {
                "key": "transfer_min_qty",
                "label": "Minimum Transfer Quantity (units)",
                "desc": "Actions below this quantity are not recommended — too small to justify logistics cost.",
                "type": "int",
                "min": 1, "max": 50, "default": 10,
                "unit": "units",
            },
            {
                "key": "logistics_express",
                "label": "Express Logistics Cost (₹ per unit)",
                "desc": "Cost used when DOH is critically low and speed matters. Compared against margin before recommending.",
                "type": "int",
                "min": 20, "max": 200, "default": 45,
                "unit": "₹/unit",
            },
            {
                "key": "logistics_surface",
                "label": "Surface Logistics Cost (₹ per unit)",
                "desc": "Standard logistics cost used for non-urgent transfers.",
                "type": "int",
                "min": 5, "max": 100, "default": 18,
                "unit": "₹/unit",
            },
        ],
    },
    "Markdown Rules": {
        "description": "Control markdown percentages for overstock and dead inventory.",
        "rules": [
            {
                "key": "markdown_pct_overstock",
                "label": "Overstock Markdown %",
                "desc": "Markdown percentage applied when DOH exceeds overstock threshold.",
                "type": "int",
                "min": 5, "max": 60, "default": 30,
                "unit": "%",
            },
            {
                "key": "markdown_pct_dead",
                "label": "Dead Stock Markdown %",
                "desc": "Markdown percentage for SKUs with no sales — more aggressive.",
                "type": "int",
                "min": 10, "max": 80, "default": 40,
                "unit": "%",
            },
        ],
    },
    "Priority Scoring": {
        "description": "Weights used to rank actions. Must sum to 1.0 (system auto-normalises).",
        "rules": [
            {
                "key": "priority_revenue_w",
                "label": "Revenue Potential Weight",
                "desc": "Higher weight = actions protecting more revenue rank higher.",
                "type": "float",
                "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.40,
                "unit": "weight",
            },
            {
                "key": "priority_urgency_w",
                "label": "Stockout Urgency Weight",
                "desc": "Higher weight = actions with imminent stockouts rank higher.",
                "type": "float",
                "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.40,
                "unit": "weight",
            },
            {
                "key": "priority_tier_w",
                "label": "Store Tier Weight",
                "desc": "Higher weight = Tier A stores get prioritised for stock allocation.",
                "type": "float",
                "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.20,
                "unit": "weight",
            },
        ],
    },
    "Automation": {
        "description": "Control when the system can act without manual approval.",
        "rules": [
            {
                "key": "auto_approve_low_risk",
                "label": "Auto-Approve Low-Risk Actions",
                "desc": "When enabled, low-confidence, low-cost actions (< ₹500 logistics) execute automatically with notification.",
                "type": "bool",
                "default": False,
            },
        ],
    },
}


def get_impact_label(key, val):
    """Return human-readable impact text for rule changes."""
    impacts = {
        "doh_stockout_critical": f"SKUs with DOH ≤ {val}d will trigger immediate action",
        "doh_stockout_warning": f"SKUs with DOH ≤ {val}d will be flagged for monitoring",
        "doh_overstock": f"SKUs with DOH > {val}d and low velocity will be marked overstock",
        "dead_stock_days": f"SKUs with no sales for {val}+ days will trigger aggressive markdown",
        "velocity_spike_mult": f"Demand {val}x above baseline triggers anomaly flag",
        "returns_spike_mult": f"Returns {val}x above average triggers spike alert",
        "transfer_min_qty": f"Transfers < {val} units will not be recommended",
        "logistics_express": f"Express transfers cost ₹{val}/unit",
        "logistics_surface": f"Surface transfers cost ₹{val}/unit",
        "markdown_pct_overstock": f"Overstock markdown = {val}% off MRP",
        "markdown_pct_dead": f"Dead stock markdown = {val}% off MRP",
        "priority_revenue_w": f"{int(val*100)}% of priority score from revenue saved",
        "priority_urgency_w": f"{int(val*100)}% of priority score from stockout urgency",
        "priority_tier_w": f"{int(val*100)}% of priority score from store tier",
        "auto_approve_low_risk": f"Auto-approve {'enabled' if val else 'disabled'}",
    }
    return impacts.get(key, "")


def render(data):
    rules = st.session_state.rules
    summary = data["summary"]

    st.markdown("""
    <div class="page-title">⚙️ Rules Engine</div>
    <div class="page-subtitle">Configure decision thresholds, transfer rules, and priority weights · Changes apply to next engine run</div>
    """, unsafe_allow_html=True)

    # ── STATUS BAR ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("Stockout Critical DOH", f"{rules['doh_stockout_critical']}d", "red"),
        ("Overstock DOH", f"{rules['doh_overstock']}d", "blue"),
        ("Dead Stock Trigger", f"{rules['dead_stock_days']}d", "amber"),
        ("Auto-Approve", "ON" if rules["auto_approve_low_risk"] else "OFF",
         "green" if rules["auto_approve_low_risk"] else "navy"),
    ]
    for col, (label, val, color) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class="kpi-card {color}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:24px;">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── RULE GROUPS ───────────────────────────────────────────────────────────
    changed_keys = []

    for group_name, group in RULE_GROUPS.items():
        with st.expander(f"**{group_name}** — {group['description']}", expanded=(group_name == "Risk Thresholds")):
            for rule in group["rules"]:
                key = rule["key"]
                current_val = rules.get(key, rule["default"])

                col_label, col_input, col_impact = st.columns([3, 2, 5])

                with col_label:
                    st.markdown(f"""
                    <div style="padding-top:4px;">
                        <div style="font-size:13px;font-weight:600;color:#1B2B5E;">{rule['label']}</div>
                        <div style="font-size:11px;color:#64748B;margin-top:2px;">{rule['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_input:
                    if rule["type"] == "int":
                        new_val = st.number_input(
                            label=rule["label"],
                            min_value=rule["min"],
                            max_value=rule["max"],
                            value=int(current_val),
                            step=1,
                            key=f"rule_input_{key}",
                            label_visibility="collapsed",
                        )
                    elif rule["type"] == "float":
                        new_val = st.number_input(
                            label=rule["label"],
                            min_value=float(rule["min"]),
                            max_value=float(rule["max"]),
                            value=float(current_val),
                            step=float(rule.get("step", 0.1)),
                            format="%.2f",
                            key=f"rule_input_{key}",
                            label_visibility="collapsed",
                        )
                    elif rule["type"] == "bool":
                        new_val = st.toggle(
                            label=rule["label"],
                            value=bool(current_val),
                            key=f"rule_input_{key}",
                            label_visibility="collapsed",
                        )
                    else:
                        new_val = current_val

                    if rule.get("unit"):
                        st.markdown(f"<div style='font-size:10px;color:#94A3B8;margin-top:2px;'>{rule['unit']}</div>", unsafe_allow_html=True)

                with col_impact:
                    impact = get_impact_label(key, new_val)
                    changed = new_val != current_val
                    impact_color = "#C2540A" if changed else "#64748B"
                    changed_tag = " <span style='color:#F47920;font-weight:700;'>← changed</span>" if changed else ""
                    st.markdown(f"""
                    <div style="padding-top:6px;font-size:12px;color:{impact_color};">
                        💡 {impact}{changed_tag}
                    </div>
                    """, unsafe_allow_html=True)

                # Update in session
                if new_val != current_val:
                    rules[key] = new_val
                    changed_keys.append(key)

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── PRIORITY WEIGHT VALIDATION ────────────────────────────────────────────
    total_w = rules["priority_revenue_w"] + rules["priority_urgency_w"] + rules["priority_tier_w"]
    if abs(total_w - 1.0) > 0.01:
        st.markdown(f"""
        <div class="alert-banner">
            ⚠️ Priority weights sum to {total_w:.2f} — should be 1.00.
            The engine will auto-normalise, but review your inputs.
        </div>
        """, unsafe_allow_html=True)

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    st.markdown("---")
    col_save, col_reset, col_info = st.columns([2, 2, 6])

    with col_save:
        if st.button("💾  Save & Apply Rules", type="primary", use_container_width=True):
            st.session_state.rules = rules
            # Clear cached data so engine re-runs with new thresholds on next load
            st.cache_data.clear()
            st.success(f"✅ Rules saved. {len(changed_keys)} rule(s) updated. Refresh the page to re-run the engine with new thresholds.")

    with col_reset:
        if st.button("↩  Reset to Defaults", use_container_width=True):
            st.session_state.rules = {
                "doh_stockout_critical": 3,
                "doh_stockout_warning": 7,
                "doh_overstock": 30,
                "dead_stock_days": 21,
                "velocity_spike_mult": 2.0,
                "returns_spike_mult": 2.5,
                "transfer_min_qty": 10,
                "logistics_express": 45,
                "logistics_surface": 18,
                "markdown_pct_overstock": 30,
                "markdown_pct_dead": 40,
                "priority_revenue_w": 0.40,
                "priority_urgency_w": 0.40,
                "priority_tier_w": 0.20,
                "auto_approve_low_risk": False,
            }
            st.rerun()

    with col_info:
        st.markdown("""
        <div style="font-size:12px;color:#64748B;padding-top:6px;">
            Rules govern all <strong>risk classification</strong>, <strong>action logic</strong>, and <strong>priority ranking</strong>.
            Changes take effect on the next engine run (page refresh after saving).
        </div>
        """, unsafe_allow_html=True)

    # ── CURRENT RULES TABLE ───────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Current Active Rules</div>", unsafe_allow_html=True)
    import pandas as pd
    rows = []
    for group_name, group in RULE_GROUPS.items():
        for rule in group["rules"]:
            key = rule["key"]
            val = rules.get(key, rule["default"])
            rows.append({
                "Group": group_name,
                "Rule": rule["label"],
                "Current Value": f"{val} {rule.get('unit', '')}".strip(),
                "Default": f"{rule['default']} {rule.get('unit', '')}".strip(),
                "Changed": "✏️ Yes" if val != rule["default"] else "—",
            })
    rules_df = pd.DataFrame(rows)
    st.dataframe(rules_df, use_container_width=True, hide_index=True)
EOF
echo "✅ pages/rules_engine.py"

echo ""
echo "Committing to GitHub..."
git add .
git status
git commit -m "feat: Ginesys theme, sidebar fix, Store Analytics, Rules Engine"
git push origin main
echo ""
echo "✅ Done! Streamlit Cloud will redeploy in ~60 seconds."
