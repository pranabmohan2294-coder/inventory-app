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
