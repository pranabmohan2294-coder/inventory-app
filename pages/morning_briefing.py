import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render(data):
    summary      = data["summary"]
    actions_df   = data["actions_df"]
    store_health = data["store_health"]
    risk_df      = data["risk_df"]
    events       = data["events"]
    today        = data["today"]
    from datetime import datetime
    day_str = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;">
        <div><div class="page-title">Good morning 👋</div>
        <div class="page-subtitle">{day_str} · Here's what needs your attention today</div></div>
        <div style="text-align:right;font-size:11px;color:#64748B;">7 stores · 12 SKUs · {summary['total_sku_locations']} SKU-locations tracked</div>
    </div>""", unsafe_allow_html=True)
    for _, ev in events.iterrows():
        days_away = (ev["start_date"] - today).days
        if 0 <= days_away <= 14:
            cats = ", ".join(ev["affected_categories"])
            cls = "red" if days_away <= 3 else ""
            st.markdown(f'<div class="alert-banner {cls}">🎯 <strong>{ev["event_name"]}</strong> in {days_away} days — {cats} demand {ev["expected_demand_multiplier"]}x normal. Pre-position stock now.</div>', unsafe_allow_html=True)
    anomaly_skus = risk_df[risk_df["velocity_anomaly"] == True]
    if not anomaly_skus.empty:
        sku_list = anomaly_skus["sku_name"].unique()[:3]
        st.markdown(f'<div class="alert-banner">📈 Velocity spike on <strong>{", ".join(sku_list)}</strong> — confirm if a sale event is running.</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-card red"><div class="kpi-label">🔴 Critical Stockouts</div><div class="kpi-value">{summary["stockout_critical_count"]}</div><div class="kpi-sub">+{summary["stockout_warning_count"]} at warning</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card blue"><div class="kpi-label">📦 Overstock Value</div><div class="kpi-value">₹{summary["overstock_value"]/100000:.1f}L</div><div class="kpi-sub">{summary["overstock_count"]} SKU-locations idle</div></div>', unsafe_allow_html=True)
    with col3:
        hc = "#DC2626" if summary["network_health_pct"] < 60 else ("#F47920" if summary["network_health_pct"] < 80 else "#16A34A")
        st.markdown(f'<div class="kpi-card green"><div class="kpi-label">💚 Network Health</div><div class="kpi-value" style="color:{hc};">{summary["network_health_pct"]}%</div><div class="kpi-sub">SKUs in healthy DOH range</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card amber"><div class="kpi-label">⚡ Actions Needed</div><div class="kpi-value">{summary["critical_actions"]}</div><div class="kpi-sub">{summary["pending_actions"]} total · {summary["data_gap_count"]} data gaps</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    left_col, right_col = st.columns([6, 4], gap="large")
    with left_col:
        st.markdown("<div class='section-header'>Top 5 Actions · Approve Right Here</div>", unsafe_allow_html=True)
        if actions_df is not None and not actions_df.empty:
            for idx, row in actions_df.head(5).iterrows():
                action_key = f"{row['sku_id']}_{row['size']}_{row['store_id']}"
                is_approved = action_key in st.session_state.approved_actions
                is_rejected = action_key in st.session_state.rejected_actions
                sev_class = "critical" if row.get("risk_severity") == "critical" else "warning"
                prevented = f"₹{row.get('prevented_loss', 0):,.0f}" if row.get("prevented_loss", 0) > 0 else "—"
                status = '<span style="color:#16A34A;font-weight:600;">✓ Approved</span>' if is_approved else ('<span style="color:#64748B;">✗ Rejected</span>' if is_rejected else "")
                st.markdown(f"""<div class="action-card {sev_class}">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                        <span style="font-size:14px;font-weight:700;color:#1B2B5E;">{row['sku_name']} · Size {row['size']} · {row['store_name']}</span>{status}
                    </div>
                    <div style="font-size:13px;color:#475569;"><strong>{str(row.get('recommended_action','—')).replace('_',' ').title()}:</strong> {row.get('action_detail','—')} <span style="color:#16A34A;margin-left:12px;">Save: {prevented}</span></div>
                    <div style="font-size:11px;color:#64748B;margin-top:4px;">DOH: {row.get('current_doh','—')}d · Priority: {row.get('priority_score',0):.0f}/100</div>
                </div>""", unsafe_allow_html=True)
                if not is_approved and not is_rejected:
                    b1, b2, _ = st.columns([1,1,6])
                    with b1:
                        if st.button("✓ Approve", key=f"mb_approve_{action_key}", type="primary"):
                            st.session_state.approved_actions.add(action_key); st.rerun()
                    with b2:
                        if st.button("✗ Reject", key=f"mb_reject_{action_key}"):
                            st.session_state.rejected_actions.add(action_key); st.rerun()
            if len(actions_df) > 5:
                st.markdown(f'<div style="text-align:center;padding:10px;color:#64748B;font-size:12px;border:1px dashed #CBD5E1;border-radius:8px;">+{len(actions_df)-5} more in Action Feed →</div>', unsafe_allow_html=True)
    with right_col:
        st.markdown("<div class='section-header'>Store Health Overview</div>", unsafe_allow_html=True)
        for _, store in store_health.iterrows():
            pct = store["health_pct"]
            bc = "#DC2626" if pct < 50 else ("#F47920" if pct < 75 else "#16A34A")
            tc = "blue" if store["tier"]=="A" else ("green" if store["tier"]=="B" else "grey")
            st.markdown(f"""<div style="margin-bottom:14px;background:#FFFFFF;padding:10px 14px;border-radius:8px;border:1px solid #E2E8F0;">
                <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                    <div><span style="font-size:13px;font-weight:700;color:#1B2B5E;">{store['store_name']}</span>
                    <span class="badge badge-{tc}" style="margin-left:6px;">Tier {store['tier']}</span></div>
                    <span style="font-size:14px;font-weight:700;color:{bc};">{pct}%</span>
                </div>
                <div style="background:#F1F5F9;border-radius:4px;height:6px;overflow:hidden;">
                    <div style="background:{bc};height:100%;width:{pct}%;border-radius:4px;"></div>
                </div>
                <div style="font-size:11px;margin-top:4px;color:#64748B;">🔴 {store['critical_count']} · 🟠 {store['warning_count']} · ✓ {store['healthy_count']}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>DOH Distribution Across Network</div>", unsafe_allow_html=True)
    rdf = risk_df[risk_df["doh"] < 200].copy()
    rdf["bucket"] = pd.cut(rdf["doh"], bins=[0,3,7,15,30,60,200], labels=["Critical (0–3d)","At Risk (3–7d)","Watch (7–15d)","Healthy (15–30d)","Surplus (30–60d)","Overstock (60d+)"])
    dist = rdf.groupby("bucket", observed=True).size().reset_index(name="count")
    cmap = {"Critical (0–3d)":"#DC2626","At Risk (3–7d)":"#F47920","Watch (7–15d)":"#7C3AED","Healthy (15–30d)":"#16A34A","Surplus (30–60d)":"#2563EB","Overstock (60d+)":"#94A3B8"}
    fig = go.Figure(go.Bar(x=dist["bucket"].astype(str), y=dist["count"], marker_color=[cmap.get(str(b),"#94A3B8") for b in dist["bucket"]], text=dist["count"], textposition="outside"))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=0,r=0,t=10,b=0), showlegend=False, xaxis=dict(tickfont=dict(color="#64748B",size=10)), yaxis=dict(gridcolor="#F1F5F9"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    approved_count = len(st.session_state.approved_actions)
    if approved_count > 0 and actions_df is not None and not actions_df.empty:
        st.markdown("<div class='section-header'>Today's Wins</div>", unsafe_allow_html=True)
        approved_df = actions_df[actions_df.apply(lambda r: f"{r['sku_id']}_{r['size']}_{r['store_id']}" in st.session_state.approved_actions, axis=1)]
        total_prevented = approved_df["prevented_loss"].sum()
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="kpi-card green"><div class="kpi-label">Actions Approved</div><div class="kpi-value">{approved_count}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card green"><div class="kpi-label">Revenue Protected</div><div class="kpi-value" style="font-size:24px;">₹{total_prevented/1000:.0f}K</div></div>', unsafe_allow_html=True)
