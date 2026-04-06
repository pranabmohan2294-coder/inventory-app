import streamlit as st
import pandas as pd

def show(signals, returns, transit):
    st.markdown("""
    <div class="ginesys-header">
        <div><h1>📡 Signals & Alerts</h1>
        <span>Anomaly detection · Returns spikes · Data gaps</span></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔥 Velocity Anomalies", "🔶 Returns Spikes", "⚠️ Data Gaps"])

    with tab1:
        anomalies = signals[signals["velocity_anomaly"] == True].copy()
        if anomalies.empty:
            st.success("No velocity anomalies detected.")
        else:
            st.markdown(f"**{len(anomalies)} SKU×Store combinations showing unusual demand spike**")
            for _, row in anomalies.iterrows():
                ratio = row.get("velocity_ratio", 0)
                st.markdown(f"""
                <div class="action-card">
                    <b style="color:#FFD700">{row['sku_name']}</b> · Size {row['size']} · {row['store_name']}<br>
                    <small style="color:#8A9BC0">
                        Velocity jumped <b style="color:#F26522">{ratio:.1f}x</b> vs prior 7-day baseline ·
                        Current: {row['velocity_7d']:.1f}/day vs Prior: {row['velocity_prior7d']:.1f}/day
                    </small><br>
                    <small style="color:#8A9BC0">💡 Check for unplanned sale event, markdown, or viral demand. Confirm before pre-positioning stock.</small>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.button("✅ Confirm Event", key=f"ev_{row['sku_id']}_{row['size']}_{row['store_id']}")

    with tab2:
        spikes = returns[returns["spike"] == True].copy()
        if spikes.empty:
            st.success("No returns spikes detected.")
        else:
            st.markdown(f"**{len(spikes)} locations with unusual returns volume**")
            for _, row in spikes.iterrows():
                st.markdown(f"""
                <div class="action-card" style="border-left-color:#FF6600">
                    <b style="color:#FF6600">{row['sku_name']}</b> · Size {row['size']} · Store {row['store_id']}<br>
                    <small style="color:#8A9BC0">
                        <b style="color:#FF4444">{row['returns_last_7d']}</b> returns in last 7d ·
                        Avg baseline: {row['avg_daily_returns']:.1f}/day
                    </small><br>
                    <small style="color:#8A9BC0">⚠️ Available stock may be overstated until QC confirms units are resaleable.</small>
                </div>
                """, unsafe_allow_html=True)

    with tab3:
        gaps = transit[transit["status"] == "Unknown"].copy()
        if gaps.empty:
            st.success("All shipments have confirmed status.")
        else:
            st.markdown(f"**{len(gaps)} shipments with unknown tracking status**")
            for _, row in gaps.iterrows():
                st.markdown(f"""
                <div class="action-card" style="border-left-color:#FFCC00">
                    <b style="color:#FFCC00">Shipment {row['shipment_id']}</b> · {row['sku_id']} Size {row['size']}<br>
                    <small style="color:#8A9BC0">
                        To: {row['to_name']} · Qty: {row['quantity']} units · ETA: {row['eta_days']}d
                    </small><br>
                    <small style="color:#8A9BC0">⚠️ Status unknown — recommendations for this route may be inaccurate. Contact logistics to confirm.</small>
                </div>
                """, unsafe_allow_html=True)

def render(data):
    show(data)
