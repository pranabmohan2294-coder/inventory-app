import streamlit as st
import pandas as pd
from datetime import datetime


def render(data):
    risk_df  = data["risk_df"]
    returns  = data["returns"]
    events   = data["events"]
    today    = data["today"]
    summary  = data["summary"]

    st.markdown("""
    <div class="page-title">Signals & Alerts</div>
    <div class="page-subtitle">Live anomaly feed · Returns spikes · Data gaps · Event flags</div>
    """, unsafe_allow_html=True)

    # ── SIGNAL SUMMARY PILLS ──────────────────────────────────────────────────
    anomaly_count  = summary["anomaly_count"]
    returns_count  = summary["returns_spike_count"]
    data_gap_count = summary["data_gap_count"]

    st.markdown(f"""
    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;">
        <div style="background:rgba(188,140,255,0.1);border:1px solid rgba(188,140,255,0.3);border-radius:8px;padding:10px 18px;">
            <span style="font-size:20px;font-weight:700;color:#7C3AED;font-family:'DM Mono',monospace;">{anomaly_count}</span>
            <span style="font-size:12px;color:#64748B;margin-left:8px;">Velocity Anomalies</span>
        </div>
        <div style="background:rgba(227,179,65,0.1);border:1px solid rgba(227,179,65,0.3);border-radius:8px;padding:10px 18px;">
            <span style="font-size:20px;font-weight:700;color:#F47920;font-family:'DM Mono',monospace;">{returns_count}</span>
            <span style="font-size:12px;color:#64748B;margin-left:8px;">Returns Spikes</span>
        </div>
        <div style="background:rgba(139,148,158,0.1);border:1px solid rgba(139,148,158,0.3);border-radius:8px;padding:10px 18px;">
            <span style="font-size:20px;font-weight:700;color:#64748B;font-family:'DM Mono',monospace;">{data_gap_count}</span>
            <span style="font-size:12px;color:#64748B;margin-left:8px;">Data Gaps</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── VELOCITY ANOMALIES ────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📈 Velocity Anomalies</div>", unsafe_allow_html=True)

    anomalies = risk_df[risk_df["velocity_anomaly"] == True].copy()
    if anomalies.empty:
        st.markdown('<div style="font-size:13px;color:#64748B;padding:12px 0;">No velocity anomalies detected.</div>', unsafe_allow_html=True)
    else:
        for _, row in anomalies.drop_duplicates(["sku_id", "store_id"]).iterrows():
            flag_key = f"flag_{row['sku_id']}_{row['store_id']}"
            is_flagged = st.session_state.event_flags.get(flag_key, False)

            ratio = row.get("velocity_ratio", 1)
            ratio_color = "#DC2626" if ratio > 3 else "#F47920"

            st.markdown(f"""
            <div class="action-card warning" style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <span style="font-size:14px;font-weight:600;color:#1B2B5E;">{row['sku_name']}</span>
                        <span style="font-size:12px;color:#64748B;margin-left:8px;">Size {row['size']} · {row['store_name']}</span>
                    </div>
                    <div>
                        <span style="font-size:22px;font-weight:700;color:{ratio_color};font-family:'DM Mono',monospace;">{ratio:.1f}x</span>
                        <span style="font-size:11px;color:#64748B;"> vs baseline</span>
                    </div>
                </div>
                <div style="display:flex;gap:24px;margin-top:8px;font-size:12px;">
                    <div>
                        <div style="color:#64748B;">7-day velocity</div>
                        <div style="color:#1B2B5E;font-weight:600;">{row.get('daily_velocity_7d', 0):.1f} units/day</div>
                    </div>
                    <div>
                        <div style="color:#64748B;">30-day baseline</div>
                        <div style="color:#1B2B5E;font-weight:600;">{row.get('daily_velocity_30d', 0):.1f} units/day</div>
                    </div>
                    <div>
                        <div style="color:#64748B;">Current DOH</div>
                        <div style="color:#F47920;font-weight:600;">{row.get('doh', '—')}d</div>
                    </div>
                    <div>
                        <div style="color:#64748B;">Event imminent?</div>
                        <div style="color:{'#16A34A' if row.get('event_imminent') else '#64748B'};font-weight:600;">{"Yes" if row.get('event_imminent') else "No"}</div>
                    </div>
                </div>
                {"<div style='margin-top:8px;font-size:11px;color:#16A34A;'>✓ Flagged as event-driven</div>" if is_flagged else ""}
            </div>
            """, unsafe_allow_html=True)

            if not is_flagged:
                c1, c2, _ = st.columns([1.5, 2, 6])
                with c1:
                    if st.button("🎯 Flag as Event", key=f"flag_ev_{flag_key}"):
                        st.session_state.event_flags[flag_key] = True
                        st.rerun()
                with c2:
                    if st.button("✗ Dismiss", key=f"dismiss_{flag_key}"):
                        st.session_state.event_flags[flag_key] = "dismissed"
                        st.rerun()

    # ── RETURNS SPIKES ────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📦 Returns Spikes</div>", unsafe_allow_html=True)

    spikes = returns[returns["is_spike"] == True].copy()
    if spikes.empty:
        st.markdown('<div style="font-size:13px;color:#64748B;padding:12px 0;">No returns spikes detected.</div>', unsafe_allow_html=True)
    else:
        spike_summary = spikes.groupby(["sku_id", "sku_name", "store_id", "store_name"]).agg(
            total_returns=("returns_last_2days", "sum"),
            avg_baseline=("returns_7day_avg", "mean"),
        ).reset_index()

        for _, row in spike_summary.iterrows():
            ratio = row["total_returns"] / max(row["avg_baseline"], 0.1)
            st.markdown(f"""
            <div class="action-card warning" style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <span style="font-size:14px;font-weight:600;color:#1B2B5E;">{row['sku_name']}</span>
                        <span style="font-size:12px;color:#64748B;margin-left:8px;">{row['store_name']}</span>
                        <span class="badge badge-amber" style="margin-left:8px;">Returns Spike</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:22px;font-weight:700;color:#F47920;font-family:'DM Mono',monospace;">{int(row['total_returns'])}</span>
                        <span style="font-size:11px;color:#64748B;"> units returned</span>
                    </div>
                </div>
                <div style="display:flex;gap:24px;margin-top:10px;font-size:12px;">
                    <div>
                        <div style="color:#64748B;">Last 2 days</div>
                        <div style="color:#F47920;font-weight:600;">{int(row['total_returns'])} units</div>
                    </div>
                    <div>
                        <div style="color:#64748B;">7-day avg</div>
                        <div style="color:#1B2B5E;font-weight:600;">{row['avg_baseline']:.1f} units</div>
                    </div>
                    <div>
                        <div style="color:#64748B;">Spike ratio</div>
                        <div style="color:#DC2626;font-weight:600;">{ratio:.1f}x</div>
                    </div>
                </div>
                <div style="background:rgba(227,179,65,0.08);border-radius:6px;padding:8px 12px;margin-top:10px;font-size:12px;color:#F47920;">
                    ⚠️ Stock overstated until QC cleared. Recommend holding {int(row['total_returns'])} units from available count.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── DATA GAPS ─────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>⚠️ Data Gaps · In-Transit Tracking</div>", unsafe_allow_html=True)

    data_gaps = risk_df[risk_df["risk_type"] == "data_gap"].drop_duplicates(["sku_id", "size", "store_id"])
    if data_gaps.empty:
        st.markdown('<div style="font-size:13px;color:#64748B;padding:12px 0;">All in-transit shipments have confirmed tracking.</div>', unsafe_allow_html=True)
    else:
        for _, row in data_gaps.iterrows():
            st.markdown(f"""
            <div class="action-card" style="border-left:3px solid #64748B;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <span style="font-size:14px;font-weight:600;color:#1B2B5E;">{row['sku_name']}</span>
                        <span style="font-size:12px;color:#64748B;margin-left:8px;">Size {row['size']} · {row['store_name']}</span>
                        <span class="badge badge-grey" style="margin-left:8px;">Data Gap</span>
                    </div>
                    <div>
                        <span style="font-size:22px;font-weight:700;color:#64748B;font-family:'DM Mono',monospace;">{int(row['in_transit'])}</span>
                        <span style="font-size:11px;color:#64748B;"> units untracked</span>
                    </div>
                </div>
                <div style="font-size:12px;color:#64748B;margin-top:8px;">
                    In-transit status: <span style="color:#DC2626;">Unknown</span> ·
                    ETA: Unknown ·
                    DOH (excluding in-transit): <span style="color:#F47920;">{row.get('doh','—')}d</span>
                </div>
                <div style="background:rgba(139,148,158,0.08);border-radius:6px;padding:8px 12px;margin-top:8px;font-size:12px;color:#64748B;">
                    🔎 Confirm shipment status before executing replenishment — may result in double-stocking.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── UPCOMING EVENTS ───────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>📅 Upcoming Events · Demand Impact</div>", unsafe_allow_html=True)

    for _, ev in events.iterrows():
        days_away = (ev["start_date"] - today).days
        urgency_color = "#DC2626" if days_away <= 3 else ("#F47920" if days_away <= 7 else "#2563EB")
        cats = ", ".join(ev["affected_categories"])
        stores_count = len(ev["stores"])

        st.markdown(f"""
        <div class="action-card" style="border-left:3px solid {urgency_color};margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <span style="font-size:14px;font-weight:600;color:#1B2B5E;">{ev['event_name']}</span>
                    <span class="badge badge-{"red" if days_away <= 3 else "amber"}" style="margin-left:8px;">
                        In {days_away} days
                    </span>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:22px;font-weight:700;color:{urgency_color};font-family:'DM Mono',monospace;">{ev['expected_demand_multiplier']}x</div>
                    <div style="font-size:11px;color:#64748B;">demand multiplier</div>
                </div>
            </div>
            <div style="display:flex;gap:24px;margin-top:10px;font-size:12px;">
                <div>
                    <div style="color:#64748B;">Start Date</div>
                    <div style="color:#1B2B5E;font-weight:600;">{ev['start_date'].strftime('%d %b %Y')}</div>
                </div>
                <div>
                    <div style="color:#64748B;">Affected Categories</div>
                    <div style="color:#1B2B5E;font-weight:600;">{cats}</div>
                </div>
                <div>
                    <div style="color:#64748B;">Stores Affected</div>
                    <div style="color:#1B2B5E;font-weight:600;">{stores_count} stores</div>
                </div>
                <div>
                    <div style="color:#64748B;">Status</div>
                    <div style="color:#16A34A;font-weight:600;">{"Confirmed" if ev['confirmed'] else "Tentative"}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
