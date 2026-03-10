"""
IMA-Sales-Analytics — Synthetic Data Generator
Generates 2 years of realistic grocery store data.
Run this from the root of your project:
    python generate_synthetic_data.py
"""

import sqlite3
import pandas as pd
import numpy as np
import random
import os
from datetime import date, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
START_DATE  = date(2023, 1, 1)
END_DATE    = date(2024, 12, 31)
DB_FILE     = "database/inventory.db"
DATA_DIR    = "data"
os.makedirs(DATA_DIR, exist_ok=True)

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ── 1. PRODUCT CATALOGUE ──────────────────────────────────────────────────────
products_raw = [
    # (product_id, name, brand, category, cost, sell, shelf_months)
    (1,  "Tam Yağlı Süt 1L",        "Sek",       "Süt Ürünleri",  6.50,  10.90, 1),
    (2,  "Yarım Yağlı Süt 1L",      "İçim",      "Süt Ürünleri",  6.00,  10.50, 1),
    (3,  "Kaşar Peyniri 400g",       "Pınar",     "Süt Ürünleri", 38.00,  59.90, 3),
    (4,  "Beyaz Peynir 500g",        "Sütaş",     "Süt Ürünleri", 32.00,  52.90, 3),
    (5,  "Yoğurt 1kg",               "Danone",    "Süt Ürünleri",  9.50,  16.90, 1),
    (6,  "Tereyağı 250g",            "Tariş",     "Süt Ürünleri", 22.00,  36.90, 2),
    (7,  "Ekmek",                    "Unlu",      "Unlu Mamul",    3.50,   6.50, 0),
    (8,  "Tost Ekmeği",              "Uno",       "Unlu Mamul",    8.00,  14.90, 0),
    (9,  "Simit",                    "Simit Sarayı","Unlu Mamul",  2.00,   4.00, 0),
    (10, "Makarna 500g",             "Barilla",   "Bakliyat",      8.50,  14.90,12),
    (11, "Pirinç 1kg",               "Baldo",     "Bakliyat",     14.00,  22.90,12),
    (12, "Nohut 1kg",                "Ülker",     "Bakliyat",     12.00,  19.90,12),
    (13, "Kırmızı Mercimek 1kg",     "Paket",     "Bakliyat",     10.50,  17.90,12),
    (14, "Zeytinyağı 1L",            "Tariş",     "Yağlar",       55.00,  89.90,18),
    (15, "Ayçiçek Yağı 1L",         "Yudum",     "Yağlar",       28.00,  45.90,12),
    (16, "Ketçap 300g",              "Tamek",     "Soslar",       12.00,  19.90, 9),
    (17, "Mayonez 250g",             "Hellmann's","Soslar",       15.00,  24.90, 6),
    (18, "Domates Salçası 700g",     "Tukaş",     "Soslar",       18.00,  29.90,12),
    (19, "Cola 1L",                  "Coca-Cola", "İçecekler",     8.00,  14.90, 9),
    (20, "Ayran 200ml",              "Sütaş",     "İçecekler",     3.50,   6.50, 1),
    (21, "Meyve Suyu 1L",            "Cappy",     "İçecekler",    14.00,  22.90, 9),
    (22, "Su 1.5L",                  "Erikli",    "İçecekler",     3.00,   5.50,24),
    (23, "Çay 500g",                 "Çaykur",    "Kuru Gıda",    28.00,  45.90,18),
    (24, "Kahve 200g",               "Nescafé",   "Kuru Gıda",    45.00,  72.90,12),
    (25, "Şeker 1kg",                "Torku",     "Kuru Gıda",    16.00,  26.90,18),
    (26, "Tuz 750g",                 "Pınar",     "Kuru Gıda",     4.00,   7.90,24),
    (27, "Un 1kg",                   "Güllüoğlu","Kuru Gıda",      9.00,  15.90,12),
    (28, "Çikolata 100g",            "Ülker",     "Atıştırmalık", 10.00,  16.90, 9),
    (29, "Cips 100g",                "Lay's",     "Atıştırmalık",  8.50,  14.90, 6),
    (30, "Bisküvi 200g",             "Eti",       "Atıştırmalık",  7.00,  12.90, 9),
    (31, "Domates (kg)",             "Taze",      "Sebze/Meyve",   8.00,  14.90, 0),
    (32, "Salatalık (kg)",           "Taze",      "Sebze/Meyve",   6.00,  10.90, 0),
    (33, "Patates (kg)",             "Taze",      "Sebze/Meyve",   7.00,  12.90, 1),
    (34, "Soğan (kg)",               "Taze",      "Sebze/Meyve",   5.00,   8.90, 2),
    (35, "Muz (kg)",                 "Taze",      "Sebze/Meyve",  18.00,  29.90, 0),
    (36, "Elma (kg)",                "Taze",      "Sebze/Meyve",  12.00,  19.90, 1),
    (37, "Portakal (kg)",            "Taze",      "Sebze/Meyve",  10.00,  16.90, 1),
    (38, "Tavuk Göğsü (kg)",         "Banvit",    "Et/Şarküteri", 68.00, 109.90, 0),
    (39, "Sucuk 200g",               "İnci",      "Et/Şarküteri", 28.00,  44.90, 2),
    (40, "Salam 200g",               "Banvit",    "Et/Şarküteri", 22.00,  36.90, 2),
    (41, "Yumurta (10'lu)",          "Aytaç",     "Yumurta",      18.00,  29.90, 1),
    (42, "Deterjan 3kg",             "Omo",       "Temizlik",     65.00, 104.90,18),
    (43, "Bulaşık Deterjanı 750ml",  "Fairy",     "Temizlik",     28.00,  44.90,18),
    (44, "Tuvalet Kağıdı 24'lü",     "Selpak",    "Temizlik",     72.00, 114.90,24),
    (45, "Şampuan 400ml",            "Head&Shoulders","Kişisel Bakım",38.00,59.90,18),
]

