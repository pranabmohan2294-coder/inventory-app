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
