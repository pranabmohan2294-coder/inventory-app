import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta


def render(data):
    sales      = data["sales"]
    risk_df    = data["risk_df"]
    actions_df = data["actions_df"]
    inventory  = data["inventory"]

    st.markdown("""
    <div class="page-title">SKU Drill Down</div>
    <div class="page-subtitle">Deep-dive into any SKU — DOH trend, size breakdown, store network</div>
    """, unsafe_allow_html=True)

    # SKU selector
    sku_options = sorted(risk_df["sku_name"].unique().tolist())
    selected_sku_name = st.selectbox("Select SKU", sku_options, key="sku_select")
    selected_sku_id = risk_df[risk_df["sku_name"] == selected_sku_name]["sku_id"].iloc[0]

    sku_meta = risk_df[risk_df["sku_id"] == selected_sku_id].iloc[0]

    # ── SKU META HEADER ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0f1117;border:1px solid #1e2130;border-radius:12px;padding:16px 24px;margin:12px 0 20px 0;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div style="font-size:18px;font-weight:700;color:#f0f6fc;">{selected_sku_name}</div>
                <div style="font-size:12px;color:#8b949e;margin-top:4px;">
                    {sku_meta['category']} · SKU {selected_sku_id} · MRP ₹{sku_meta['mrp']:,}
                </div>
            </div>
            <div style="text-align:right;font-size:12px;color:#8b949e;">
                {len(risk_df[risk_df['sku_id'] == selected_sku_id])} store-size combinations tracked
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── DOH TREND CHART ───────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Days on Hand Trend · Network Average (30 days)</div>", unsafe_allow_html=True)

    sku_sales = sales[sales["sku_id"] == selected_sku_id].copy()
    sku_inventory = inventory[inventory["sku_id"] == selected_sku_id].copy()

    # Compute daily velocity and rolling DOH
    daily_sales = sku_sales.groupby("date")["units_sold"].sum().reset_index()
    daily_sales = daily_sales.sort_values("date")
    daily_sales["rolling_7d_vel"] = daily_sales["units_sold"].rolling(7, min_periods=1).mean()

    total_available = sku_inventory["available"].sum()
    daily_sales["doh_estimate"] = daily_sales.apply(
        lambda r: round(total_available / r["rolling_7d_vel"], 1) if r["rolling_7d_vel"] > 0 else 0,
        axis=1
    )

    fig = go.Figure()

    # Shaded danger zone
    fig.add_hrect(y0=0, y1=3, fillcolor="rgba(248,81,73,0.08)", line_width=0, annotation_text="Critical", annotation_position="right")
    fig.add_hrect(y0=3, y1=7, fillcolor="rgba(227,179,65,0.06)", line_width=0, annotation_text="At Risk", annotation_position="right")

    fig.add_trace(go.Scatter(
        x=daily_sales["date"],
        y=daily_sales["doh_estimate"],
        mode="lines",
        line=dict(color="#58a6ff", width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.08)",
        name="DOH (network avg)",
        hovertemplate="<b>%{x}</b><br>DOH: %{y:.1f} days<extra></extra>",
    ))

    # Today marker
    fig.add_vline(x=str(daily_sales["date"].max()), line_dash="dash", line_color="#8b949e", line_width=1)

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=260,
        margin=dict(l=0, r=60, t=10, b=0),
        xaxis=dict(tickfont=dict(color="#8b949e", size=11), gridcolor="#1e2130", showline=False),
        yaxis=dict(tickfont=dict(color="#8b949e", size=11), gridcolor="#1e2130", showline=False, title="Days on Hand"),
        showlegend=False,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── SIZE BREAKDOWN ────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Size Breakdown · Network Totals</div>", unsafe_allow_html=True)

    sku_risk = risk_df[risk_df["sku_id"] == selected_sku_id].copy()
    size_summary = sku_risk.groupby("size").agg(
        total_available=("effective_stock", "sum"),
        avg_velocity=("daily_velocity_7d", "mean"),
        avg_doh=("doh", "mean"),
        critical_count=("risk_severity", lambda x: (x == "critical").sum()),
        is_pivotal=("is_pivotal_size", "first"),
    ).reset_index()
    size_summary["avg_doh_display"] = size_summary["avg_doh"].apply(lambda d: f"{d:.0f}d" if d < 999 else "N/A")

    size_rows = []
    for _, s in size_summary.iterrows():
        doh_val = s["avg_doh"]
        doh_color = "#f85149" if doh_val < 3 else ("#e3b341" if doh_val < 7 else ("#3fb950" if doh_val < 30 else "#8b949e"))
        pivotal_tag = " 🎯" if s["is_pivotal"] else ""
        size_rows.append({
            "Size": f"{s['size']}{pivotal_tag}",
            "Available (Network)": int(s["total_available"]),
            "Avg Velocity (units/day)": f"{s['avg_velocity']:.1f}",
            "Avg DOH": s["avg_doh_display"],
            "Critical Locations": int(s["critical_count"]),
        })

    size_df = pd.DataFrame(size_rows)
    st.dataframe(
        size_df,
        use_container_width=True,
        hide_index=True,
    )

    # Size DOH bar chart
    fig2 = go.Figure()
    colors = ["#f85149" if d < 3 else ("#e3b341" if d < 7 else ("#3fb950" if d < 30 else "#8b949e"))
              for d in size_summary["avg_doh"].clip(upper=60)]
    fig2.add_trace(go.Bar(
        x=size_summary["size"],
        y=size_summary["avg_doh"].clip(upper=60),
        marker_color=colors,
        marker_line_width=0,
        text=size_summary["avg_doh_display"],
        textposition="outside",
        textfont=dict(color="#c9d1d9", size=11),
    ))
    fig2.add_hline(y=7, line_dash="dash", line_color="#e3b341", line_width=1, annotation_text="Warning threshold")
    fig2.add_hline(y=3, line_dash="dash", line_color="#f85149", line_width=1, annotation_text="Critical threshold")
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickfont=dict(color="#8b949e", size=12), showgrid=False),
        yaxis=dict(tickfont=dict(color="#8b949e", size=11), gridcolor="#1e2130", title="Avg DOH (days)"),
        showlegend=False,
        title=dict(text="Average DOH by Size", font=dict(color="#8b949e", size=12)),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── STORE NETWORK TABLE ───────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Store Network · Stock vs Demand</div>", unsafe_allow_html=True)

    store_summary = sku_risk.groupby(["store_id", "store_name", "city", "tier"]).agg(
        total_available=("effective_stock", "sum"),
        total_in_transit=("in_transit", "sum"),
        avg_velocity=("daily_velocity_7d", "mean"),
        avg_doh=("doh", "mean"),
        critical_count=("risk_severity", lambda x: (x == "critical").sum()),
        risk_types=("risk_type", lambda x: list(x.unique())),
    ).reset_index()

    store_summary = store_summary.sort_values("avg_doh")

    for _, s in store_summary.iterrows():
        doh = s["avg_doh"]
        doh_color = "#f85149" if doh < 3 else ("#e3b341" if doh < 7 else ("#3fb950" if doh < 30 else "#8b949e"))
        tier_color = "blue" if s["tier"] == "A" else ("green" if s["tier"] == "B" else "grey")
        risks = [r for r in s["risk_types"] if r != "healthy"]
        risk_pills = " ".join([f'<span class="badge badge-{"red" if r in ("stockout","size_gap") else "amber"}">{r.replace("_"," ")}</span>' for r in risks[:2]])

        col_l, col_m, col_r = st.columns([4, 3, 3])
        with col_l:
            st.markdown(f"""
            <div style="padding:4px 0;">
                <span style="font-size:13px;font-weight:600;color:#f0f6fc;">{s['store_name']}</span>
                <span class="badge badge-{tier_color}" style="margin-left:6px;">Tier {s['tier']}</span>
                <span style="font-size:11px;color:#8b949e;margin-left:6px;">{s['city']}</span>
                <div style="margin-top:4px;">{risk_pills}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_m:
            st.markdown(f"""
            <div style="font-size:12px;color:#8b949e;">Available: <span style="color:#f0f6fc;">{int(s['total_available'])} units</span></div>
            <div style="font-size:12px;color:#8b949e;">In Transit: <span style="color:#58a6ff;">{int(s['total_in_transit'])} units</span></div>
            <div style="font-size:12px;color:#8b949e;">Velocity: <span style="color:#f0f6fc;">{s['avg_velocity']:.1f}/day</span></div>
            """, unsafe_allow_html=True)
        with col_r:
            doh_display = f"{doh:.0f}d" if doh < 999 else "No sales"
            st.markdown(f"""
            <div style="font-size:22px;font-weight:700;color:{doh_color};font-family:'DM Mono',monospace;text-align:right;">{doh_display}</div>
            <div style="font-size:11px;color:#8b949e;text-align:right;">avg days on hand</div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:2px;background:#1e2130;margin:8px 0;'></div>", unsafe_allow_html=True)

    # ── ACTION HISTORY ────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Action History · This Session</div>", unsafe_allow_html=True)

    if actions_df is not None and not actions_df.empty:
        sku_actions = actions_df[actions_df["sku_id"] == selected_sku_id]
        if not sku_actions.empty:
            for _, row in sku_actions.iterrows():
                action_key = f"{row['sku_id']}_{row['size']}_{row['store_id']}"
                status = "✅ Approved" if action_key in st.session_state.approved_actions else (
                    "✗ Rejected" if action_key in st.session_state.rejected_actions else "⏳ Pending"
                )
                status_color = "#3fb950" if "Approved" in status else ("#8b949e" if "Rejected" in status else "#e3b341")
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:8px 12px;border:1px solid #1e2130;border-radius:6px;margin-bottom:6px;">
                    <div style="font-size:12px;color:#c9d1d9;">Size {row['size']} · {row['store_name']} · {row.get('action_detail','—')}</div>
                    <div style="font-size:12px;font-weight:600;color:{status_color};">{status}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px;color:#8b949e;">No actions generated for this SKU.</div>', unsafe_allow_html=True)
