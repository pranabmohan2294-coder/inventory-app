import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

STORES = [
    {"store_id": "S01", "name": "Connaught Place", "city": "Delhi",     "tier": "A", "monthly_revenue": 4200000},
    {"store_id": "S02", "name": "Lajpat Nagar",    "city": "Delhi",     "tier": "B", "monthly_revenue": 2800000},
    {"store_id": "S03", "name": "Linking Road",    "city": "Mumbai",    "tier": "A", "monthly_revenue": 3900000},
    {"store_id": "S04", "name": "FC Road",         "city": "Pune",      "tier": "B", "monthly_revenue": 2100000},
    {"store_id": "S05", "name": "Brigade Road",    "city": "Bangalore", "tier": "A", "monthly_revenue": 3600000},
    {"store_id": "S06", "name": "New Market",      "city": "Kolkata",   "tier": "C", "monthly_revenue": 1400000},
    {"store_id": "S07", "name": "GN Chetty Road",  "city": "Chennai",   "tier": "B", "monthly_revenue": 2300000},
]

WAREHOUSES = [
    {"wh_id": "WH01", "name": "WH-Delhi North",    "city": "Delhi"},
    {"wh_id": "WH02", "name": "WH-Mumbai Central", "city": "Mumbai"},
    {"wh_id": "WH03", "name": "WH-Bangalore",      "city": "Bangalore"},
]

SKUS = [
    {"sku_id": "KU001", "name": "Bandhani Kurta",      "category": "Kurta",   "subcategory": "Ethnic",  "mrp": 1999, "cost": 800},
    {"sku_id": "KU002", "name": "Linen Kurta",         "category": "Kurta",   "subcategory": "Casual",  "mrp": 1499, "cost": 600},
    {"sku_id": "KU003", "name": "Festive Silk Kurta",  "category": "Kurta",   "subcategory": "Festive", "mrp": 3499, "cost": 1400},
    {"sku_id": "KU004", "name": "Cotton Kurta",        "category": "Kurta",   "subcategory": "Casual",  "mrp": 999,  "cost": 400},
    {"sku_id": "TR001", "name": "Slim Fit Trouser",    "category": "Trouser", "subcategory": "Formal",  "mrp": 1799, "cost": 700},
    {"sku_id": "TR002", "name": "Chino Trouser",       "category": "Trouser", "subcategory": "Casual",  "mrp": 1299, "cost": 520},
    {"sku_id": "TR003", "name": "Jogger Pant",         "category": "Trouser", "subcategory": "Casual",  "mrp": 1099, "cost": 440},
    {"sku_id": "SH001", "name": "Oxford Formal Shirt", "category": "Shirt",   "subcategory": "Formal",  "mrp": 1599, "cost": 640},
    {"sku_id": "SH002", "name": "Linen Casual Shirt",  "category": "Shirt",   "subcategory": "Casual",  "mrp": 1299, "cost": 520},
    {"sku_id": "SH003", "name": "Printed Shirt",       "category": "Shirt",   "subcategory": "Casual",  "mrp": 1199, "cost": 480},
    {"sku_id": "ET001", "name": "Sherwani Set",        "category": "Ethnic",  "subcategory": "Wedding", "mrp": 8999, "cost": 3600},
    {"sku_id": "ET002", "name": "Nehru Jacket Set",    "category": "Ethnic",  "subcategory": "Festive", "mrp": 4999, "cost": 2000},
]

SIZES = {
    "Kurta":   ["S", "M", "L", "XL", "XXL"],
    "Trouser": ["30", "32", "34", "36", "38"],
    "Shirt":   ["S", "M", "L", "XL", "XXL"],
    "Ethnic":  ["S", "M", "L", "XL"],
}

PIVOTAL_SIZES = {
    "Kurta":   ["M", "L"],
    "Trouser": ["32", "34"],
    "Shirt":   ["M", "L"],
    "Ethnic":  ["M", "L"],
}

TODAY = datetime.now().date()
HISTORY_DAYS = 30


def store_df():
    return pd.DataFrame(STORES)

def warehouse_df():
    return pd.DataFrame(WAREHOUSES)

