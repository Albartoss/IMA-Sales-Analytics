import sqlite3
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QDateEdit, QPushButton, QHBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDate
from modules.config import DB_PATH
from modules.lang.translator import Translator

class SalesOverviewWindow(QDialog):
    def __init__(self, user_role, user_id):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("sales_overview.title"))
        self.setMinimumSize(850, 600)

        self.user_role = user_role
        self.user_id = user_id
        self.only_self = False

        main_layout = QVBoxLayout()
        filter_layout = QHBoxLayout()

        self.product_filter = QComboBox()
        self.product_filter.addItem(self.t.tr("common.all_products"), None)
        self.populate_product_filter()

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        # DB'deki son tarihi varsayilan yap
        self._set_default_date()

        self.refresh_btn = QPushButton(self.t.tr("sales_overview.refresh"))
        self.refresh_btn.clicked.connect(self.load_sales)

        filter_layout.addWidget(QLabel(self.t.tr("form.product")))
        filter_layout.addWidget(self.product_filter)
        filter_layout.addWidget(QLabel(self.t.tr("form.date")))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(self.refresh_btn)

        if self.user_role == "worker":
            self.self_toggle_btn = QPushButton("\U0001f7e2 " + self.t.tr("sales_overview.show_all"))
            self.self_toggle_btn.clicked.connect(self.toggle_self_sales)
            filter_layout.addWidget(self.self_toggle_btn)

        main_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.t.tr("form.user"),
            self.t.tr("form.product"),
            self.t.tr("form.quantity"),
            self.t.tr("form.date"),
            self.t.tr("form.image")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.table)

        self.total_label = QLabel(self.t.tr("sales_overview.total_sales").format(count=0))
        self.total_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.total_label)

        self.setLayout(main_layout)
        self.load_sales()

    def _set_default_date(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM sales")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                qdate = QDate.fromString(row[0], "yyyy-MM-dd")
                self.date_filter.setDate(qdate if qdate.isValid() else QDate.currentDate())
            else:
                self.date_filter.setDate(QDate.currentDate())
        except:
            self.date_filter.setDate(QDate.currentDate())

    def populate_product_filter(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, product_name FROM products ORDER BY product_name")
            for pid, name in cursor.fetchall():
                self.product_filter.addItem(f"{pid} – {name}", pid)
            conn.close()
        except:
            pass

    def toggle_self_sales(self):
        self.only_self = not self.only_self
        text = ("✅ " + self.t.tr("sales_overview.only_self")
                if self.only_self else
                "🟢 " + self.t.tr("sales_overview.show_all"))
        self.self_toggle_btn.setText(text)
        self.load_sales()

    def load_sales(self):
        date_str = self.date_filter.date().toString("yyyy-MM-dd")
        selected_pid = self.product_filter.currentData()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # LEFT JOIN users — user_id NULL olsa bile satirlari goster
            base_query = """
                SELECT
                    COALESCE(u.nickname, u.username, '?') AS kullanici,
                    p.product_name,
                    s.quantity_sold,
                    s.date,
                    COALESCE(p.image_path, '') AS image_path
                FROM sales s
                LEFT JOIN users u ON s.user_id = u.id
                JOIN products p ON s.product_id = p.product_id
                WHERE s.date = ? AND s.quantity_sold > 0
            """
            params = [date_str]

            if self.user_role == "owner":
                base_query += " AND (u.owner_id = ? OR u.id = ? OR s.user_id IS NULL)"
                params += [self.user_id, self.user_id]
            elif self.user_role == "worker" and self.only_self:
                base_query += " AND s.user_id = ?"
                params.append(self.user_id)

            if selected_pid is not None:
                base_query += " AND s.product_id = ?"
                params.append(selected_pid)

            base_query += " ORDER BY s.date DESC"
            cursor.execute(base_query, tuple(params))
            rows = cursor.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            total_sales = 0
            for row_idx, (kullanici, product_name, qty, date, img_path) in enumerate(rows):
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(kullanici)))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(product_name)))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(qty)))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(date)))

                image_label = QLabel()
                if img_path and os.path.exists(img_path):
                    pixmap = QPixmap(img_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(pixmap)
                self.table.setCellWidget(row_idx, 4, image_label)
                self.table.setRowHeight(row_idx, 65)
                total_sales += int(qty)

            self.total_label.setText(self.t.tr("sales_overview.total_sales").format(count=total_sales))

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(f"Hata: {str(e)}"))
