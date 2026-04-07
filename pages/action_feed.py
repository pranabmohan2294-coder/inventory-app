import streamlit as st
import pandas as pd

ACTION_LABELS = {
    "transfer_store": "🔄 Transfer",
    "replenish": "📦 Replenish",
    "markdown": "🏷️ Markdown",
    "wait": "⏳ Wait",
    "investigate": "🔎 Investigate",
    "hold_qc": "🔒 QC Hold",
    "monitor": "👁️ Monitor",
}

RISK_LABELS = {
    "stockout": "Stockout",
    "stockout_warning": "At Risk",
    "size_gap": "Size Gap",
    "overstock": "Overstock",
    "dead_stock": "Dead Stock",
    "velocity_anomaly": "Velocity Spike",
    "returns_spike": "Returns Spike",
    "data_gap": "Data Gap",
}


def render(data):
    actions_df = data["actions_df"]
    summary    = data["summary"]

    st.markdown("""
    <div class="page-title">Action Feed</div>
    <div class="page-subtitle">All prioritised recommendations · Approve, modify or reject</div>
    """, unsafe_allow_html=True)

    if actions_df is None or actions_df.empty:
        st.info("No actions generated. Network looks healthy!")
        return

    # ── STATS ROW ─────────────────────────────────────────────────────────────
    total    = len(actions_df)
    critical = len(actions_df[actions_df["risk_severity"] == "critical"])
    approved = len(st.session_state.approved_actions)
    rejected = len(st.session_state.rejected_actions)
    pending  = total - approved - rejected

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Total Actions", total, "#64748B"),
        (c2, "Critical", critical, "#DC2626"),
        (c3, "Approved", approved, "#16A34A"),
        (c4, "Pending", pending, "#F47920"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="padding:14px 18px;">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value" style="font-size:26px;color:{color};">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── FILTERS ───────────────────────────────────────────────────────────────
    filt_col1, filt_col2, filt_col3, filt_col4 = st.columns([2, 2, 2, 2])

    with filt_col1:
        risk_opts = ["All"] + sorted(actions_df["risk_type"].unique().tolist())
        risk_filter = st.selectbox("Risk Type", risk_opts, key="af_risk")
    with filt_col2:
        store_opts = ["All"] + sorted(actions_df["store_name"].unique().tolist())
        store_filter = st.selectbox("Store", store_opts, key="af_store")
    with filt_col3:
        cat_opts = ["All"] + sorted(actions_df["category"].unique().tolist())
        cat_filter = st.selectbox("Category", cat_opts, key="af_cat")
    with filt_col4:
        status_filter = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"], key="af_status")

    # Apply filters
    df = actions_df.copy()
    if risk_filter != "All":
        df = df[df["risk_type"] == risk_filter]
    if store_filter != "All":
        df = df[df["store_name"] == store_filter]
    if cat_filter != "All":
        df = df[df["category"] == cat_filter]

    if status_filter == "Pending":
        df = df[df.apply(lambda r: f"{r['sku_id']}_{r['size']}_{r['store_id']}" not in st.session_state.approved_actions
                         and f"{r['sku_id']}_{r['size']}_{r['store_id']}" not in st.session_state.rejected_actions, axis=1)]
    elif status_filter == "Approved":
        df = df[df.apply(lambda r: f"{r['sku_id']}_{r['size']}_{r['store_id']}" in st.session_state.approved_actions, axis=1)]
    elif status_filter == "Rejected":
        df = df[df.apply(lambda r: f"{r['sku_id']}_{r['size']}_{r['store_id']}" in st.session_state.rejected_actions, axis=1)]

    st.markdown(f"<div style='font-size:12px;color:#64748B;margin:12px 0 8px 0;'>{len(df)} actions shown</div>", unsafe_allow_html=True)

    # ── ACTION CARDS ──────────────────────────────────────────────────────────
    for idx, row in df.iterrows():
        action_key = f"{row['sku_id']}_{row['size']}_{row['store_id']}"
        is_approved = action_key in st.session_state.approved_actions
        is_rejected = action_key in st.session_state.rejected_actions

        sev = row.get("risk_severity", "warning")
        border_color = "#DC2626" if sev == "critical" else "#F47920"
        if is_approved:
            border_color = "#16A34A"
        elif is_rejected:
            border_color = "#94A3B8"

        risk_label = RISK_LABELS.get(row["risk_type"], row["risk_type"])
        action_label = ACTION_LABELS.get(row.get("recommended_action", ""), row.get("recommended_action", ""))

        conf = row.get("confidence", "medium")
        conf_color = {"high": "#16A34A", "medium": "#F47920", "low": "#DC2626"}.get(conf, "#64748B")
        conf_label = {"high": "High", "medium": "Med", "low": "Low"}.get(conf, conf)

        prevented = f"₹{row.get('prevented_loss', 0):,.0f}" if row.get("prevented_loss", 0) > 0 else "—"
        cost = f"₹{row.get('logistics_cost', 0):,.0f}" if row.get("logistics_cost", 0) > 0 else "₹0"
        eta = f"{row.get('eta_days', '—')}d" if row.get("eta_days") is not None else "—"

        event_tag = ' <span class="badge badge-amber">Event</span>' if row.get("event_imminent") else ""

        with st.expander(
            f"#{row.get('action_rank', idx+1)}  {row['sku_name']} · {row['size']} · {row['store_name']}  |  {risk_label}  →  {action_label}",
            expanded=False
        ):
            st.markdown(f"""
            <div style="border-left:3px solid {border_color};padding-left:16px;">
            """, unsafe_allow_html=True)

            # Detail grid
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"""
                <div style="font-size:11px;color:#64748B;margin-bottom:2px;">FROM → TO</div>
                <div style="font-size:13px;color:#1B2B5E;font-weight:600;">
                    {row.get('from_location', '—')} → {row.get('to_location', '—')}
                </div>
                <div style="font-size:11px;color:#64748B;margin-top:8px;">Quantity</div>
                <div style="font-size:13px;color:#1B2B5E;">{row.get('transfer_qty', 0)} units · {row.get('mode', '—')} · ETA {eta}</div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div style="font-size:11px;color:#64748B;margin-bottom:2px;">FINANCIALS</div>
                <div style="font-size:13px;color:#16A34A;font-weight:600;">Save: {prevented}</div>
                <div style="font-size:11px;color:#64748B;margin-top:4px;">Cost: {cost}</div>
                <div style="font-size:11px;color:#64748B;">DOH: {row.get('current_doh', '—')}d current</div>
                """, unsafe_allow_html=True)
            with col_c:
                st.markdown(f"""
                <div style="font-size:11px;color:#64748B;margin-bottom:2px;">SIGNALS</div>
                <div style="font-size:12px;color:{conf_color};font-weight:600;">Confidence: {conf_label}</div>
                <div style="font-size:11px;color:#64748B;margin-top:4px;">Priority: {row.get('priority_score', 0):.0f}/100</div>
                <div style="font-size:11px;color:#64748B;">Velocity: {row.get('daily_velocity', 0):.1f} units/day</div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:#F4F6FB;border-radius:6px;padding:10px 14px;margin:12px 0;font-size:12px;color:#475569;border:1px solid #E2E8F0;">
                💡 <strong>Why:</strong> {row.get('reason', '—')}
            </div>
            """, unsafe_allow_html=True)

            # Transfer vs Markdown comparison for overstock
            if row.get("recommended_action") == "markdown" and row.get("effective_stock", 0) > 0:
                st.markdown(f"""
                <div style="background:#F4F6FB;border-radius:6px;padding:12px;margin-bottom:12px;border:1px solid #E2E8F0;">
                    <div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;">Markdown vs Hold Comparison</div>
                    <div style="display:flex;gap:24px;font-size:12px;">
                        <div>
                            <div style="color:#F47920;font-weight:600;">30% Markdown Now</div>
                            <div style="color:#64748B;margin-top:4px;">Revenue: ₹{row.get('effective_stock',0) * row.get('mrp',0) * 0.7:,.0f}</div>
                            <div style="color:#DC2626;">Loss: ₹{row.get('markdown_loss',0):,.0f}</div>
                        </div>
                        <div>
                            <div style="color:#DC2626;font-weight:600;">Hold (risk)</div>
                            <div style="color:#64748B;margin-top:4px;">Capital tied: ₹{row.get('effective_stock',0) * row.get('mrp',0):,.0f}</div>
                            <div style="color:#DC2626;">Aging cost grows daily</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Action buttons
            if is_approved:
                st.success("✅ Approved — action logged")
                if st.button("↩ Undo", key=f"undo_{action_key}_{idx}"):
                    st.session_state.approved_actions.discard(action_key)
                    st.rerun()
            elif is_rejected:
                st.warning("✗ Rejected")
                if st.button("↩ Undo", key=f"undo_rej_{action_key}_{idx}"):
                    st.session_state.rejected_actions.discard(action_key)
                    st.rerun()
            else:
                btn1, btn2, btn3 = st.columns([1.5, 1.5, 6])
                with btn1:
                    if st.button("✓ Approve", key=f"approve_{action_key}_{idx}", type="primary"):
                        st.session_state.approved_actions.add(action_key)
                        st.rerun()
                with btn2:
                    if st.button("✗ Reject", key=f"reject_{action_key}_{idx}"):
                        st.session_state.rejected_actions.add(action_key)
                        st.rerun()
