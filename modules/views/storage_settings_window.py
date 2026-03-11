from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox
)
import sqlite3
from modules.config import DB_PATH
from modules.lang.translator import translator as _

class ProductStorageSettingsWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("storage_settings.title"))
        self.setMinimumSize(450, 300)

        self.layout = QVBoxLayout()
        self.form = QFormLayout()

        self.product_dropdown = QComboBox()
        self.location_type = QComboBox()
        self.location_id = QComboBox()
        self.unit_volume_input = QLineEdit()

        self.load_products()
        self.location_type.addItems([_("storage_settings.shelf"), _("storage_settings.fridge")])
        self.location_type.currentTextChanged.connect(self.load_locations)
        self.load_locations(_("storage_settings.shelf"))

        self.form.addRow(_("storage_settings.product") + ":", self.product_dropdown)
        self.form.addRow(_("storage_settings.type") + ":", self.location_type)
        self.form.addRow(_("storage_settings.id") + ":", self.location_id)
        self.form.addRow(_("storage_settings.unit_volume") + ":", self.unit_volume_input)

        self.btn_save = QPushButton(_("storage_settings.save"))
        self.btn_save.clicked.connect(self.save_setting)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.btn_save)
        self.setLayout(self.layout)

    def load_products(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, product_name FROM products")
            products = cursor.fetchall()
            conn.close()
            self.product_dropdown.clear()
            for pid, name in products:
                self.product_dropdown.addItem(f"{name} ({pid})", pid)
        except Exception as e:
            QMessageBox.critical(self, _("error.title"), _("storage_settings.load_products_error").format(error=e))

    def load_locations(self, location_type_text):
        try:
            # shelves/fridges tablolarını kullan — storage_units yok
            location_type = "shelf" if location_type_text == _("storage_settings.shelf") else "fridge"
            table = "shelves" if location_type == "shelf" else "fridges"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, name FROM {table}")
            locations = cursor.fetchall()
            conn.close()
            self.location_id.clear()
            for lid, name in locations:
                self.location_id.addItem(f"{name} ({lid})", lid)
        except Exception as e:
            QMessageBox.critical(self, _("error.title"), _("storage_settings.load_locations_error").format(error=e))

    def save_setting(self):
        try:
            product_id = self.product_dropdown.currentData()
            location_type_text = self.location_type.currentText()
            location_type = "shelf" if location_type_text == _("storage_settings.shelf") else "fridge"
            location_id = self.location_id.currentData()

            # unit_volume boş bırakılabilir
            vol_text = self.unit_volume_input.text().strip()
            unit_volume = float(vol_text) if vol_text else None

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # product_storage_links — ai_suggestion_engine ve reorder_advisor ile aynı tablo
            cursor.execute("""
                INSERT OR REPLACE INTO product_storage_links (product_id, storage_type, storage_id)
                VALUES (?, ?, ?)
            """, (product_id, location_type, location_id))

            # unit_volume varsa products tablosunu güncelle
            if unit_volume is not None:
                cursor.execute("""
                    UPDATE products SET unit_volume = ? WHERE product_id = ?
                """, (unit_volume, product_id))

            conn.commit()
            conn.close()

            QMessageBox.information(self, _("success.title"), _("storage_settings.success"))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, _("error.title"), _("storage_settings.failed").format(error=e))
