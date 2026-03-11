import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

DB_PATH = "/home/claude/inventory.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─── SCHEMA ────────────────────────────────────────────────────────────────────

cur.executescript("""
CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name    TEXT NOT NULL,
    brand           TEXT,
    category        TEXT,
    cost_price      REAL,
    selling_price   REAL,
    expiry_date     TEXT,
    discount_price  REAL,
    discount_until  TEXT,
    unit_volume     REAL DEFAULT 1.0
);

CREATE TABLE sales (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    product_id      INTEGER NOT NULL,
    quantity_sold   INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE stock_transactions (
    transaction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    date            TEXT NOT NULL,
    quantity        INTEGER NOT NULL,
    note            TEXT,
    expiry_date     TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE shelves (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    max_capacity REAL NOT NULL
);

CREATE TABLE fridges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    max_capacity REAL NOT NULL
);

CREATE TABLE product_storage_links (
    product_id   INTEGER NOT NULL,
    storage_type TEXT CHECK(storage_type IN ('fridge', 'shelf')),
    storage_id   INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
""")
conn.commit()

# ─── PRODUCTS ──────────────────────────────────────────────────────────────────
# (product_name, brand, category, cost_price, selling_price, unit_volume, storage_type)
# storage_type: 'shelf' or 'fridge'

