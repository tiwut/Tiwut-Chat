# main_chat_window.py

from PyQt6.QtWidgets import (QMainWindow, QWidget, QSplitter, QListWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
import datetime
import time

class MainChatWindow(QMainWindow):
    # NEUES Signal für den Logout
    logout_requested = pyqtSignal()

    def __init__(self, firebase_manager, user_data):
        super().__init__()
        self.firebase_manager = firebase_manager
        self.user_data = user_data
        self.chat_rooms, self.current_room_id, self.last_timestamp = {}, None, 0
        self.setWindowTitle("Tiwut Chat"); self.setGeometry(100, 100, 900, 600)
        self.init_ui()
        self.load_chat_rooms()

    def init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout()
        
        # --- HIER SIND DIE ÄNDERUNGEN ---
        top_bar_layout = QHBoxLayout()
        user_label = QLabel(f"Logged in as: {self.user_data.get('displayName', 'User')}")
        user_label.setFont(QFont("Poppins", 10, QFont.Weight.Bold))
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout_requested.emit) # Signal senden
        top_bar_layout.addWidget(user_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.logout_button)
        # --- ENDE DER ÄNDERUNGEN ---

        self.room_list_widget = QListWidget()
        self.room_list_widget.itemClicked.connect(self.on_room_selected)
        
        sidebar_layout.addLayout(top_bar_layout) # Das neue Layout mit dem Button hinzufügen
        sidebar_layout.addWidget(QLabel("Chat Rooms:"))
        sidebar_layout.addWidget(self.room_list_widget)
        sidebar_widget.setLayout(sidebar_layout)

        # (Der Rest der UI-Initialisierung bleibt unverändert)
        chat_area_widget = QWidget(); chat_layout = QVBoxLayout()
        self.chat_room_title = QLabel("Select a chat to start messaging.")
        self.chat_room_title.setFont(QFont("Poppins", 12, QFont.Weight.Bold))
        self.chat_room_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_view = QTextEdit(); self.message_view.setReadOnly(True)
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit(); self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Send"); self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.message_input); input_layout.addWidget(self.send_button)
        chat_layout.addWidget(self.chat_room_title); chat_layout.addWidget(self.message_view)
        chat_layout.addLayout(input_layout); chat_area_widget.setLayout(chat_layout)
        splitter.addWidget(sidebar_widget); splitter.addWidget(chat_area_widget)
        splitter.setSizes([300, 600]); self.setCentralWidget(splitter)

    # (Alle anderen Methoden wie load_chat_rooms, on_room_selected etc. bleiben unverändert)
    def load_chat_rooms(self):
        self.room_list_widget.clear(); self.chat_rooms = self.firebase_manager.get_chat_rooms()
        if not self.chat_rooms: self.room_list_widget.addItem("No chat rooms found."); return
        for room_id, room_data in self.chat_rooms.items():
            item = QListWidgetItem(f"{room_data.get('name', 'Unnamed Room')}")
            item.setData(Qt.ItemDataRole.UserRole, room_id); self.room_list_widget.addItem(item)
            
    def on_room_selected(self, item):
        self.current_room_id = item.data(Qt.ItemDataRole.UserRole)
        if not self.current_room_id: return
        self.firebase_manager.stop_message_stream()
        room_data = self.chat_rooms.get(self.current_room_id, {})
        self.chat_room_title.setText(room_data.get('name', 'Chat'))
        self.message_view.setText("<i>Loading message history...</i>")
        self.firebase_manager.load_message_history(self.current_room_id, self.on_history_loaded, self.on_stream_error)

    @pyqtSlot(dict)
    def on_history_loaded(self, messages_dict):
        self.message_view.clear()
        if not messages_dict: self.message_view.setText("<i>No messages in this room yet.</i>"); self.last_timestamp = int(time.time() * 1000)
        else:
            sorted_messages = sorted(messages_dict.values(), key=lambda x: x.get('timestamp', 0))
            self.message_view.setHtml("<br>".join([self.format_message(m) for m in sorted_messages]))
            if sorted_messages: self.last_timestamp = sorted_messages[-1].get('timestamp', 0)
        self.message_view.moveCursor(QTextCursor.MoveOperation.End)
        self.firebase_manager.start_message_stream(self.current_room_id, self.last_timestamp + 1, self.on_new_message, self.on_stream_error)

    def send_message(self):
        text = self.message_input.text().strip()
        if text and self.current_room_id: self.firebase_manager.send_message(self.current_room_id, text); self.message_input.clear()

    def format_message(self, msg_data):
        sender = msg_data.get('username', 'Unknown'); text = msg_data.get('text', '').replace('\n', '<br>')
        try: time_str = datetime.datetime.fromtimestamp(msg_data.get('timestamp', 0) / 1000).strftime('%H:%M:%S')
        except (ValueError, TypeError): time_str = "??:??"
        return f"<small>[{time_str}]</small> <b>{sender}:</b> {text}"

    @pyqtSlot(dict)
    def on_new_message(self, msg_data):
        if not msg_data.get('timestamp'): return
        if "<i>" in self.message_view.toHtml(): self.message_view.clear()
        self.message_view.append(self.format_message(msg_data))
        self.last_timestamp = msg_data.get('timestamp', self.last_timestamp)
    
    @pyqtSlot(str)
    def on_stream_error(self, error_message):
        if "Index not defined" in error_message: return
        self.message_view.append(f"<i style='color: red;'>Error: {error_message}</i>")

    def closeEvent(self, event): self.firebase_manager.stop_message_stream(); event.accept()
