# login_window.py

from PyQt6.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from PyQt6.QtCore import pyqtSignal

class LoginWindow(QWidget):
    # Signal, das gesendet wird, wenn die Anmeldung erfolgreich ist
    login_successful = pyqtSignal(dict)
    # Signal zum Öffnen des Registrierungsfensters
    show_register_window = pyqtSignal()

    def __init__(self, firebase_manager):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.setWindowTitle("Login - Tiwut Chat")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)
        
        self.register_button = QPushButton("Don't have an account? Register here")
        # Stil ändern, um es wie einen Link aussehen zu lassen
        self.register_button.setStyleSheet("background-color: transparent; border: none; color: #00A884;")
        self.register_button.clicked.connect(self.show_register_window.emit)


        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter username and password.")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("Logging in...")

        success, data = self.firebase_manager.login(username, password)
        
        if success:
            # Signal mit Benutzerdaten senden
            self.login_successful.emit(data)
        else:
            QMessageBox.critical(self, "Login Failed", f"Error: {data}")
            self.login_button.setEnabled(True)
            self.login_button.setText("Login")