def sku_df():
    return pd.DataFrame(SKUS)


def generate_sales_history():
    records = []
    for sku in SKUS:
        sizes = SIZES[sku["category"]]
        for store in STORES:
            tier_mult = {"A": 1.4, "B": 1.0, "C": 0.6}[store["tier"]]
            price_mult = 1.0 if sku["mrp"] < 2000 else (0.6 if sku["mrp"] < 5000 else 0.3)
            base_daily = round(random.uniform(0.5, 3.5) * tier_mult * price_mult, 2)

            for size in sizes:
                pivotal = PIVOTAL_SIZES[sku["category"]]
                size_mult = 1.4 if size in pivotal else (0.5 if size in ["S", "XXL", "38"] else 0.9)
                size_daily = base_daily * size_mult

                for day_offset in range(HISTORY_DAYS):
                    date = TODAY - timedelta(days=HISTORY_DAYS - day_offset)
                    is_weekend = date.weekday() >= 5
                    weekend_mult = 1.35 if is_weekend else 1.0
                    noise = random.uniform(0.7, 1.3)
                    units = max(0, round(size_daily * weekend_mult * noise))

                    if sku["sku_id"] == "KU002" and size == "M" and store["store_id"] == "S01" and day_offset >= 25:
                        units = units * 4

                    records.append({
                        "date": date,
                        "sku_id": sku["sku_id"],
                        "sku_name": sku["name"],
                        "category": sku["category"],
                        "size": size,
                        "store_id": store["store_id"],
                        "store_name": store["name"],
                        "city": store["city"],
                        "units_sold": units,
                        "revenue": units * sku["mrp"],
                    })

    return pd.DataFrame(records)


def generate_inventory():
    records = []
    for sku in SKUS:
        sizes = SIZES[sku["category"]]
        for store in STORES:
            tier_mult = {"A": 1.3, "B": 1.0, "C": 0.7}[store["tier"]]

            for size in sizes:
                pivotal = PIVOTAL_SIZES[sku["category"]]
                is_pivotal = size in pivotal
                base = round(random.uniform(10, 60) * tier_mult)

                if sku["sku_id"] == "KU001" and size == "M" and store["store_id"] == "S02":
                    base = 4
                if sku["sku_id"] == "TR001" and size == "32" and store["store_id"] == "S05":
                    base = 3
                if sku["sku_id"] == "SH001" and size == "L" and store["store_id"] == "S01":
                    base = 5
                if sku["sku_id"] == "ET001" and store["store_id"] == "S06":
                    base = 85
                if sku["sku_id"] == "KU003" and store["store_id"] == "S07":
                    base = 72
                if sku["sku_id"] == "KU002" and size == "M" and store["store_id"] == "S01":
                    base = 6
                if sku["sku_id"] == "KU002" and size == "M" and store["store_id"] == "S04":
                    base = 48
                if sku["sku_id"] == "KU001" and size in ["M", "L"] and store["store_id"] == "S03":
                    base = 5
                if sku["sku_id"] == "KU001" and size in ["XL", "XXL"] and store["store_id"] == "S03":
                    base = 55
                if sku["sku_id"] == "ET002" and store["store_id"] == "S06":
                    base = 34

                reserved = round(base * random.uniform(0.05, 0.20))
                available = max(0, base - reserved)

                in_transit = 0
                in_transit_status = "none"
                in_transit_eta_days = None

                if sku["sku_id"] == "TR001" and size == "32" and store["store_id"] == "S05":
                    in_transit = 20
                    in_transit_status = "confirmed"
                    in_transit_eta_days = 2
                if sku["sku_id"] == "SH001" and size == "L" and store["store_id"] == "S01":
                    in_transit = 15
                    in_transit_status = "unknown"
                    in_transit_eta_days = None

                damaged = round(base * random.uniform(0, 0.05))

                records.append({
                    "sku_id": sku["sku_id"],
                    "sku_name": sku["name"],
                    "category": sku["category"],
                    "size": size,
                    "mrp": sku["mrp"],
                    "cost": sku["cost"],
                    "store_id": store["store_id"],
                    "store_name": store["name"],
                    "city": store["city"],
                    "tier": store["tier"],
                    "total_stock": base,
                    "reserved": reserved,
                    "available": available,
                    "in_transit": in_transit,
                    "in_transit_status": in_transit_status,
                    "in_transit_eta_days": in_transit_eta_days,
                    "damaged": damaged,
                    "is_pivotal_size": is_pivotal,
                })

    wh_records = []
    for sku in SKUS:
        sizes = SIZES[sku["category"]]
        for wh in WAREHOUSES:
            for size in sizes:
                wh_stock = round(random.uniform(30, 150))
                if sku["sku_id"] == "KU001" and size == "M":
                    wh_stock = 120
                if sku["sku_id"] == "SH001" and size == "L":
                    wh_stock = 80
                wh_records.append({
                    "sku_id": sku["sku_id"],
                    "sku_name": sku["name"],
                    "category": sku["category"],
                    "size": size,
                    "wh_id": wh["wh_id"],
                    "wh_name": wh["name"],
                    "wh_city": wh["city"],
                    "wh_stock": wh_stock,
                })

    return pd.DataFrame(records), pd.DataFrame(wh_records)


