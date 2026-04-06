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

def render(data):
    show(data)
