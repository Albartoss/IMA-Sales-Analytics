import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import os
from datetime import datetime
from prophet import Prophet
from modules.config import DB_PATH

conn = sqlite3.connect(DB_PATH)
df_sales = pd.read_sql_query("SELECT date, product_id, quantity_sold FROM sales", conn)
df_products = pd.read_sql_query("SELECT * FROM products", conn)
df_stock = pd.read_sql_query("SELECT product_id, date, quantity FROM stock_transactions", conn)
df_links = pd.read_sql_query("SELECT * FROM product_storage_links", conn)
df_shelves = pd.read_sql_query("SELECT id, max_capacity FROM shelves", conn)
df_fridges = pd.read_sql_query("SELECT id, max_capacity FROM fridges", conn)
conn.close()

df_sales["date"] = pd.to_datetime(df_sales["date"], errors="coerce")
df_stock["date"] = pd.to_datetime(df_stock["date"], errors="coerce")
df_products["discount_until"] = pd.to_datetime(df_products["discount_until"], errors="coerce")

# FIX 1: today = verinin son tarihi, gerçek saat değil.
# Böylece 2024-12-31'de biten veri için tahmin 2025-01-xx'e uzanır,
# ~15 aylık boşluk kaybolur ve Prophet saçmalamaz.
data_end = df_sales["date"].max()
today = data_end

df_daily = df_sales.groupby("date")["quantity_sold"].sum().reset_index()
df_prophet = df_daily.rename(columns={"date": "ds", "quantity_sold": "y"})

# FIX 2: Son 365 günü kullan. 2 yıl veride trendin ağırlığı
# çok artar; kısa pencere mevsimselliği daha temiz yakalar.
cutoff = data_end - pd.Timedelta(days=365)
df_prophet_fit = df_prophet[df_prophet["ds"] >= cutoff].copy()

model = Prophet(
    daily_seasonality=False,   # FIX 3: Günlük seasonality gereksiz gürültü ekler,
    weekly_seasonality=True,   # haftalık (Cuma/hafta sonu boostları) yeterli.
    yearly_seasonality=True,
    seasonality_mode="multiplicative",  # FIX 4: Satışlar çarpımsal büyür (Ramazan x%, hafta sonu x%).
    interval_width=0.8,        # FIX 5: 0.6 çok dar, güven aralığını 0.8'e çektik.
    changepoint_prior_scale=0.1  # FIX 6: Ani trend değişimlerine daha duyarlı.
)
model.fit(df_prophet_fit)

future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)

# FIX 7: Filtre artık data_end'e göre, today (Mart 2026) değil.
forecast_30 = forecast[
    (forecast["ds"] > data_end) &
    (forecast["ds"] <= data_end + pd.Timedelta(days=30))
].copy()

forecast_30["yhat"] = forecast_30["yhat"].clip(lower=0)
forecast_30["yhat_upper"] = forecast_30["yhat_upper"].clip(lower=0)
forecast_30["yhat_lower"] = forecast_30["yhat_lower"].clip(lower=0)

total_forecast_qty = forecast_30["yhat"].sum()

# FIX 8: Stok = toplam giriş - toplam satış.
# Önceki kodda sadece giriş toplanıyordu, satış düşülmüyordu.
df_sales_sum = df_sales.groupby("product_id")["quantity_sold"].sum().reset_index()
df_stock_sum = df_stock.groupby("product_id")["quantity"].sum().reset_index()

df_summary = pd.merge(df_products, df_sales_sum, on="product_id", how="left").fillna(0).infer_objects()
df_summary = pd.merge(df_summary, df_stock_sum, on="product_id", how="left").fillna(0).infer_objects()
df_summary = pd.merge(df_summary, df_links, on="product_id", how="left")
df_summary["current_stock"] = df_summary["quantity"] - df_summary["quantity_sold"]
df_summary["current_stock"] = df_summary["current_stock"].clip(lower=0)  # negatif stok mantıksız

mask = (
    pd.notna(df_summary["discount_price"]) &
    pd.notna(df_summary["discount_until"]) &
    (df_summary["discount_until"] >= today)
)
df_summary["effective_price"] = df_summary["selling_price"]
df_summary.loc[mask, "effective_price"] = df_summary.loc[mask, "discount_price"]

for col in ["effective_price", "cost_price", "quantity_sold", "quantity", "unit_volume"]:
    df_summary[col] = pd.to_numeric(df_summary[col], errors="coerce").fillna(1.0 if col == "unit_volume" else 0.0)

# FIX 9: Ürün bazlı ağırlık sadece son 90 günün satışına göre hesaplanıyor.
# Tüm zamanın toplamı mevsimsel sapmaları gizler; kısa pencere daha gerçekçi.
recent_cutoff = data_end - pd.Timedelta(days=90)
df_recent_sales = df_sales[df_sales["date"] >= recent_cutoff]
df_recent_sum = df_recent_sales.groupby("product_id")["quantity_sold"].sum().reset_index()
df_recent_sum.columns = ["product_id", "recent_qty"]
df_summary = pd.merge(df_summary, df_recent_sum, on="product_id", how="left").fillna(0)