def make_expiry(shelf_months: int, ref_date: date) -> str:
    if shelf_months == 0:
        return (ref_date + timedelta(days=random.randint(1, 5))).isoformat()
    return (ref_date + timedelta(days=shelf_months * 30)).isoformat()

records = []
for p in products_raw:
    pid, name, brand, cat, cost, sell, shelf = p
    records.append({
        "product_id":    pid,
        "product_name":  name,
        "brand":         brand,
        "category":      cat,
        "cost_price":    cost,
        "selling_price": sell,
        "expiry_date":   make_expiry(shelf, date(2025, 6, 1)),
        "discount_price":  round(sell * random.uniform(0.80, 0.90), 2) if random.random() < 0.3 else None,
        "discount_until":  date(2025, random.randint(1,12), random.randint(1,28)).isoformat() if random.random() < 0.3 else None,
    })

df_products = pd.DataFrame(records)


# ── 2. SALES DATA ─────────────────────────────────────────────────────────────
# Base daily demand per product (units/day on a typical weekday)
base_demand = {
    1: 15, 2: 12, 3: 8,  4: 9,  5: 14, 6: 6,
    7: 40, 8: 18, 9: 25, 10: 7, 11: 6, 12: 5, 13: 5,
    14: 4, 15: 8, 16: 6, 17: 5, 18: 7,
    19: 12, 20: 20, 21: 8, 22: 25,
    23: 8, 24: 5, 25: 9, 26: 5, 27: 4,
    28: 10, 29: 12, 30: 11,
    31: 18, 32: 14, 33: 12, 34: 10, 35: 9, 36: 8, 37: 7,
    38: 7,  39: 6,  40: 5,
    41: 20, 42: 3, 43: 4, 44: 3, 45: 2,
}

# Category seasonality multipliers by month (1=Jan … 12=Dec)
season_map = {
    "İçecekler":      [0.7,0.7,0.8,0.9,1.1,1.4,1.8,1.9,1.5,1.0,0.8,0.7],
    "Sebze/Meyve":    [0.8,0.8,0.9,1.1,1.2,1.3,1.4,1.3,1.1,1.0,0.9,0.8],
    "Süt Ürünleri":   [1.1,1.0,1.0,1.0,0.9,0.9,0.8,0.8,0.9,1.0,1.1,1.2],
    "Kuru Gıda":      [1.2,1.1,1.0,1.0,0.9,0.9,0.8,0.8,0.9,1.0,1.1,1.3],
    "Atıştırmalık":   [0.9,0.9,0.9,1.0,1.0,1.1,1.3,1.3,1.1,1.0,1.0,1.2],
    "Temizlik":       [1.2,1.0,1.3,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.1],
    "DEFAULT":        [1.0]*12,
}

