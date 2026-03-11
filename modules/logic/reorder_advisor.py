import sqlite3
import pandas as pd
from datetime import datetime
from modules.config import DB_PATH


class ReorderAdvisor:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.ensure_table_exists()

    def ensure_table_exists(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_storage_links (
                product_id INTEGER,
                storage_type TEXT CHECK(storage_type IN ('fridge', 'shelf')),
                storage_id INTEGER
            )
        """)
        self.conn.commit()

    def load_data(self):
        products = pd.read_sql_query("SELECT product_id, product_name, unit_volume FROM products", self.conn)
        sales = pd.read_sql_query("SELECT product_id, quantity_sold, date FROM sales", self.conn)
        stock = pd.read_sql_query("SELECT product_id, quantity, date FROM stock_transactions", self.conn)
        links = pd.read_sql_query("SELECT * FROM product_storage_links", self.conn)
        fridges = pd.read_sql_query("SELECT id, name, max_capacity FROM fridges", self.conn)
        shelves = pd.read_sql_query("SELECT id, name, max_capacity FROM shelves", self.conn)

        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
        stock["date"] = pd.to_datetime(stock["date"], errors="coerce")
        return products, sales, stock, links, fridges, shelves

    def compute_reorder_advice(self, min_days=5):
        products, sales, stock, links, fridges, shelves = self.load_data()

        # FIX 14: today = verinin son tarihi, sistem saati değil.
        # Sentetik veri 2024-12-31'de bitiyor; sistem saati Mart 2026 olunca
        # span ~800 gün fazla uzuyor ve daily_avg gerçekten küçük çıkıyor.
        data_end = sales["date"].max()
        today = data_end

        span = max((today - sales["date"].min()).days, 1)

        avg_sales = sales.groupby("product_id")["quantity_sold"].sum().reset_index()
        avg_sales["daily_avg"] = avg_sales["quantity_sold"] / span

        # FIX 8 (reorder): Gerçek stok = toplam giriş - toplam satış.
        # Önceki kod sadece giriş toplamını alıyordu.
        total_in = stock.groupby("product_id")["quantity"].sum().reset_index()
        total_in.columns = ["product_id", "total_in"]

        total_sold = sales.groupby("product_id")["quantity_sold"].sum().reset_index()
        total_sold.columns = ["product_id", "total_sold"]

        net_stock = pd.merge(total_in, total_sold, on="product_id", how="left").fillna(0)
        net_stock["current_stock"] = (net_stock["total_in"] - net_stock["total_sold"]).clip(lower=0)

        df = pd.merge(products, avg_sales[["product_id", "daily_avg"]], on="product_id", how="left")
        df = pd.merge(df, net_stock[["product_id", "current_stock"]], on="product_id", how="left")
        df = pd.merge(df, links, on="product_id", how="left")

        df["daily_avg"] = df["daily_avg"].fillna(0)
        df["current_stock"] = df["current_stock"].fillna(0)
        df["days_left"] = df.apply(
            lambda row: row["current_stock"] / row["daily_avg"] if row["daily_avg"] > 0 else float("inf"),
            axis=1
        )

        suggestions = []
        for _, row in df.iterrows():
            if row["days_left"] <= min_days:
                storage_type = row["storage_type"]
                sid = row["storage_id"]
                capacity = None
                storage_name = "?"

                if storage_type == "shelf":
                    cap_row = shelves[shelves["id"] == sid]
                    if not cap_row.empty:
                        capacity = cap_row["max_capacity"].values[0]
                        storage_name = cap_row["name"].values[0]
                elif storage_type == "fridge":
                    cap_row = fridges[fridges["id"] == sid]
                    if not cap_row.empty:
                        capacity = cap_row["max_capacity"].values[0]
                        storage_name = cap_row["name"].values[0]

                used_space = row["current_stock"] * row.get("unit_volume", 1)
                used_percent = (
                    f"{round((used_space / capacity) * 100, 1)}%" if capacity else "Bilinmiyor"
                )

                suggestions.append({
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "daily_avg": round(row["daily_avg"], 2),
                    "stock_left": int(row["current_stock"]),
                    "days_left": round(row["days_left"], 1),
                    "storage_type": storage_type,
                    "storage_id": sid,
                    "storage_name": storage_name,
                    "used_capacity": used_percent,
                    "suggested_order": max(
                        int(row["daily_avg"] * min_days) - int(row["current_stock"]), 0
                    ),
                })

        return suggestions


if __name__ == "__main__":
    advisor = ReorderAdvisor()
    result = advisor.compute_reorder_advice()
    for r in result:
        print(f"\n🔄 {r['product_name']} (ID: {r['product_id']})")
        print(f"  Kalan Gün: {r['days_left']} | Günlük Satış: {r['daily_avg']} | Stok: {r['stock_left']}")
        print(f"  Depo: {r['storage_type']} - {r['storage_name']} | Alan Kullanımı: {r['used_capacity']}")