products_data = [
    # Süt & Süt Ürünleri → fridge
    ("Tam Yağlı Süt 1L",       "Sütaş",    "Süt Ürünleri",   8.50,  14.90, 1.0,  "fridge"),
    ("Yarım Yağlı Süt 1L",     "Pınar",    "Süt Ürünleri",   8.20,  14.50, 1.0,  "fridge"),
    ("Kaşar Peyniri 400g",     "Sütaş",    "Süt Ürünleri",  28.00,  49.90, 0.4,  "fridge"),
    ("Beyaz Peynir 500g",      "Pınar",    "Süt Ürünleri",  22.00,  39.90, 0.5,  "fridge"),
    ("Yoğurt 1kg",             "Sütaş",    "Süt Ürünleri",  14.00,  24.90, 1.0,  "fridge"),
    ("Tereyağı 250g",          "Sütaş",    "Süt Ürünleri",  32.00,  54.90, 0.25, "fridge"),
    # Ekmek & Unlu → shelf
    ("Ekmek",                  "Uno",      "Ekmek",          3.50,   7.00, 0.4,  "shelf"),
    ("Tost Ekmeği",            "Uno",      "Ekmek",          9.00,  16.90, 0.45, "shelf"),
    ("Simit",                  "Simit Sarayı","Ekmek",       3.00,   6.00, 0.15, "shelf"),
    # Kuru Gıda → shelf
    ("Makarna 500g",           "Barilla",  "Kuru Gıda",      9.50,  16.90, 0.5,  "shelf"),
    ("Pirinç 1kg",             "Paşazade", "Kuru Gıda",     14.00,  24.90, 1.0,  "shelf"),
    ("Nohut 1kg",              "Paşazade", "Kuru Gıda",     12.00,  21.90, 1.0,  "shelf"),
    ("Kırmızı Mercimek 1kg",   "Paşazade", "Kuru Gıda",     11.00,  19.90, 1.0,  "shelf"),
    # Yağ & Sos → shelf
    ("Zeytinyağı 1L",          "Tariş",    "Yağ & Sos",     45.00,  79.90, 1.0,  "shelf"),
    ("Ayçiçek Yağı 1L",        "Yudum",    "Yağ & Sos",     22.00,  38.90, 1.0,  "shelf"),
    ("Ketçap 300g",            "Tat",      "Yağ & Sos",      9.00,  16.90, 0.3,  "shelf"),
    ("Mayonez 250g",           "Hellmann's","Yağ & Sos",    12.00,  21.90, 0.25, "shelf"),
    ("Domates Salçası 700g",   "Tat",      "Yağ & Sos",     14.00,  24.90, 0.7,  "shelf"),
    # İçecek → shelf (büyük hacim)
    ("Cola 1L",                "Coca-Cola","İçecek",        12.00,  21.90, 1.0,  "shelf"),
    ("Ayran 200ml",            "Sütaş",    "İçecek",         4.00,   7.90, 0.2,  "fridge"),
    ("Meyve Suyu 1L",          "Cappy",    "İçecek",        14.00,  24.90, 1.0,  "shelf"),
    ("Su 1.5L",                "Erikli",   "İçecek",         4.50,   8.90, 1.5,  "shelf"),
    # Kahvaltılık → shelf
    ("Çay 500g",               "Çaykur",   "Kahvaltılık",   35.00,  59.90, 0.5,  "shelf"),
    ("Kahve 200g",             "Jacobs",   "Kahvaltılık",   55.00,  89.90, 0.2,  "shelf"),
    ("Şeker 1kg",              "Torku",    "Kahvaltılık",   18.00,  29.90, 1.0,  "shelf"),
    ("Tuz 750g",               "Balıkesir","Kahvaltılık",    4.00,   7.90, 0.75, "shelf"),
    ("Un 1kg",                 "Güllüoğlu","Kahvaltılık",    9.00,  15.90, 1.0,  "shelf"),
    # Atıştırmalık → shelf
    ("Çikolata 100g",          "Milka",    "Atıştırmalık",  14.00,  24.90, 0.1,  "shelf"),
    ("Cips 100g",              "Ruffles",  "Atıştırmalık",  10.00,  18.90, 0.1,  "shelf"),
    ("Bisküvi 200g",           "Ülker",    "Atıştırmalık",   9.00,  15.90, 0.2,  "shelf"),
    # Sebze & Meyve → shelf (taze bölüm)
    ("Domates (kg)",           "Yerel",    "Sebze & Meyve",  8.00,  14.90, 1.0,  "shelf"),
    ("Salatalık (kg)",         "Yerel",    "Sebze & Meyve",  6.00,  11.90, 1.0,  "shelf"),
    ("Patates (kg)",           "Yerel",    "Sebze & Meyve",  5.00,   9.90, 1.0,  "shelf"),
    ("Soğan (kg)",             "Yerel",    "Sebze & Meyve",  4.50,   8.90, 1.0,  "shelf"),
    ("Muz (kg)",               "Dole",     "Sebze & Meyve", 18.00,  29.90, 1.0,  "shelf"),
    ("Elma (kg)",              "Yerel",    "Sebze & Meyve", 10.00,  18.90, 1.0,  "shelf"),
    ("Portakal (kg)",          "Yerel",    "Sebze & Meyve",  9.00,  16.90, 1.0,  "shelf"),
    # Et & Şarküteri → fridge
    ("Tavuk Göğsü (kg)",       "Banvit",   "Et & Şarküteri",45.00,  79.90, 1.0,  "fridge"),
    ("Sucuk 200g",             "Polonez",  "Et & Şarküteri",28.00,  49.90, 0.2,  "fridge"),
    ("Salam 200g",             "Pınar",    "Et & Şarküteri",22.00,  39.90, 0.2,  "fridge"),
    ("Yumurta (10'lu)",        "Sek",      "Et & Şarküteri",20.00,  34.90, 0.6,  "fridge"),
    # Temizlik → shelf
    ("Deterjan 3kg",           "Ariel",    "Temizlik",      65.00, 109.90, 3.0,  "shelf"),
    ("Bulaşık Deterjanı 750ml","Fairy",    "Temizlik",      28.00,  49.90, 0.75, "shelf"),
    ("Tuvalet Kağıdı 24'lü",   "Selpak",   "Temizlik",      45.00,  79.90, 4.0,  "shelf"),
    ("Şampuan 400ml",          "Head&Shoulders","Kişisel Bakım",38.00,64.90,0.4, "shelf"),
]

# expiry_date: perishables get near-future dates, others get far future
today = datetime.today()