def generate_returns():
    records = []
    for sku in SKUS:
        sizes = SIZES[sku["category"]]
        for store in STORES:
            for size in sizes:
                normal_returns = round(random.uniform(0, 2))
                if sku["sku_id"] == "KU004" and store["store_id"] == "S03":
                    normal_returns = random.randint(12, 18)
                if normal_returns > 0:
                    records.append({
                        "sku_id": sku["sku_id"],
                        "sku_name": sku["name"],
                        "category": sku["category"],
                        "size": size,
                        "store_id": store["store_id"],
                        "store_name": store["name"],
                        "returns_last_2days": normal_returns,
                        "returns_7day_avg": round(normal_returns * 0.25),
                        "is_spike": (sku["sku_id"] == "KU004" and store["store_id"] == "S03"),
                        "qc_cleared": False if (sku["sku_id"] == "KU004" and store["store_id"] == "S03") else True,
                    })

    return pd.DataFrame(records)


def generate_events():
    return pd.DataFrame([
        {
            "event_id": "EV001",
            "event_name": "Diwali Sale",
            "start_date": TODAY + timedelta(days=12),
            "end_date": TODAY + timedelta(days=17),
            "affected_categories": ["Kurta", "Ethnic"],
            "expected_demand_multiplier": 3.2,
            "stores": ["S01", "S02", "S03", "S04", "S05", "S06", "S07"],
            "confirmed": True,
        },
        {
            "event_id": "EV002",
            "event_name": "Weekend Flash Sale",
            "start_date": TODAY + timedelta(days=3),
            "end_date": TODAY + timedelta(days=4),
            "affected_categories": ["Shirt", "Trouser"],
            "expected_demand_multiplier": 1.8,
            "stores": ["S01", "S03", "S05"],
            "confirmed": True,
        },
    ])


def generate_vendor_info():
    return pd.DataFrame([
        {"vendor_id": "V01", "vendor_name": "Rajesh Textiles",    "category": "Kurta",   "lead_time_days": 5,  "reliability": "high"},
        {"vendor_id": "V02", "vendor_name": "Mumbai Weavers",     "category": "Shirt",   "lead_time_days": 7,  "reliability": "medium"},
        {"vendor_id": "V03", "vendor_name": "Tiruppur Exports",   "category": "Trouser", "lead_time_days": 6,  "reliability": "high"},
        {"vendor_id": "V04", "vendor_name": "Chanderi Handlooms", "category": "Ethnic",  "lead_time_days": 10, "reliability": "low"},
    ])


def load_all_data():
    sales = generate_sales_history()
    inventory, wh_inventory = generate_inventory()
    returns = generate_returns()
    events = generate_events()
    vendors = generate_vendor_info()

    return {
        "stores": store_df(),
        "warehouses": warehouse_df(),
        "skus": sku_df(),
        "sales": sales,
        "inventory": inventory,
        "wh_inventory": wh_inventory,
        "returns": returns,
        "events": events,
        "vendors": vendors,
        "today": TODAY,
    }
