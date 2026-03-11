from PyQt5.QtWidgets import QDialog, QFormLayout, QComboBox, QPushButton, QMessageBox, QFileDialog
import sqlite3
import pandas as pd
import tempfile
from modules.config import DB_PATH
from modules.widgets.plotly_to_gui import PlotlyViewer
from modules.lang.translator import Translator
from modules.logic.forecasting import get_forecast_with_arima

class FilteredForecastWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("forecast.filtered_title"))
        self.setFixedSize(320, 220)

        self.layout = QFormLayout()
        self.product_dropdown = QComboBox()

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT DISTINCT product_name FROM products", conn)
            conn.close()
            for name in df["product_name"].dropna().unique():
                self.product_dropdown.addItem(name)
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("forecast.load_error").format(error=str(e)))
            self.close()

        # FIX: Kullanıcı tahmin penceresini seçebilsin
        self.periods_dropdown = QComboBox()
        for label, val in [("14 Gün", 14), ("30 Gün", 30), ("60 Gün", 60), ("90 Gün", 90)]:
            self.periods_dropdown.addItem(label, val)
        self.periods_dropdown.setCurrentIndex(1)  # default: 30 gün

        self.forecast_btn = QPushButton(self.t.tr("forecast.button"))
        self.forecast_btn.clicked.connect(self.show_forecast)

        self.save_html_btn = QPushButton(self.t.tr("plotly.save_html"))
        self.save_html_btn.clicked.connect(self.save_html)

        self.layout.addRow(self.t.tr("forecast.select_product"), self.product_dropdown)
        self.layout.addRow("Tahmin Penceresi:", self.periods_dropdown)
        self.layout.addRow(self.forecast_btn)
        self.layout.addRow(self.save_html_btn)
        self.setLayout(self.layout)

        self.last_fig = None

    def show_forecast(self):
        product_name = self.product_dropdown.currentText()
        periods = self.periods_dropdown.currentData()  # FIX: seçilen değeri al

        result = get_forecast_with_arima(product_name, periods=periods)
        if not result or result[0] is None or result[6] is None:
            QMessageBox.warning(self, self.t.tr("warning.title"), self.t.tr("forecast.no_data"))
            self.last_fig = None
            return

        df_prophet, forecast, mae_prophet, rmse_prophet, mae_arima, rmse_arima, fig = result
        self.last_fig = fig

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
            fig.write_html(tmp_html.name)
            html_path = tmp_html.name

        viewer = PlotlyViewer((html_path, f"{product_name} – {self.t.tr('forecast.title')}"))
        viewer.exec_()

        QMessageBox.information(
            self,
            self.t.tr("forecast.result_title"),
            f"Prophet\nMAE: {mae_prophet:.2f}  RMSE: {rmse_prophet:.2f}\n"
            f"ARIMA\nMAE: {mae_arima:.2f}  RMSE: {rmse_arima:.2f}"
        )

    def save_html(self):
        if self.last_fig is None:
            QMessageBox.warning(self, self.t.tr("warning.title"), self.t.tr("forecast.no_data"))
            return
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getSaveFileName(self, self.t.tr("plotly.save_html"), "", "HTML (*.html)")
        if file_path:
            if not file_path.endswith(".html"):
                file_path += ".html"
            try:
                self.last_fig.write_html(file_path)
                QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("plotly.html_saved").format(path=file_path))
            except Exception as e:
                QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("plotly.html_exception").format(error=str(e)))
