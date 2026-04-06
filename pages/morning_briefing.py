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
