# register_window.py

from PyQt6.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
                             QMessageBox, QCheckBox, QHBoxLayout)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

class RegisterWindow(QWidget):
    registration_successful = pyqtSignal()
    show_login_window = pyqtSignal()

    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.setWindowTitle("Register - Tiwut Chat")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.display_name_input = QLineEdit(); self.display_name_input.setPlaceholderText("Display Name")
        self.username_input = QLineEdit(); self.username_input.setPlaceholderText("Username (3-20 characters, a-z, 0-9, _)")
        self.password_input = QLineEdit(); self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password (min. 6 characters)")
        self.confirm_password_input = QLineEdit(); self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        
        # --- HIER SIND DIE ÄNDERUNGEN ---
        terms_layout = QHBoxLayout()
        self.terms_checkbox = QCheckBox() # Checkbox ohne eigenen Text
        self.terms_checkbox.toggled.connect(self.toggle_register_button)
        
        terms_label = QLabel()
        # Erlaubt dem Label, Links zu öffnen
        terms_label.setOpenExternalLinks(True) 
        terms_label.setText(
            'I accept the <a href="https://tiwut.de/Tiwut-Chat/sys/terms.html" style="color: #00A884;">'
            'Terms and Conditions</a>'
        )
        
        terms_layout.addWidget(self.terms_checkbox)
        terms_layout.addWidget(terms_label)
        terms_layout.addStretch() # Sorgt dafür, dass alles linksbündig bleibt
        # --- ENDE DER ÄNDERUNGEN ---

        self.register_button = QPushButton("Register")
        self.register_button.setEnabled(False)
        self.register_button.clicked.connect(self.handle_register)
        self.login_button = QPushButton("Already have an account? Login here")
        self.login_button.setStyleSheet("background-color: transparent; border: none; color: #00A884;")
        self.login_button.clicked.connect(self.show_login_window.emit)
        
        layout.addWidget(QLabel("Display Name:")); layout.addWidget(self.display_name_input)
        layout.addWidget(QLabel("Username:")); layout.addWidget(self.username_input)
        layout.addWidget(QLabel("Password:")); layout.addWidget(self.password_input)
        layout.addWidget(QLabel("Confirm Password:")); layout.addWidget(self.confirm_password_input)
        layout.addLayout(terms_layout) # Das neue Layout mit dem Link hinzufügen
        layout.addWidget(self.register_button)
        layout.addWidget(self.login_button)
        
        self.setLayout(layout)

    def toggle_register_button(self): self.register_button.setEnabled(self.terms_checkbox.isChecked())
    def handle_register(self):
        display_name = self.display_name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if password != self.confirm_password_input.text(): QMessageBox.warning(self, "Input Error", "Passwords do not match."); return
        if len(password) < 6: QMessageBox.warning(self, "Input Error", "Password must be at least 6 characters long."); return
        
        self.register_button.setEnabled(False); self.register_button.setText("Registering...")
        success, message = self.firebase_manager.register(display_name, username, password)
        if success:
            QMessageBox.information(self, "Success", "Registration successful! Please log in.")
            self.registration_successful.emit()
        else:
            QMessageBox.critical(self, "Registration Failed", f"Error: {message}")
            self.register_button.setEnabled(True); self.register_button.setText("Register")
