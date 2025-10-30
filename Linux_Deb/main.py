#!/usr/bin/env python3

# main.py

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

from firebase_manager import FirebaseManager
from login_window import LoginWindow
from register_window import RegisterWindow
from main_chat_window import MainChatWindow

class AppController(QStackedWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.firebase_manager = FirebaseManager()
        self.login_win = LoginWindow(self.firebase_manager)
        self.register_win = RegisterWindow(self.firebase_manager)
        self.main_chat_win = None
        self.addWidget(self.login_win); self.addWidget(self.register_win)
        self.login_win.login_successful.connect(self.show_chat_window)
        self.login_win.show_register_window.connect(self.show_register)
        self.register_win.registration_successful.connect(self.show_login)
        self.register_win.show_login_window.connect(self.show_login)

    def show_login(self):
        print("DEBUG: Zeige Login-Fenster an...")
        self.setCurrentWidget(self.login_win)
        self.main_window.setWindowTitle("Login - Tiwut Chat"); self.main_window.setFixedSize(400, 300)

    def show_register(self):
        print("DEBUG: Zeige Registrierungs-Fenster an...")
        self.setCurrentWidget(self.register_win)
        self.main_window.setWindowTitle("Register - Tiwut Chat"); self.main_window.setFixedSize(400, 450) # Etwas höher

    def show_chat_window(self, user_data):
        print(f"DEBUG: Login erfolgreich für {user_data.get('displayName')}. Zeige Chat-Fenster an...")
        if self.main_chat_win: self.removeWidget(self.main_chat_win); self.main_chat_win.deleteLater()
        
        # user_data an den FirebaseManager übergeben
        self.firebase_manager.user_data = user_data
        self.firebase_manager.user_token = user_data.get('idToken')

        self.main_chat_win = MainChatWindow(self.firebase_manager, user_data)
        # Logout-Signal verbinden
        self.main_chat_win.logout_requested.connect(self.handle_logout)
        
        self.addWidget(self.main_chat_win); self.setCurrentWidget(self.main_chat_win)
        self.main_window.setFixedSize(900, 600); self.main_window.setWindowTitle("Tiwut Chat")

    def handle_logout(self):
        """Behandelt den Logout-Prozess."""
        print("DEBUG: Logout wird ausgeführt...")
        if self.main_chat_win:
            self.main_chat_win.close() # Schließt Fenster und stoppt Stream
        self.firebase_manager.clear_session() # Löscht die Sitzungsdatei
        self.show_login() # Zeigt das Login-Fenster an

def main():
    app = QApplication(sys.argv)
    
    # (Dark Theme Code bleibt unverändert)
    app.setStyle("Fusion"); dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(32, 44, 51))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(233, 237, 239))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 57, 66))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(233, 237, 239))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(0, 168, 132))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(17, 27, 33))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 92, 75))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(0, 168, 132))
    app.setPalette(dark_palette)

    main_window = QMainWindow()
    controller = AppController(main_window)
    main_window.setCentralWidget(controller)

    # --- HIER IST DIE NEUE START-LOGIK ---
    session_data = controller.firebase_manager.load_session()
    auto_login_success = False
    if session_data and session_data.get('refreshToken'):
        print("DEBUG: Gespeicherte Sitzung gefunden, versuche Token zu erneuern...")
        success, token_data = controller.firebase_manager.refresh_token(session_data['refreshToken'])
        if success:
            print("DEBUG: Token-Erneuerung erfolgreich. Automatischer Login...")
            # Kombiniere alte und neue Sitzungsdaten für die Anzeige
            full_user_data = {**session_data, **token_data}
            controller.show_chat_window(full_user_data)
            auto_login_success = True
        else:
            print(f"DEBUG: Token-Erneuerung fehlgeschlagen: {token_data}")

    if not auto_login_success:
        # Wenn kein Auto-Login, zeige das normale Login-Fenster
        controller.show_login()
    # --- ENDE DER NEUEN START-LOGIK ---

    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