def get_expiry(category, pname):
    if category in ["Süt Ürünleri", "Et & Şarküteri"]:
        return (today + timedelta(days=random.randint(10, 30))).strftime("%Y-%m-%d")
    elif category in ["Ekmek", "Sebze & Meyve"]:
        return (today + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d")
    elif category in ["İçecek", "Atıştırmalık", "Kuru Gıda", "Yağ & Sos"]:
        return (today + timedelta(days=random.randint(180, 720))).strftime("%Y-%m-%d")
    else:
        return (today + timedelta(days=random.randint(365, 900))).strftime("%Y-%m-%d")

for row in products_data:
    pname, brand, cat, cost, sell, vol, _ = row
    expiry = get_expiry(cat, pname)
    cur.execute("""
        INSERT INTO products (product_name, brand, category, cost_price, selling_price, expiry_date, unit_volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (pname, brand, cat, cost, sell, expiry, vol))

conn.commit()

# Get product IDs
products_df = pd.read_sql_query("SELECT product_id, product_name FROM products", conn)
pid_map = dict(zip(products_df["product_name"], products_df["product_id"]))

# ─── SHELVES & FRIDGES ──────────────────────────────────────────────────────────

shelves = [
    ("Raf 1 – Kuru Gıda",      500.0),
    ("Raf 2 – İçecek & Su",    600.0),
    ("Raf 3 – Temizlik",       400.0),
    ("Raf 4 – Kahvaltılık",    350.0),
    ("Raf 5 – Sebze & Meyve",  300.0),
]
fridges = [
    ("Buzdolabı 1 – Süt & Peynir", 200.0),
    ("Buzdolabı 2 – Et & Şarküteri", 150.0),
    ("Buzdolabı 3 – İçecek",       180.0),
]

shelf_ids = []
for name, cap in shelves:
    cur.execute("INSERT INTO shelves (name, max_capacity) VALUES (?, ?)", (name, cap))
    shelf_ids.append(cur.lastrowid)

fridge_ids = []
for name, cap in fridges:
    cur.execute("INSERT INTO fridges (name, max_capacity) VALUES (?, ?)", (name, cap))
    fridge_ids.append(cur.lastrowid)

conn.commit()

# ─── PRODUCT STORAGE LINKS ─────────────────────────────────────────────────────

# Assign each product to a shelf or fridge based on its storage_type
category_shelf_map = {
    "Kuru Gıda":      shelf_ids[0],
    "Yağ & Sos":      shelf_ids[0],
    "İçecek":         shelf_ids[1],
    "Ekmek":          shelf_ids[1],
    "Temizlik":       shelf_ids[2],
    "Kişisel Bakım":  shelf_ids[2],
    "Kahvaltılık":    shelf_ids[3],
    "Atıştırmalık":   shelf_ids[3],
    "Sebze & Meyve":  shelf_ids[4],
}
category_fridge_map = {
    "Süt Ürünleri":   fridge_ids[0],
    "Et & Şarküteri": fridge_ids[1],
}
# Ayran ve fridge içecekler
fridge_içecek = {"Ayran 200ml": fridge_ids[2]}

for row in products_data:
    pname, brand, cat, cost, sell, vol, storage_type = row
    pid = pid_map[pname]

    if pname in fridge_içecek:
        storage_id = fridge_içecek[pname]
        storage_type = "fridge"
    elif storage_type == "fridge":
        storage_id = category_fridge_map.get(cat, fridge_ids[0])
    else:
        storage_id = category_shelf_map.get(cat, shelf_ids[0])
        storage_type = "shelf"

    cur.execute("""
        INSERT INTO product_storage_links (product_id, storage_type, storage_id)
        VALUES (?, ?, ?)
    """, (pid, storage_type, storage_id))

conn.commit()

# ─── SALES (2023-01-01 to 2024-12-31) ──────────────────────────────────────────

start = datetime(2023, 1, 1)
end   = datetime(2024, 12, 31)
dates = pd.date_range(start, end, freq="D")

# Category base daily sales
category_base = {
    "Süt Ürünleri":    8,
    "Ekmek":           15,
    "Kuru Gıda":       7,
    "Yağ & Sos":       5,
    "İçecek":          12,
    "Kahvaltılık":     6,
    "Atıştırmalık":    8,
    "Sebze & Meyve":   10,
    "Et & Şarküteri":  6,
    "Temizlik":        3,
    "Kişisel Bakım":   2,
}

# Map product → category
prod_cat = {}
for row in products_data:
    pname, brand, cat = row[0], row[1], row[2]
    prod_cat[pname] = cat

ramadan_2023 = (datetime(2023, 3, 22), datetime(2023, 4, 21))
ramadan_2024 = (datetime(2024, 3, 10), datetime(2024, 4, 9))

sales_rows = []
for pname, pid in pid_map.items():
    cat = prod_cat.get(pname, "Kuru Gıda")
    base = category_base.get(cat, 5)

    for d in dates:
        # Weekend boost
        dow = d.dayofweek
        weekend = 1.35 if dow >= 5 else 1.0

        # Yearly seasonality (summer +20% for drinks, winter +20% for hot drinks)
        month = d.month
        if cat == "İçecek" and month in [6, 7, 8]:
            seasonal = 1.3
        elif cat == "Kahvaltılık" and month in [11, 12, 1, 2]:
            seasonal = 1.2
        elif cat == "Sebze & Meyve" and month in [4, 5, 6]:
            seasonal = 1.25
        else:
            seasonal = 1.0

        # Ramadan boost for food
        in_ramadan = (ramadan_2023[0] <= d.to_pydatetime() <= ramadan_2023[1] or
                      ramadan_2024[0] <= d.to_pydatetime() <= ramadan_2024[1])
        ramadan = 1.35 if (in_ramadan and cat in ["Kuru Gıda", "Kahvaltılık", "Et & Şarküteri", "Ekmek"]) else 1.0

        # Growth trend +20% over 2 years
        day_idx = (d - pd.Timestamp(start)).days
        trend = 1.0 + 0.20 * (day_idx / len(dates))

        mu = base * weekend * seasonal * ramadan * trend
        qty = max(1, int(np.random.poisson(mu)))

        sales_rows.append((d.strftime("%Y-%m-%d"), pid, qty))

cur.executemany("INSERT INTO sales (date, product_id, quantity_sold) VALUES (?, ?, ?)", sales_rows)
conn.commit()
print(f"Sales inserted: {len(sales_rows)}")

# ─── STOCK TRANSACTIONS ────────────────────────────────────────────────────────
# Weekly restocking: enough to cover ~14 days of demand + some buffer
# We also add expiry_date per batch (realistic: perishables expire sooner)

stock_rows = []
restock_dates = pd.date_range(start, end, freq="7D")  # weekly

for pname, pid in pid_map.items():
    cat = prod_cat.get(pname, "Kuru Gıda")
    base = category_base.get(cat, 5)

    for rd in restock_dates:
        # Restock ~14 days worth + 20% buffer
        qty = max(5, int(base * 14 * 1.2 * random.uniform(0.85, 1.15)))

        # Expiry date on the batch
        if cat in ["Süt Ürünleri", "Et & Şarküteri"]:
            exp = rd + timedelta(days=random.randint(14, 30))
        elif cat in ["Ekmek", "Sebze & Meyve"]:
            exp = rd + timedelta(days=random.randint(3, 7))
        else:
            exp = rd + timedelta(days=random.randint(180, 730))

        stock_rows.append((
            pid,
            rd.strftime("%Y-%m-%d"),
            qty,
            "Haftalık yenileme",
            exp.strftime("%Y-%m-%d")
        ))

cur.executemany("""
    INSERT INTO stock_transactions (product_id, date, quantity, note, expiry_date)
    VALUES (?, ?, ?, ?, ?)
""", stock_rows)
conn.commit()
print(f"Stock transactions inserted: {len(stock_rows)}")

# ─── VERIFY ────────────────────────────────────────────────────────────────────

tables = ["products", "sales", "stock_transactions", "shelves", "fridges", "product_storage_links"]
for t in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {count} rows")

# Check a few product links
sample = pd.read_sql_query("""
    SELECT p.product_name, psl.storage_type, 
           CASE WHEN psl.storage_type='shelf' THEN s.name ELSE f.name END AS storage_name
    FROM product_storage_links psl
    JOIN products p ON p.product_id = psl.product_id
    LEFT JOIN shelves s ON psl.storage_type='shelf' AND s.id = psl.storage_id
    LEFT JOIN fridges f ON psl.storage_type='fridge' AND f.id = psl.storage_id
    LIMIT 10
""", conn)
print("\nSample storage links:")
print(sample.to_string(index=False))

# Check net stock for 3 products
net_check = pd.read_sql_query("""
    SELECT p.product_name,
           SUM(st.quantity) AS total_in,
           COALESCE((SELECT SUM(quantity_sold) FROM sales WHERE product_id=p.product_id),0) AS total_sold,
           SUM(st.quantity) - COALESCE((SELECT SUM(quantity_sold) FROM sales WHERE product_id=p.product_id),0) AS net_stock
    FROM products p
    JOIN stock_transactions st ON st.product_id = p.product_id
    WHERE p.product_name IN ('Pirinç 1kg','Tam Yağlı Süt 1L','Deterjan 3kg')
    GROUP BY p.product_id
""", conn)
print("\nNet stock check:")
print(net_check.to_string(index=False))

conn.close()
print("\nDone! inventory.db ready.")
