import sqlite3
import hashlib
import json
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QFormLayout, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt
from modules.config import DB_PATH
from modules.lang.translator import Translator

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT CHECK(role IN ('admin', 'owner', 'worker')),
            permissions TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "nickname" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")

    if "owner_id" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN owner_id INTEGER")

    if "theme" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'Varsayılan'")

    if "only_self_sales" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN only_self_sales INTEGER DEFAULT 0")

    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'Yigit'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, permissions, nickname, owner_id)
            VALUES (?, ?, 'admin', ?, ?, NULL)
        """, (
            'Yigit',
            hash_password('3535'),
            json.dumps({}),
            'Sistem Yöneticisi'
        ))

    conn.commit()
    conn.close()

class LoginRegisterWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.translator = Translator()
        self.setWindowTitle(self.translator.tr("login.title"))
        self.setFixedSize(350, 250)
        self.logged_in_role = None
        self.logged_in_permissions = None
        self.logged_in_nickname = None
        self.logged_in_user_id = None

        create_user_table()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.welcome = QLabel()
        self.welcome.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.welcome)

        self.form = QFormLayout()

        self.login_user = QLineEdit()
        self.login_pass = QLineEdit()
        self.login_pass.setEchoMode(QLineEdit.Password)
        self.lang_select = QComboBox()
        # --- Ukraynaca Seçeneği Eklendi ---
        self.lang_select.addItems(["Türkçe", "English", "Українська"])
        self.lang_select.currentTextChanged.connect(self.change_language)

        self.login_button = QPushButton()
        self.login_button.clicked.connect(self.handle_login)

        # Etiketleri referanslı oluştur
        self.label_username = QLabel()
        self.label_password = QLabel()
        self.label_language = QLabel()

        self.form.addRow(self.label_username, self.login_user)
        self.form.addRow(self.label_password, self.login_pass)
        self.form.addRow(self.label_language, self.lang_select)
        self.form.addRow(self.login_button)

        self.layout.addLayout(self.form)
        self.setLayout(self.layout)

        self.apply_translations()

    def apply_translations(self):
        _ = self.translator.tr
        self.setWindowTitle(_("login.title"))
        self.welcome.setText("<h2>Inventory Management Assistant</h2><p style='color:gray;'>"
                             + _("login.description") + "</p>")
        self.label_username.setText(_("login.username"))
        self.label_password.setText(_("login.password"))
        self.label_language.setText(_("login.select_language"))
        self.login_button.setText(_("login.submit"))

    def change_language(self, lang_name):
        # --- Ukraynaca Dil Map Eklendi ---
        lang_map = {"Türkçe": "tr", "English": "en", "Українська": "uk"}
        selected_code = lang_map.get(lang_name, "tr")
        self.translator.set_language(selected_code)
        self.apply_translations()

    def handle_login(self):
        username = self.login_user.text().strip()
        password = self.login_pass.text().strip()

        if not username or not password:
            QMessageBox.warning(self, self.translator.tr("warning.title"), self.translator.tr("login.fill_fields"))
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash, role, permissions, nickname FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("error.title"), self.translator.tr("login.db_error").format(error=str(e)))
            return

        if result and result[1] == hash_password(password):
            self.logged_in_user_id = result[0]
            self.logged_in_role = result[2]
            self.logged_in_permissions = json.loads(result[3]) if result[3] else {}
            self.logged_in_nickname = result[4] or username

            QMessageBox.information(self, self.translator.tr("login.success"), self.translator.tr("login.welcome").format(name=self.logged_in_nickname, role=self.logged_in_role))
            self.accept()
        else:
            QMessageBox.critical(self, self.translator.tr("error.title"), self.translator.tr("login.invalid_credentials"))