total_recent = df_summary["recent_qty"].sum()
df_summary["weight"] = df_summary["recent_qty"] / total_recent if total_recent > 0 else 1 / len(df_summary)
df_summary["forecasted_qty"] = df_summary["weight"] * total_forecast_qty
df_summary["shortage"] = (df_summary["forecasted_qty"] - df_summary["current_stock"]).apply(lambda x: x if x > 0 else 0)

df_summary["potential_revenue"] = df_summary["forecasted_qty"] * df_summary["effective_price"]
df_summary["potential_cost"] = df_summary["forecasted_qty"] * df_summary["cost_price"]
df_summary["potential_profit"] = df_summary["potential_revenue"] - df_summary["potential_cost"]

def get_capacity(row):
    try:
        if row["storage_type"] == "shelf":
            return df_shelves[df_shelves["id"] == row["storage_id"]]["max_capacity"].values[0]
        elif row["storage_type"] == "fridge":
            return df_fridges[df_fridges["id"] == row["storage_id"]]["max_capacity"].values[0]
    except:
        return None

df_summary["storage_capacity"] = df_summary.apply(get_capacity, axis=1)
df_summary["projected_volume"] = df_summary["forecasted_qty"] * df_summary["unit_volume"]
df_summary["volume_overload"] = df_summary.apply(
    lambda row: row["projected_volume"] > row["storage_capacity"] if pd.notna(row["storage_capacity"]) else False,
    axis=1
)

total_profit = df_summary["potential_profit"].sum()
total_revenue = df_summary["potential_revenue"].sum()
total_shortage = df_summary["shortage"].sum()
critical_items = df_summary[df_summary["shortage"] > 0]
volume_issues = df_summary[df_summary["volume_overload"] == True]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_prophet_fit["ds"], y=df_prophet_fit["y"],
    mode='lines+markers',
    name='Gerçek Satış (Son 365 Gün)',
    line=dict(color='royalblue')
))

fig.add_trace(go.Scatter(
    x=forecast_30["ds"], y=forecast_30["yhat"],
    mode='lines',
    name='Tahmin (30 Gün)',
    line=dict(color='darkorange', dash='dash')
))

fig.add_trace(go.Scatter(
    x=forecast_30["ds"].tolist() + forecast_30["ds"][::-1].tolist(),
    y=forecast_30["yhat_upper"].tolist() + forecast_30["yhat_lower"][::-1].tolist(),
    fill='toself',
    fillcolor='rgba(255,165,0,0.2)',
    line=dict(color='rgba(255,255,255,0)'),
    hoverinfo="skip",
    name='Tahmin Aralığı'
))

if not critical_items.empty:
    warning_text = "<br>".join(
        f"{row['product_name']}: {int(row['shortage'])} eksik"
        for _, row in critical_items.iterrows()
    )
    fig.add_annotation(
        text=f"⚠️ Kritik Ürünler:<br>{warning_text}",
        xref="paper", yref="paper",
        x=1, y=0.1, showarrow=False,
        bgcolor="lightyellow", bordercolor="red", borderwidth=1
    )

if not volume_issues.empty:
    overflow_text = "<br>".join(
        f"{row['product_name']} → Kapasite aşımı"
        for _, row in volume_issues.iterrows()
    )
    fig.add_annotation(
        text=f"📦 Depo Yetersizliği:<br>{overflow_text}",
        xref="paper", yref="paper",
        x=1, y=0, showarrow=False,
        bgcolor="mistyrose", bordercolor="darkred", borderwidth=1
    )

fig.update_layout(
    title=f"📈 Toplam Satış Tahmini – Gelecek 30 Gün (Baz: {data_end.strftime('%Y-%m-%d')})",
    xaxis_title="Tarih",
    yaxis_title="Satış Adedi",
    legend=dict(x=0.01, y=0.99),
    template="plotly_white"
)

html_path = os.path.join(os.getcwd(), "forecast_plot.html")
pio.write_html(fig, file=html_path, auto_open=False)

print("30 Günlük Tahmin:")
print(f"  • Baz Tarih: {data_end.strftime('%Y-%m-%d')}")
print(f"  • Beklenen Toplam Satış: {total_forecast_qty:.0f} adet")
print(f"  • Beklenen Gelir: {total_revenue:.2f} TL")
print(f"  • Beklenen Kâr: {total_profit:.2f} TL")
print(f"  • Stok Yetersiz Ürün Sayısı: {len(critical_items)} ürün")
print(f"  • Toplam Açık Miktar: {total_shortage:.0f} adet")
print(f"  • Kapasite Aşımı Olası Ürün Sayısı: {len(volume_issues)}")
print(f"<<HTML_PATH>>{html_path}<<END>>")
