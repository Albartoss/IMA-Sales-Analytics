import sqlite3
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
import warnings
from modules.config import DB_PATH

warnings.filterwarnings("ignore")


def _select_arima_order(y: np.ndarray) -> tuple:
    """
    FIX 10: Sabit (1,1,1) yerine veriye göre ARIMA order seç.
    - Çok kısa seri  → (0,1,0)  basit random walk
    - Sparse (sıfır ağırlıklı) seri → (0,1,1)  moving average yeterli
    - Durağan seri   → d=0, (1,0,1)
    - Durağan değil  → d=1, (1,1,1)
    """
    n = len(y)
    if n < 10:
        return (0, 1, 0)

    nonzero_ratio = np.count_nonzero(y) / n
    if nonzero_ratio < 0.4:
        # Günlerin %60'ından fazlasında satış yok → sparse, MA yeterli
        return (0, 1, 1)

    try:
        p_value = adfuller(y, autolag="AIC")[1]
        d = 0 if p_value < 0.05 else 1
    except Exception:
        d = 1

    return (1, d, 1)


def get_forecast_with_arima(product_name, periods=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        sales = pd.read_sql_query("SELECT * FROM sales", conn)
        products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()

        df = pd.merge(sales, products, on="product_id")
        df = df[df["product_name"] == product_name]

        if df.empty:
            print("DEBUG: DataFrame boş, ürün bulunamadı!")
            return None, None, None, None, None, None, None

        df["date"] = pd.to_datetime(df["date"])
        df_grouped = df.groupby("date")["quantity_sold"].sum().reset_index()
        df_prophet = df_grouped.rename(columns={"date": "ds", "quantity_sold": "y"})

        # FIX 11: Ürün bazlı Prophet'te de today = data_end.
        # Gerçek saat değil, verinin son noktası baz alınır.
        data_end = df_prophet["ds"].max()

        # FIX 12: Fit için son 365 günü kullan (tüm tarih değil).
        cutoff = data_end - pd.Timedelta(days=365)
        df_fit = df_prophet[df_prophet["ds"] >= cutoff].copy()
        if len(df_fit) < 30:
            df_fit = df_prophet.copy()  # yeterli veri yoksa tümünü kullan

        # Prophet
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            seasonality_mode="multiplicative",  # FIX 13: multiplicative mod
            interval_width=0.8,
            changepoint_prior_scale=0.1
        )
        model.fit(df_fit)
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        forecast["yhat"] = forecast["yhat"].clip(lower=0)
        forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)
        forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)

        forecast_future = forecast[forecast["ds"] > data_end].copy()

        merged = pd.merge(df_fit, forecast[forecast["ds"] <= data_end], on="ds", how="left").dropna(subset=["yhat"])
        mae_prophet = mean_absolute_error(merged["y"], merged["yhat"])
        rmse_prophet = mean_squared_error(merged["y"], merged["yhat"]) ** 0.5

        # ARIMA
        y = df_fit["y"].values
        order = _select_arima_order(y)  # FIX 10: akıllı order seçimi

        arima_model = ARIMA(y, order=order)
        arima_fit = arima_model.fit()
        arima_forecast_vals = arima_fit.forecast(steps=periods)
        arima_forecast_vals = np.maximum(arima_forecast_vals, 0)  # negatif tahmini sıfırla

        arima_index = pd.date_range(
            data_end + pd.Timedelta(days=1), periods=periods, freq="D"
        )
        arima_series = pd.Series(arima_forecast_vals, index=arima_index)

        # FIX: integer index yerine fittedvalues kullan.
        # predict(start=0, end=n) pandas'ın yeni versiyonlarında patlıyor.
        arima_in_sample = arima_fit.fittedvalues
        mae_arima = mean_absolute_error(y[-len(arima_in_sample):], arima_in_sample)
        rmse_arima = mean_squared_error(y[-len(arima_in_sample):], arima_in_sample) ** 0.5

        # Plot
        # FIX: Grafik tüm geçmişi gösterir (df_prophet), sadece fit penceresi değil.
        # Fit başlangıcı dikey çizgiyle işaretlenir — nerede eğitildiği görülür.
        fig = go.Figure()

        # Fit öncesi soluk gri — bağlam için gösteriliyor ama modele verilmedi
        df_pre_fit = df_prophet[df_prophet["ds"] < cutoff]
        if not df_pre_fit.empty:
            fig.add_trace(go.Scatter(
                x=df_pre_fit["ds"], y=df_pre_fit["y"],
                mode='lines',
                name='Geçmiş (Eğitim Dışı)',
                line=dict(color='lightgray', width=1),
                opacity=0.6
            ))

        fig.add_trace(go.Scatter(
            x=df_fit["ds"], y=df_fit["y"],
            mode='lines+markers',
            name='Gerçek Satış (Eğitim)',
            line=dict(color='royalblue'),
            marker=dict(size=3)
        ))

        # Fit başlangıcını dikey çizgiyle göster.
        # FIX: add_vline, pd.Timestamp ile eski Plotly versiyonlarında patlıyor.
        # add_shape + add_annotation ile aynı görsel sonuç, sıfır hata.
        cutoff_str = str(cutoff.date())
        fig.add_shape(
            type="line",
            x0=cutoff_str, x1=cutoff_str,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="gray", width=1, dash="dot")
        )
        fig.add_annotation(
            x=cutoff_str, y=1,
            xref="x", yref="paper",
            text="Eğitim başlangıcı",
            showarrow=False,
            font=dict(size=10, color="gray"),
            xanchor="left", yanchor="bottom"
        )
        fig.add_trace(go.Scatter(
            x=forecast_future["ds"], y=forecast_future["yhat"],
            mode='lines',
            name='Prophet Tahmini',
            line=dict(color='darkorange', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=forecast_future["ds"].tolist() + forecast_future["ds"][::-1].tolist(),
            y=forecast_future["yhat_upper"].tolist() + forecast_future["yhat_lower"][::-1].tolist(),
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            name='Prophet Tahmin Aralığı'
        ))
        fig.add_trace(go.Scatter(
            x=arima_series.index, y=arima_series.values,
            mode='lines',
            name=f'ARIMA{order} Tahmini',
            line=dict(color='green', dash='dot')
        ))

        fig.update_layout(
            title=f"📈 {product_name} – Prophet vs ARIMA{order} Tahmini",
            xaxis_title="Tarih",
            yaxis_title="Satış Adedi",
            legend=dict(x=0.01, y=0.99),
            template="plotly_white"
        )

        fig.add_annotation(
            text=f"Prophet - MAE: {mae_prophet:.2f} | RMSE: {rmse_prophet:.2f}",
            xref="paper", yref="paper",
            x=1, y=1.13, showarrow=False,
            bgcolor="lightblue", bordercolor="blue", borderwidth=1
        )
        fig.add_annotation(
            text=f"ARIMA{order} - MAE: {mae_arima:.2f} | RMSE: {rmse_arima:.2f}",
            xref="paper", yref="paper",
            x=1, y=1.06, showarrow=False,
            bgcolor="lightgreen", bordercolor="green", borderwidth=1
        )

        return df_prophet, forecast, mae_prophet, rmse_prophet, mae_arima, rmse_arima, fig

    except Exception as e:
        print(f"[forecasting] Hata: {e}")
        return None, None, None, None, None, None, None
