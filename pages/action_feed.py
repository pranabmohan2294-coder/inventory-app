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