def get_season(cat, month):
    return season_map.get(cat, season_map["DEFAULT"])[month - 1]

# Ramadan boost (approximate): 2023-Mar23–Apr21, 2024-Mar11–Apr09
def ramadan_mult(d: date) -> float:
    ranges = [
        (date(2023, 3, 23), date(2023, 4, 21)),
        (date(2024, 3, 11), date(2024, 4,  9)),
    ]
    for s, e in ranges:
        if s <= d <= e:
            return 1.35
    return 1.0

cat_lookup = {p["product_id"]: p["category"] for p in records}

sales_rows = []
sale_id = 1
current = START_DATE
while current <= END_DATE:
    dow = current.weekday()          # 0=Mon … 6=Sun
    weekend_mult = 1.35 if dow >= 5 else 1.0
    ram = ramadan_mult(current)
    # Slight long-term growth trend
    days_elapsed = (current - START_DATE).days
    trend = 1.0 + (days_elapsed / 730) * 0.20   # +20% over 2 years

    for pid, base in base_demand.items():
        cat = cat_lookup[pid]
        s_mult = get_season(cat, current.month)
        mu = base * s_mult * weekend_mult * ram * trend
        qty = max(0, int(np.random.poisson(mu)))
        if qty > 0:
            sales_rows.append({
                "id":            sale_id,
                "date":          current.isoformat(),
                "product_id":    pid,
                "quantity_sold": qty,
            })
            sale_id += 1
    current += timedelta(days=1)

df_sales = pd.DataFrame(sales_rows)


# ── 3. STOCK TRANSACTIONS ────────────────────────────────────────────────────
# Restock every ~7 days per product, quantity = ~14 days of expected demand
stock_rows = []
txn_id = 1
for pid, base in base_demand.items():
    cat = cat_lookup[pid]
    current = START_DATE
    while current <= END_DATE:
        s_mult = get_season(cat, current.month)
        restock_qty = int(base * s_mult * 14 * random.uniform(0.85, 1.15))
        shelf = next(p[6] for p in products_raw if p[0] == pid)
        exp = make_expiry(shelf, current)
        stock_rows.append({
            "transaction_id": txn_id,
            "product_id":     pid,
            "date":           current.isoformat(),
            "quantity":       restock_qty,
            "note":           "Stok girişi",
            "expiry_date":    exp,
        })
        txn_id += 1
        current += timedelta(days=random.randint(6, 9))

df_stock = pd.DataFrame(stock_rows)


# ── 4. WRITE TO DB ────────────────────────────────────────────────────────────
os.makedirs("database", exist_ok=True)
conn = sqlite3.connect(DB_FILE)

# Products
conn.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    cost_price REAL,
    selling_price REAL,
    expiry_date TEXT,
    discount_price REAL,
    discount_until TEXT
)""")

# Sales
conn.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    product_id INTEGER,
    quantity_sold INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)""")

# Stock transactions
conn.execute("DROP TABLE IF EXISTS stock_transactions")
conn.execute("""
CREATE TABLE stock_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    date TEXT,
    quantity INTEGER,
    note TEXT,
    expiry_date TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)""")

df_products.to_sql("products",          conn, if_exists="replace", index=False)
df_sales.to_sql(   "sales",             conn, if_exists="replace", index=False)
df_stock.to_sql(   "stock_transactions",conn, if_exists="replace", index=False)

conn.commit()
conn.close()

# ── 5. ALSO SAVE AS CSV (for data/ folder) ───────────────────────────────────
df_products.to_csv(os.path.join(DATA_DIR, "products.csv"), index=False)
df_sales.to_csv(   os.path.join(DATA_DIR, "sales.csv"),    index=False)
df_stock.to_csv(   os.path.join(DATA_DIR, "stock_transactions.csv"), index=False)

print(f"✅ Ürünler:           {len(df_products):>6} kayıt")
print(f"✅ Satış işlemleri:   {len(df_sales):>6} kayıt  ({df_sales['date'].min()} → {df_sales['date'].max()})")
print(f"✅ Stok işlemleri:    {len(df_stock):>6} kayıt")
print(f"✅ Veritabanı:        {DB_FILE}")
print(f"✅ CSV dosyaları:     {DATA_DIR}/")
