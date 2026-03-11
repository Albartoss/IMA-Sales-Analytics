from modules.config import DB_PATH
from modules.lang.translator import Translator
import sqlite3
import os
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel,
    QDateEdit, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QCompleter, QFileDialog
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QDate

t = Translator()

class AddSaleWindow(QDialog):
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle(t.tr("sale.title"))
        self.setFixedSize(900, 650)
        self.user_id = user_id

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.product_input = QLineEdit()
        self.date_input = QDateEdit()
        self.quantity_input = QLineEdit()
        self.discount_input = QLineEdit()
        self.payment_input = QComboBox()
        self.payment_input.addItems([
            t.tr("payment.cash"),
            t.tr("payment.card"),
            t.tr("payment.transfer"),
            t.tr("payment.other")
        ])


        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.product_input.textChanged.connect(self.autofill_by_id)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name, selling_price, discount_price, discount_until, image_path FROM products")
        self.products = cursor.fetchall()
        conn.close()

        self.product_map = {
            name: (pid, price, discount_price, discount_until, img)
            for pid, name, price, discount_price, discount_until, img in self.products
        }
        self.id_to_name = {pid: name for pid, name, *_ in self.products}
        completer = QCompleter(list(self.product_map.keys()))
        completer.setCaseSensitivity(False)
        self.product_input.setCompleter(completer)

        self.form_layout.addRow(t.tr("form.product"), self.product_input)
        self.form_layout.addRow(t.tr("form.quantity"), self.quantity_input)
        self.form_layout.addRow(t.tr("form.date"), self.date_input)
        self.form_layout.addRow(t.tr("form.discount"), self.discount_input)
        self.form_layout.addRow(t.tr("form.payment_type"), self.payment_input)

        self.image_preview = QLabel(t.tr("common.no_image"))
        self.image_preview.setFixedSize(100, 100)
        self.image_preview.setStyleSheet("border: 1px solid gray")
        self.form_layout.addRow(t.tr("form.image"), self.image_preview)

        self.btn_add = QPushButton(t.tr("sale.add_to_list"))
        self.btn_add.clicked.connect(self.add_to_list)
        self.form_layout.addRow(self.btn_add)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
             t("product.name"),
             t("form.quantity"),
             t("form.price"),
             t("form.image")
         ])

        self.table.setMinimumHeight(300)
        self.total_label = QLabel(f"{t('sale.total').format(amount=0.00, currency=t.currency_symbol)}")

        self.btn_delete_selected = QPushButton(t.tr("sale.remove_selected"))
        self.btn_delete_selected.clicked.connect(self.remove_selected_item)
        self.btn_clear_all = QPushButton(t.tr("sale.clear_list"))
        self.btn_clear_all.clicked.connect(self.clear_list)
        self.btn_finalize = QPushButton(t.tr("sale.finalize"))
        self.btn_finalize.clicked.connect(self.finalize_sale)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.total_label)
        self.layout.addWidget(self.btn_delete_selected)
        self.layout.addWidget(self.btn_clear_all)
        self.layout.addWidget(self.btn_finalize)
        self.setLayout(self.layout)

        self.sale_list = []
        self.total_price = 0.0

    def autofill_by_id(self, text):
        try:
            if text.isdigit():
                pid = int(text)
                if pid in self.id_to_name:
                    self.product_input.setText(self.id_to_name[pid])
            else:
                if text in self.product_map:
                    _, _, _, _, img_path = self.product_map[text]
                    if img_path and os.path.exists(img_path):
                        pixmap = QPixmap(img_path)
                        self.image_preview.setPixmap(pixmap.scaled(self.image_preview.size()))
                    else:
                        self.image_preview.setText(t.tr("common.no_image"))
                        self.image_preview.setPixmap(QPixmap())
        except:
            pass

    def add_to_list(self):
        product_name = self.product_input.text()
        quantity_text = self.quantity_input.text()

        if product_name not in self.product_map or not quantity_text.isdigit():
            QMessageBox.warning(self, t.tr("error.title"), t.tr("sale.invalid_entry"))
            return

        quantity = int(quantity_text)
        pid, regular_price, discount_price, discount_until, img_path = self.product_map[product_name]

        use_discount = False
        if discount_price and discount_until:
            try:
                until_date = QDate.fromString(discount_until, "yyyy-MM-dd")
                if QDate.currentDate() <= until_date:
                    use_discount = True
            except:
                pass

        price_used = discount_price if use_discount else regular_price
        total = float(price_used) * quantity

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == product_name:
                old_quantity = int(self.table.item(row, 1).text())
                new_quantity = old_quantity + quantity
                self.table.setItem(row, 1, QTableWidgetItem(str(new_quantity)))
                self.sale_list[row] = (pid, new_quantity, price_used)
                self.total_price += total
                self.table.setItem(row, 2, QTableWidgetItem(f"{new_quantity * price_used:.2f}₺"))
                self.total_label.setText(t.tr("sale.total").format(amount=self.total_price, currency=t.currency_symbol))
                self.product_input.clear()
                self.quantity_input.clear()
                self.image_preview.clear()
                self.image_preview.setText(t.tr("common.no_image"))
                return

        self.sale_list.append((pid, quantity, price_used))
        self.total_price += total

        row_pos = self.table.rowCount()
        self.table.insertRow(row_pos)
        self.table.setItem(row_pos, 0, QTableWidgetItem(product_name))
        self.table.setItem(row_pos, 1, QTableWidgetItem(str(quantity)))
        self.table.setItem(row_pos, 2, QTableWidgetItem(f"{total:.2f}₺"))
        image_item = QLabel()
        if img_path and os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(60, 60)
            image_item.setPixmap(pixmap)
        self.table.setCellWidget(row_pos, 3, image_item)
        self.table.setRowHeight(row_pos, 65)

        self.total_label.setText(t.tr("sale.total").format(amount=self.total_price, currency=t.currency_symbol))
        self.product_input.clear()
        self.quantity_input.clear()
        self.image_preview.clear()
        self.image_preview.setText(t.tr("common.no_image"))

    def remove_selected_item(self):
        selected = self.table.currentRow()
        if selected >= 0:
            price_text = self.table.item(selected, 2).text().replace("₺", "").replace(",", ".")
            self.total_price -= float(price_text)
            del self.sale_list[selected]
            self.table.removeRow(selected)
            self.total_label.setText(t.tr("sale.total").format(amount=self.total_price, currency=t.currency_symbol))

    def clear_list(self):
        self.sale_list.clear()
        self.total_price = 0.0
        self.table.setRowCount(0)
        self.total_label.setText(t.tr("sale.total").format(amount=self.total_price, currency=t.currency_symbol))

    def finalize_sale(self):
        if not self.sale_list:
            QMessageBox.warning(self, t.tr("error.title"), t.tr("sale.empty_list"))
            return

        date = self.date_input.date().toString("yyyy-MM-dd")
        payment_type = self.payment_input.currentText()
        discount_text = self.discount_input.text().replace(",", ".")
        discount = float(discount_text) if discount_text and discount_text.replace(".", "").isdigit() else 0.0

        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()

            total_amount = 0.0
            # Sadece sepetteki urunleri insert et — tum 45 urunu degil
            for pid, qty, price_used in self.sale_list:
                if qty > 0:
                    cursor.execute("""
                        INSERT INTO sales (date, product_id, quantity_sold, user_id)
                        VALUES (?, ?, ?, ?)
                    """, (date, pid, qty, self.user_id))
                    total_amount += qty * float(price_used)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    user_id INTEGER,
                    total_sales REAL DEFAULT 0.0
                )
            """)
            cursor.execute("""
                INSERT INTO sales_summary (date, user_id, total_sales)
                VALUES (?, ?, ?)
            """, (date, self.user_id, total_amount - discount))

            conn.commit()
            conn.close()

            QMessageBox.information(self, t.tr("sale.success"),
                f"{t.tr('sale.total').format(amount=self.total_price, currency=t.currency_symbol)}\n"
                f"{t.tr('sale.discount')}: {discount:.2f}{t.currency_symbol}\n"
                f"{t.tr('sale.net_amount')}: {total_amount - discount:.2f}{t.currency_symbol}\n"
                f"{t.tr('form.payment_type')}: {payment_type}"
            )
            self.clear_list()
            self.close()

        except Exception as e:
            QMessageBox.critical(self, t.tr("error.title"), f"{str(e)}")
