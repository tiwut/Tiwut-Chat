# firebase_manager.py

import requests
import json
import time
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from config import firebaseConfig, DUMMY_EMAIL_DOMAIN

# Der Pfad zur Datei, in der wir die Sitzungsinformationen speichern
SESSION_FILE = os.path.join(os.path.expanduser('~'), '.tiwut_chat_session')

# (Die Worker-Klassen HistoryLoader und MessageStreamer bleiben unverändert)
class HistoryLoader(QObject):
    historyLoaded = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)
    def __init__(self, room_id, id_token):
        super().__init__()
        self.room_id, self.id_token, self.db_url = room_id, id_token, firebaseConfig['databaseURL']
    def run(self):
        url = f"{self.db_url}/chats/{self.room_id}/messages.json?auth={self.id_token}"
        try:
            response = requests.get(url, timeout=15)
            self.historyLoaded.emit(response.json() or {}) if response.status_code == 200 else self.errorOccurred.emit(f"Error loading history: {response.text}")
        except requests.exceptions.RequestException as e: self.errorOccurred.emit(f"Network error: {e}")

class MessageStreamer(QObject):
    newMessage = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)
    def __init__(self, room_id, id_token, start_timestamp):
        super().__init__()
        self.room_id, self.id_token, self.start_timestamp = room_id, id_token, start_timestamp
        self._is_running, self.db_url = True, firebaseConfig['databaseURL']
    def run(self):
        stream_url = (f'{self.db_url}/chats/{self.room_id}/messages.json?auth={self.id_token}&orderBy="timestamp"&startAt={self.start_timestamp}')
        headers = {'Accept': 'text/event-stream'}
        try:
            with requests.get(stream_url, headers=headers, stream=True, timeout=30) as r:
                if r.status_code != 200: self.errorOccurred.emit(f"Error connecting to stream: {r.text}"); return
                for line in r.iter_lines():
                    if not self._is_running: break
                    if line and line.decode('utf-8').startswith('data:'):
                        try:
                            data = json.loads(line.decode('utf-8')[len('data: '):])
                            if data.get('path') != '/': self.newMessage.emit(data['data'])
                        except (json.JSONDecodeError, TypeError): pass
        except requests.exceptions.RequestException as e: self.errorOccurred.emit(f"Connection error: {e}")
    def stop(self): self._is_running = False

class FirebaseManager:
    def __init__(self):
        self.api_key = firebaseConfig['apiKey']
        self.db_url = firebaseConfig['databaseURL']
        self.auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        self.signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        self.update_profile_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.api_key}"
        self.refresh_url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        self.user_token, self.user_data = None, None
        self.history_thread, self.message_thread = None, None
        self.history_loader, self.message_streamer = None, None

    # NEUE Methoden zur Sitzungsverwaltung
    def save_session(self, user_data):
        """Speichert die relevanten Sitzungsdaten in die Datei."""
        session_data = {
            'refreshToken': user_data.get('refreshToken'),
            'displayName': user_data.get('displayName'),
            'localId': user_data.get('localId'),
        }
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)
        print("DEBUG: Sitzung gespeichert.")

    def load_session(self):
        """Lädt Sitzungsdaten aus der Datei, wenn sie existiert."""
        if not os.path.exists(SESSION_FILE):
            return None
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return None

    def clear_session(self):
        """Löscht die Sitzungsdatei (für den Logout)."""
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print("DEBUG: Sitzung gelöscht.")

    def refresh_token(self, refresh_token):
        """Versucht, mit dem Refresh-Token ein neues ID-Token zu erhalten."""
        payload = json.dumps({"grant_type": "refresh_token", "refresh_token": refresh_token})
        response = requests.post(self.refresh_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            # Wir formatieren die Antwort so, dass sie unseren user_data ähnelt
            self.user_token = token_data['id_token']
            return True, {'idToken': token_data['id_token'], 'refreshToken': token_data['refresh_token']}
        return False, response.json().get('error', {}).get('message')

    def login(self, username, password):
        email = f"{username.lower()}{DUMMY_EMAIL_DOMAIN}"
        payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
        response = requests.post(self.auth_url, data=payload)
        if response.status_code == 200:
            self.user_data = response.json()
            self.user_token = self.user_data['idToken']
            self.save_session(self.user_data) # Sitzung nach erfolgreichem Login speichern
            return True, self.user_data
        return False, response.json().get('error', {}).get('message', 'Unknown error')

    # (register, get_chat_rooms, etc. bleiben größtenteils unverändert)
    def register(self, display_name, username, password):
        check_url = f"{self.db_url}/usernames/{username.lower()}.json"
        response = requests.get(check_url)
        if response.json() is not None: return False, "Username is already taken."
        email = f"{username.lower()}{DUMMY_EMAIL_DOMAIN}"
        payload = json.dumps({"email": email, "password": password, "returnSecureToken": True})
        signup_response = requests.post(self.signup_url, data=payload)
        if signup_response.status_code != 200: return False, signup_response.json().get('error',{}).get('message')
        signup_data = signup_response.json()
        user_id, id_token = signup_data['localId'], signup_data['idToken']
        requests.post(self.update_profile_url, data=json.dumps({"idToken": id_token, "displayName": display_name}))
        db_payload = {f"usernames/{username.lower()}": user_id, f"users/{user_id}/profile": {"displayName": display_name}}
        requests.patch(f"{self.db_url}/.json?auth={id_token}", data=json.dumps(db_payload))
        return True, "Registration successful."

    def get_chat_rooms(self):
        url = f"{self.db_url}/chatrooms.json"
        if self.user_token: url += f"?auth={self.user_token}"
        try:
            response = requests.get(url); return response.json() or {}
        except requests.RequestException: return {}

    def send_message(self, room_id, message_text):
        if not self.user_token or not self.user_data: return False, "User not logged in."
        url = f"{self.db_url}/chats/{room_id}/messages.json?auth={self.user_token}"
        payload = {"username": self.user_data.get('displayName', 'Unknown'), "text": message_text, "timestamp": {".sv": "timestamp"}}
        response = requests.post(url, data=json.dumps(payload))
        return response.status_code == 200, response.text
    
    def load_message_history(self, room_id, success_slot, error_slot):
        self.history_thread = QThread()
        self.history_loader = HistoryLoader(room_id, self.user_token)
        self.history_loader.moveToThread(self.history_thread)
        self.history_thread.started.connect(self.history_loader.run)
        self.history_loader.historyLoaded.connect(success_slot)
        self.history_loader.errorOccurred.connect(error_slot)
        self.history_thread.finished.connect(self.history_thread.deleteLater)
        self.history_loader.historyLoaded.connect(self.history_thread.quit)
        self.history_loader.errorOccurred.connect(self.history_thread.quit)
        self.history_thread.start()

    def start_message_stream(self, room_id, start_timestamp, new_message_slot, error_slot):
        self.stop_message_stream()
        self.message_thread = QThread()
        self.message_streamer = MessageStreamer(room_id, self.user_token, start_timestamp)
        self.message_streamer.moveToThread(self.message_thread)
        self.message_thread.started.connect(self.message_streamer.run)
        self.message_streamer.newMessage.connect(new_message_slot)
        self.message_streamer.errorOccurred.connect(error_slot)
        self.message_thread.start()

    def stop_message_stream(self):
        if self.message_thread and self.message_thread.isRunning():
            self.message_streamer.stop(); self.message_thread.quit(); self.message_thread.wait()
