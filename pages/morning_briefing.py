import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

RISK_COLORS = {
    "stockout": "#f85149",
    "stockout_warning": "#e3b341",
    "size_gap": "#f85149",
    "overstock": "#58a6ff",
    "dead_stock": "#8b949e",
    "velocity_anomaly": "#bc8cff",
    "returns_spike": "#e3b341",
    "data_gap": "#8b949e",
    "healthy": "#3fb950",
}

ACTION_LABELS = {
    "transfer_store": "Transfer",
    "replenish": "Replenish",
    "markdown": "Markdown",
    "wait": "Wait",
    "investigate": "Investigate",
    "hold_qc": "QC Hold",
    "monitor": "Monitor",
}


def render(data):
    summary      = data["summary"]
    actions_df   = data["actions_df"]
    store_health = data["store_health"]
    risk_df      = data["risk_df"]
    events       = data["events"]
    today        = data["today"]

    # ── PAGE HEADER ────────────────────────────────────────────────────────────
    from datetime import datetime
    day_str = datetime.now().strftime("%A, %d %B %Y")

    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;">
        <div>
            <div class="page-title">Good morning 👋</div>
            <div class="page-subtitle">{day_str} · Here's what needs your attention today</div>
        </div>
        <div style="text-align:right;font-size:11px;color:#8b949e;">
            7 stores · 12 SKUs · {summary['total_sku_locations']} SKU-locations tracked
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── EVENT BANNERS ──────────────────────────────────────────────────────────
    for _, ev in events.iterrows():
        days_away = (ev["start_date"] - today).days
        if 0 <= days_away <= 14:
            cats = ", ".join(ev["affected_categories"])
            urgency_cls = "red" if days_away <= 3 else ""
            st.markdown(f"""
            <div class="alert-banner {urgency_cls}">
                🎯 <strong>{ev['event_name']}</strong> starts in {days_away} days —
                {cats} demand expected {ev['expected_demand_multiplier']}x normal.
                Pre-position stock now.
            </div>
            """, unsafe_allow_html=True)

    # Anomaly banners
    anomaly_skus = risk_df[risk_df["velocity_anomaly"] == True]
    if not anomaly_skus.empty:
        sku_list = anomaly_skus["sku_name"].unique()[:3]
        st.markdown(f"""
        <div class="alert-banner">
            📈 Velocity spike on <strong>{", ".join(sku_list)}</strong> — unusual demand detected.
            Confirm if a sale event is running.
        </div>
        """, unsafe_allow_html=True)

    # ── KPI CARDS ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card red">
            <div class="kpi-label">🔴 Critical Stockouts</div>
            <div class="kpi-value">{summary['stockout_critical_count']}</div>
            <div class="kpi-sub">+{summary['stockout_warning_count']} at warning level</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        ov_cr = f"₹{summary['overstock_value']/100000:.1f}L"
        st.markdown(f"""
        <div class="kpi-card blue">
            <div class="kpi-label">📦 Overstock Value</div>
            <div class="kpi-value">{ov_cr}</div>
            <div class="kpi-sub">{summary['overstock_count']} SKU-locations idle</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        health_color = "#f85149" if summary['network_health_pct'] < 60 else ("#e3b341" if summary['network_health_pct'] < 80 else "#3fb950")
        st.markdown(f"""
        <div class="kpi-card green">
            <div class="kpi-label">💚 Network Health</div>
            <div class="kpi-value" style="color:{health_color};">{summary['network_health_pct']}%</div>
            <div class="kpi-sub">SKUs in healthy DOH range</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card amber">
            <div class="kpi-label">⚡ Actions Needed</div>
            <div class="kpi-value">{summary['critical_actions']}</div>
            <div class="kpi-sub">{summary['pending_actions']} total · {summary['data_gap_count']} data gaps</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── TOP ACTIONS + STORE HEALTH SPLIT ──────────────────────────────────────
    left_col, right_col = st.columns([6, 4], gap="large")

    with left_col:
        st.markdown("<div class='section-header'>Top 5 Actions · Approve Right Here</div>", unsafe_allow_html=True)

        if actions_df is not None and not actions_df.empty:
            top5 = actions_df.head(5)

            for idx, row in top5.iterrows():
                action_key = f"{row['sku_id']}_{row['size']}_{row['store_id']}"
                is_approved = action_key in st.session_state.approved_actions
                is_rejected = action_key in st.session_state.rejected_actions

                sev = row.get("risk_severity", "warning")
                sev_class = "critical" if sev == "critical" else "warning"

                risk_badge = {
                    "stockout": '<span class="badge badge-red">Stockout</span>',
                    "stockout_warning": '<span class="badge badge-amber">At Risk</span>',
                    "size_gap": '<span class="badge badge-red">Size Gap</span>',
                    "overstock": '<span class="badge badge-blue">Overstock</span>',
                    "dead_stock": '<span class="badge badge-grey">Dead Stock</span>',
                    "velocity_anomaly": '<span class="badge badge-blue">Velocity Spike</span>',
                    "returns_spike": '<span class="badge badge-amber">Returns Spike</span>',
                    "data_gap": '<span class="badge badge-grey">Data Gap</span>',
                }.get(row["risk_type"], "")

                conf_badge = {
                    "high": '<span class="badge badge-green">High Confidence</span>',
                    "medium": '<span class="badge badge-amber">Medium Confidence</span>',
                    "low": '<span class="badge badge-grey">Low Confidence</span>',
                }.get(row.get("confidence", "medium"), "")

                prevented = f"₹{row.get('prevented_loss', 0):,.0f}" if row.get("prevented_loss", 0) > 0 else "—"
                action_label = ACTION_LABELS.get(row.get("recommended_action", ""), row.get("recommended_action", ""))

                status_indicator = ""
                if is_approved:
                    status_indicator = '<span style="color:#3fb950;font-size:12px;font-weight:600;">✓ Approved</span>'
                elif is_rejected:
                    status_indicator = '<span style="color:#8b949e;font-size:12px;">✗ Rejected</span>'

                st.markdown(f"""
                <div class="action-card {sev_class}">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                        <div>
                            <span style="font-size:14px;font-weight:600;color:#f0f6fc;">{row['sku_name']}</span>
                            <span style="font-size:12px;color:#8b949e;margin-left:8px;">Size {row['size']} · {row['store_name']}</span>
                        </div>
                        <div style="display:flex;gap:6px;align-items:center;">
                            {risk_badge} {conf_badge} {status_indicator}
                        </div>
                    </div>
                    <div style="font-size:13px;color:#c9d1d9;margin-bottom:8px;">
                        <strong style="color:#58a6ff;">{action_label}:</strong> {row.get('action_detail', '—')}
                        <span style="color:#8b949e;margin-left:12px;">DOH: {row.get('current_doh', '—')}d</span>
                        <span style="color:#3fb950;margin-left:12px;">Save: {prevented}</span>
                    </div>
                    <div style="font-size:11px;color:#8b949e;">{row.get('reason', '')}</div>
                </div>
                """, unsafe_allow_html=True)

                if not is_approved and not is_rejected:
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 6])
                    with btn_col1:
                        if st.button("✓ Approve", key=f"approve_brief_{action_key}", type="primary"):
                            st.session_state.approved_actions.add(action_key)
                            st.rerun()
                    with btn_col2:
                        if st.button("✗ Reject", key=f"reject_brief_{action_key}"):
                            st.session_state.rejected_actions.add(action_key)
                            st.rerun()

            if len(actions_df) > 5:
                st.markdown(f"""
                <div style="text-align:center;padding:12px;color:#8b949e;font-size:12px;border:1px dashed #1e2130;border-radius:8px;margin-top:8px;">
                    +{len(actions_df) - 5} more actions in the Action Feed →
                </div>
                """, unsafe_allow_html=True)

    with right_col:
        st.markdown("<div class='section-header'>Store Health Overview</div>", unsafe_allow_html=True)

        for _, store in store_health.iterrows():
            pct = store["health_pct"]
            bar_color = "#f85149" if pct < 50 else ("#e3b341" if pct < 75 else "#3fb950")
            tier_badge = f'<span class="badge badge-{"blue" if store["tier"]=="A" else ("green" if store["tier"]=="B" else "grey")}">Tier {store["tier"]}</span>'

            st.markdown(f"""
            <div style="margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <div>
                        <span style="font-size:13px;font-weight:600;color:#f0f6fc;">{store['store_name']}</span>
                        <span style="font-size:11px;color:#8b949e;margin-left:6px;">{store['city']}</span>
                        {tier_badge}
                    </div>
                    <div style="font-size:12px;font-weight:600;color:{bar_color};font-family:'DM Mono',monospace;">{pct}%</div>
                </div>
                <div style="background:#1e2130;border-radius:4px;height:6px;overflow:hidden;">
                    <div style="background:{bar_color};height:100%;width:{pct}%;border-radius:4px;transition:width 0.3s;"></div>
                </div>
                <div style="display:flex;gap:12px;margin-top:4px;font-size:11px;color:#8b949e;">
                    <span style="color:#f85149;">🔴 {store['critical_count']} critical</span>
                    <span style="color:#e3b341;">🟡 {store['warning_count']} warning</span>
                    <span style="color:#3fb950;">✓ {store['healthy_count']} healthy</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── DOH DISTRIBUTION CHART ─────────────────────────────────────────────────
    st.markdown("<div class='section-header'>DOH Distribution Across Network</div>", unsafe_allow_html=True)

    risk_df_clean = risk_df[risk_df["doh"] < 200].copy()
    risk_df_clean["doh_bucket"] = pd.cut(
        risk_df_clean["doh"],
        bins=[0, 3, 7, 15, 30, 60, 200],
        labels=["Critical (0–3d)", "At Risk (3–7d)", "Watch (7–15d)", "Healthy (15–30d)", "Surplus (30–60d)", "Overstock (60d+)"]
    )
    dist = risk_df_clean.groupby("doh_bucket", observed=True).size().reset_index(name="count")

    colors_map = {
        "Critical (0–3d)": "#f85149",
        "At Risk (3–7d)": "#e3b341",
        "Watch (7–15d)": "#bc8cff",
        "Healthy (15–30d)": "#3fb950",
        "Surplus (30–60d)": "#58a6ff",
        "Overstock (60d+)": "#8b949e",
    }

    fig = go.Figure(go.Bar(
        x=dist["doh_bucket"].astype(str),
        y=dist["count"],
        marker_color=[colors_map.get(str(b), "#8b949e") for b in dist["doh_bucket"]],
        marker_line_width=0,
        text=dist["count"],
        textposition="outside",
        textfont=dict(color="#c9d1d9", size=11, family="DM Mono"),
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(
            tickfont=dict(color="#8b949e", size=11, family="DM Sans"),
            gridcolor="rgba(0,0,0,0)",
            showline=False,
        ),
        yaxis=dict(
            tickfont=dict(color="#8b949e", size=11),
            gridcolor="#1e2130",
            showline=False,
            title=None,
        ),
        bargap=0.3,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── WINS PANEL ─────────────────────────────────────────────────────────────
    approved_count = len(st.session_state.approved_actions)
    if approved_count > 0:
        st.markdown("<div class='section-header'>Today's Wins</div>", unsafe_allow_html=True)
        approved_actions = actions_df[
            actions_df.apply(lambda r: f"{r['sku_id']}_{r['size']}_{r['store_id']}" in st.session_state.approved_actions, axis=1)
        ]
        total_prevented = approved_actions["prevented_loss"].sum()
        st.markdown(f"""
        <div style="display:flex;gap:16px;">
            <div class="kpi-card green" style="flex:1;">
                <div class="kpi-label">Actions Approved</div>
                <div class="kpi-value">{approved_count}</div>
            </div>
            <div class="kpi-card green" style="flex:1;">
                <div class="kpi-label">Revenue Protected</div>
                <div class="kpi-value" style="font-size:24px;">₹{total_prevented/1000:.0f}K</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
