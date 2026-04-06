import pandas as pd
import numpy as np
from datetime import timedelta

DOH_STOCKOUT_CRITICAL = 3
DOH_STOCKOUT_WARNING  = 7
DOH_OVERSTOCK         = 30
DEAD_STOCK_DAYS       = 21
VELOCITY_SPIKE_MULT   = 2.0
RETURNS_SPIKE_MULT    = 2.5
TRANSFER_MIN_QTY      = 10
LOGISTICS_COST_PER_UNIT_EXPRESS = 45
LOGISTICS_COST_PER_UNIT_SURFACE = 18


def compute_velocity(sales: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    cutoff = sales["date"].max() - timedelta(days=days)
    recent = sales[sales["date"] >= cutoff]
    vel = (
        recent.groupby(["sku_id", "size", "store_id"])["units_sold"]
        .sum()
        .reset_index()
        .rename(columns={"units_sold": f"velocity_{days}d"})
    )
    vel[f"daily_velocity_{days}d"] = (vel[f"velocity_{days}d"] / days).round(2)
    return vel


def compute_baseline_velocity(sales: pd.DataFrame) -> pd.DataFrame:
    base = (
        sales.groupby(["sku_id", "size", "store_id"])["units_sold"]
        .sum()
        .reset_index()
        .rename(columns={"units_sold": "velocity_30d"})
    )
    base["daily_velocity_30d"] = (base["velocity_30d"] / 30).round(2)
    return base


def compute_last_sale_date(sales: pd.DataFrame) -> pd.DataFrame:
    last = (
        sales[sales["units_sold"] > 0]
        .groupby(["sku_id", "size", "store_id"])["date"]
        .max()
        .reset_index()
        .rename(columns={"date": "last_sale_date"})
    )
    return last


def compute_doh(inventory: pd.DataFrame, velocity_7d: pd.DataFrame) -> pd.DataFrame:
    df = inventory.merge(velocity_7d, on=["sku_id", "size", "store_id"], how="left")
    df["daily_velocity_7d"] = df["daily_velocity_7d"].fillna(0)
    df["effective_stock"] = (df["available"] - df["reserved"]).clip(lower=0)
    df["confirmed_in_transit"] = df.apply(
        lambda r: r["in_transit"] if r["in_transit_status"] == "confirmed" else 0, axis=1
    )
    df["doh"] = df.apply(
        lambda r: round(r["effective_stock"] / r["daily_velocity_7d"], 1)
        if r["daily_velocity_7d"] > 0 else 999,
        axis=1
    )
    df["doh_adjusted"] = df.apply(
        lambda r: round((r["effective_stock"] + r["confirmed_in_transit"]) / r["daily_velocity_7d"], 1)
        if r["daily_velocity_7d"] > 0 else 999,
        axis=1
    )
    return df


def classify_risks(doh_df, sales, returns, events, today):
    df = doh_df.copy()
    last_sale = compute_last_sale_date(sales)
    df = df.merge(last_sale, on=["sku_id", "size", "store_id"], how="left")
    df["days_since_last_sale"] = (
        pd.Timestamp(today) - pd.to_datetime(df["last_sale_date"])
    ).dt.days.fillna(999).astype(int)

    base_vel = compute_baseline_velocity(sales)
    df = df.merge(
        base_vel[["sku_id", "size", "store_id", "daily_velocity_30d"]],
        on=["sku_id", "size", "store_id"], how="left"
    )
    df["daily_velocity_30d"] = df["daily_velocity_30d"].fillna(0)
    df["velocity_ratio"] = df.apply(
        lambda r: round(r["daily_velocity_7d"] / r["daily_velocity_30d"], 2)
        if r["daily_velocity_30d"] > 0 else 1.0,
        axis=1
    )
    df["velocity_anomaly"] = df["velocity_ratio"] >= VELOCITY_SPIKE_MULT

    returns_spike = returns[returns["is_spike"]][["sku_id", "store_id", "returns_last_2days", "returns_7day_avg", "is_spike"]].drop_duplicates(["sku_id", "store_id"])
    df = df.merge(returns_spike, on=["sku_id", "store_id"], how="left")
    df["is_spike"] = df["is_spike"].fillna(False)
    df["returns_last_2days"] = df["returns_last_2days"].fillna(0)

    upcoming_event_skus = set()
    for _, ev in events.iterrows():
        days_to_event = (ev["start_date"] - today).days
        if 0 <= days_to_event <= 14:
            upcoming_event_skus.add(tuple(ev["affected_categories"]))
    df["event_imminent"] = df["category"].apply(
        lambda c: any(c in cats for cats in upcoming_event_skus)
    )

    def assign_risk(row):
        risks = []
        if row["in_transit"] > 0 and row["in_transit_status"] == "unknown":
            risks.append(("data_gap", "warning", 40))
        if row["is_spike"]:
            risks.append(("returns_spike", "warning", 35))
        if row["days_since_last_sale"] >= DEAD_STOCK_DAYS and row["effective_stock"] > 5:
            risks.append(("dead_stock", "critical", 50))
        if row["doh"] > DOH_OVERSTOCK and row["daily_velocity_7d"] < 0.3:
            risks.append(("overstock", "warning", 45))
        if row["doh_adjusted"] <= DOH_STOCKOUT_CRITICAL and row["daily_velocity_7d"] > 0:
            urgency = 100 - (row["doh_adjusted"] * 10)
            if row["event_imminent"]:
                urgency += 20
            risks.append(("stockout", "critical", min(urgency, 100)))
        elif row["doh_adjusted"] <= DOH_STOCKOUT_WARNING and row["daily_velocity_7d"] > 0:
            risks.append(("stockout_warning", "warning", 70 - row["doh_adjusted"] * 5))
        if row["is_pivotal_size"] and row["doh"] <= DOH_STOCKOUT_WARNING and row["daily_velocity_7d"] > 0:
            risks.append(("size_gap", "critical", 80))
        if row["velocity_anomaly"] and row["doh"] > DOH_STOCKOUT_CRITICAL:
            risks.append(("velocity_anomaly", "warning", 55))
        if not risks:
            return ("healthy", "healthy", 0)
        risks.sort(key=lambda x: x[2], reverse=True)
        return risks[0]

    risk_result = df.apply(assign_risk, axis=1)
    df["risk_type"]     = risk_result.apply(lambda x: x[0])
    df["risk_severity"] = risk_result.apply(lambda x: x[1])
    df["risk_score"]    = risk_result.apply(lambda x: x[2])
    return df


def generate_actions(risk_df, wh_inventory, events, today):
    at_risk = risk_df[risk_df["risk_type"] != "healthy"].copy()
    actions = []

    overstock_pool = risk_df[
        (risk_df["risk_type"] == "overstock") | (risk_df["doh"] > 25)
    ][["sku_id", "size", "store_id", "store_name", "available", "doh"]].copy()

    def get_wh_stock(sku_id, size):
        wh = wh_inventory[(wh_inventory["sku_id"] == sku_id) & (wh_inventory["size"] == size)]
        if wh.empty:
            return 0, "Unknown WH", "Unknown"
        best = wh.sort_values("wh_stock", ascending=False).iloc[0]
        return best["wh_stock"], best["wh_name"], best["wh_id"]

    for _, row in at_risk.iterrows():
        action = {
            "sku_id": row["sku_id"],
            "sku_name": row["sku_name"],
            "category": row["category"],
            "size": row["size"],
            "store_id": row["store_id"],
            "store_name": row["store_name"],
            "city": row["city"],
            "tier": row["tier"],
            "risk_type": row["risk_type"],
            "risk_severity": row["risk_severity"],
            "risk_score": row["risk_score"],
            "current_doh": row["doh"],
            "adjusted_doh": row["doh_adjusted"],
            "daily_velocity": row["daily_velocity_7d"],
            "effective_stock": row["effective_stock"],
            "in_transit": row["in_transit"],
            "in_transit_status": row["in_transit_status"],
            "in_transit_eta": row["in_transit_eta_days"],
            "event_imminent": row["event_imminent"],
            "velocity_anomaly": row["velocity_anomaly"],
            "mrp": row["mrp"],
            "days_since_last_sale": row.get("days_since_last_sale", 0),
            "returns_last_2days": row.get("returns_last_2days", 0),
            "transfer_vs_markdown": None,
            "markdown_loss": 0,
        }

        if row["risk_type"] in ("stockout", "stockout_warning", "size_gap"):
            if row["in_transit"] > 0 and row["in_transit_status"] == "confirmed" and row.get("in_transit_eta_days") and row["in_transit_eta_days"] <= 2:
                action.update({
                    "recommended_action": "wait",
                    "action_detail": f"Confirmed in-transit of {row['in_transit']} units arriving in {row['in_transit_eta_days']} days",
                    "from_location": "In Transit",
                    "to_location": row["store_name"],
                    "transfer_qty": row["in_transit"],
                    "mode": "—",
                    "eta_days": row["in_transit_eta_days"],
                    "logistics_cost": 0,
                    "prevented_loss": round(row["daily_velocity_7d"] * row["mrp"] * 3),
                    "confidence": "high",
                    "reason": "In-transit stock arriving soon — no immediate action needed",
                })
                actions.append(action)
                continue

            excess_stores = overstock_pool[
                (overstock_pool["sku_id"] == row["sku_id"]) &
                (overstock_pool["size"] == row["size"]) &
                (overstock_pool["store_id"] != row["store_id"]) &
                (overstock_pool["available"] >= TRANSFER_MIN_QTY)
            ]

            if not excess_stores.empty:
                source = excess_stores.sort_values("available", ascending=False).iloc[0]
                transfer_qty = min(int(source["available"] * 0.4), 60)
                mode = "express" if row["doh"] <= DOH_STOCKOUT_CRITICAL else "surface"
                cost_per = LOGISTICS_COST_PER_UNIT_EXPRESS if mode == "express" else LOGISTICS_COST_PER_UNIT_SURFACE
                logistics_cost = transfer_qty * cost_per
                prevented_loss = round(row["daily_velocity_7d"] * row["mrp"] * max(DOH_STOCKOUT_WARNING - row["doh"], 3))
                action.update({
                    "recommended_action": "transfer_store",
                    "action_detail": f"Transfer {transfer_qty} units from {source['store_name']}",
                    "from_location": source["store_name"],
                    "to_location": row["store_name"],
                    "transfer_qty": transfer_qty,
                    "mode": mode,
                    "eta_days": 1 if mode == "express" else 3,
                    "logistics_cost": logistics_cost,
                    "prevented_loss": prevented_loss,
                    "confidence": "high",
                    "reason": f"Excess stock at {source['store_name']} (DOH {source['doh']:.0f}d) vs shortage here",
                })
                actions.append(action)
                continue

            wh_stock, wh_name, wh_id = get_wh_stock(row["sku_id"], row["size"])
            if wh_stock >= TRANSFER_MIN_QTY:
                replenish_qty = min(int(row["daily_velocity_7d"] * 14), wh_stock, 80)
                mode = "express" if row["doh"] <= DOH_STOCKOUT_CRITICAL else "surface"
                cost_per = LOGISTICS_COST_PER_UNIT_EXPRESS if mode == "express" else LOGISTICS_COST_PER_UNIT_SURFACE
                logistics_cost = replenish_qty * cost_per
                prevented_loss = round(row["daily_velocity_7d"] * row["mrp"] * max(DOH_STOCKOUT_WARNING - row["doh"], 3))
                confidence = "medium" if row["in_transit_status"] == "unknown" else "high"
                action.update({
                    "recommended_action": "replenish",
                    "action_detail": f"Replenish {replenish_qty} units from {wh_name}",
                    "from_location": wh_name,
                    "to_location": row["store_name"],
                    "transfer_qty": replenish_qty,
                    "mode": mode,
                    "eta_days": 2 if mode == "express" else 5,
                    "logistics_cost": logistics_cost,
                    "prevented_loss": prevented_loss,
                    "confidence": confidence,
                    "reason": f"DOH is {row['doh']} days — replenish before stockout" + (" (note: in-transit tracking unconfirmed)" if row["in_transit_status"] == "unknown" else ""),
                })
                actions.append(action)
                continue

        if row["risk_type"] in ("overstock", "dead_stock"):
            markdown_loss = round(row["effective_stock"] * row["mrp"] * 0.3)
            capital_tied = round(row["effective_stock"] * row["cost"])
            action.update({
                "recommended_action": "markdown",
                "action_detail": f"Mark down {row['effective_stock']} units by 30%",
                "from_location": row["store_name"],
                "to_location": "—",
                "transfer_qty": row["effective_stock"],
                "mode": "—",
                "eta_days": 0,
                "logistics_cost": 0,
                "prevented_loss": capital_tied,
                "markdown_loss": markdown_loss,
                "confidence": "high",
                "reason": (
                    f"Dead stock — no sales for {row.get('days_since_last_sale', 0)} days"
                    if row["risk_type"] == "dead_stock"
                    else f"DOH is {row['doh']:.0f} days — stock not moving"
                ),
            })
            actions.append(action)
            continue

        if row["risk_type"] == "data_gap":
            action.update({
                "recommended_action": "investigate",
                "action_detail": f"Confirm in-transit status for {row['in_transit']} units",
                "from_location": "In Transit (untracked)",
                "to_location": row["store_name"],
                "transfer_qty": row["in_transit"],
                "mode": "—",
                "eta_days": None,
                "logistics_cost": 0,
                "prevented_loss": 0,
                "confidence": "low",
                "reason": "In-transit tracking status unknown — confirm before replenishing",
            })
            actions.append(action)
            continue

        if row["risk_type"] == "returns_spike":
            action.update({
                "recommended_action": "hold_qc",
                "action_detail": f"Hold {int(row['returns_last_2days'])} returned units for QC",
                "from_location": row["store_name"],
                "to_location": "QC Hold",
                "transfer_qty": int(row["returns_last_2days"]),
                "mode": "—",
                "eta_days": 0,
                "logistics_cost": 0,
                "prevented_loss": 0,
                "confidence": "high",
                "reason": f"Returns spike: {int(row['returns_last_2days'])} units in 2 days vs avg {int(row.get('returns_7day_avg', 0))}",
            })
            actions.append(action)
            continue

        if row["risk_type"] == "velocity_anomaly":
            action.update({
                "recommended_action": "monitor",
                "action_detail": "Demand spiking — confirm if event is driving this",
                "from_location": "—",
                "to_location": row["store_name"],
                "transfer_qty": 0,
                "mode": "—",
                "eta_days": None,
                "logistics_cost": 0,
                "prevented_loss": 0,
                "confidence": "medium",
                "reason": f"Velocity {row['velocity_ratio']:.1f}x above baseline — potential event or trend",
            })
            actions.append(action)

    if not actions:
        return pd.DataFrame()

    actions_df = pd.DataFrame(actions)

    tier_weight = {"A": 1.0, "B": 0.7, "C": 0.4}
    actions_df["tier_weight"] = actions_df["tier"].map(tier_weight).fillna(0.5)
    actions_df["urgency_score"] = actions_df["current_doh"].apply(
        lambda d: max(0, min(100, 100 - d * 10)) if d < 999 else 0
    )
    max_prevented = actions_df["prevented_loss"].max() if actions_df["prevented_loss"].max() > 0 else 1
    actions_df["revenue_score"] = (actions_df["prevented_loss"] / max_prevented * 100).fillna(0)
    actions_df["priority_score"] = (
        actions_df["revenue_score"]   * 0.40 +
        actions_df["urgency_score"]   * 0.40 +
        actions_df["tier_weight"]     * 100 * 0.20
    ).round(1)
    actions_df.loc[actions_df["event_imminent"] == True, "priority_score"] += 15
    actions_df = actions_df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    actions_df["action_rank"] = actions_df.index + 1

    return actions_df


def compute_network_summary(risk_df, actions_df):
    total_skus = len(risk_df)
    stockout_critical = risk_df[risk_df["risk_type"] == "stockout"]
    stockout_warning  = risk_df[risk_df["risk_type"] == "stockout_warning"]
    overstock         = risk_df[risk_df["risk_type"].isin(["overstock", "dead_stock"])]
    anomalies         = risk_df[risk_df["velocity_anomaly"] == True]
    data_gaps         = risk_df[risk_df["risk_type"] == "data_gap"]
    returns_spikes    = risk_df[risk_df["is_spike"] == True]

    overstock_value = int((overstock["effective_stock"] * overstock["mrp"]).sum())
    capital_at_risk = int((stockout_critical["effective_stock"] * stockout_critical["mrp"]).sum())
    healthy_pct = round((len(risk_df[risk_df["risk_type"] == "healthy"]) / total_skus) * 100, 1)
    pending_actions = len(actions_df) if actions_df is not None and not actions_df.empty else 0
    critical_actions = len(actions_df[actions_df["risk_severity"] == "critical"]) if pending_actions > 0 else 0

    return {
        "total_sku_locations": total_skus,
        "stockout_critical_count": len(stockout_critical),
        "stockout_warning_count": len(stockout_warning),
        "overstock_count": len(overstock),
        "overstock_value": overstock_value,
        "anomaly_count": len(anomalies),
        "data_gap_count": len(data_gaps),
        "returns_spike_count": len(returns_spikes),
        "network_health_pct": healthy_pct,
        "capital_at_risk": capital_at_risk,
        "pending_actions": pending_actions,
        "critical_actions": critical_actions,
    }


def compute_store_health(risk_df):
    rows = []
    for store_id, grp in risk_df.groupby("store_id"):
        total = len(grp)
        critical = len(grp[grp["risk_severity"] == "critical"])
        warning  = len(grp[grp["risk_severity"] == "warning"])
        healthy  = len(grp[grp["risk_type"] == "healthy"])
        health_pct = round(healthy / total * 100) if total > 0 else 0
        status = "critical" if critical >= 3 else ("warning" if warning >= 3 else "healthy")
        rows.append({
            "store_id": store_id,
            "store_name": grp["store_name"].iloc[0],
            "city": grp["city"].iloc[0],
            "tier": grp["tier"].iloc[0],
            "total_skus": total,
            "critical_count": critical,
            "warning_count": warning,
            "healthy_count": healthy,
            "health_pct": health_pct,
            "status": status,
        })
    return pd.DataFrame(rows).sort_values("health_pct")


def run_engine(data):
    sales     = data["sales"]
    inventory = data["inventory"]
    wh_inv    = data["wh_inventory"]
    returns   = data["returns"]
    events    = data["events"]
    today     = data["today"]

    velocity_7d  = compute_velocity(sales, days=7)
    doh_df       = compute_doh(inventory, velocity_7d)
    risk_df      = classify_risks(doh_df, sales, returns, events, today)
    actions_df   = generate_actions(risk_df, wh_inv, events, today)
    summary      = compute_network_summary(risk_df, actions_df)
    store_health = compute_store_health(risk_df)

    return {
        **data,
        "velocity_7d":  velocity_7d,
        "risk_df":      risk_df,
        "actions_df":   actions_df,
        "summary":      summary,
        "store_health": store_health,
    }
