from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from src.SQL_Alchemy.database_manager import DatabaseManager
import sys
import subprocess
import os
import json
from pathlib import Path

class ChangeUsernameWindow(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle("Change Username")
        self.setWindowIcon(sidebar_reference.windowIcon() if sidebar_reference else None)
        self.resize(450, 300)
        self.centerOnScreen()

        # self.setStyleSheet("""
        #     QWidget {
        #         background-color: #101e29;
        #         color: #e5e7eb;
        #     }
        #     QLineEdit {
        #         background-color: #1e293b;
        #         border: 1px solid #334155;
        #         border-radius: 8px;
        #         padding: 8px 10px;
        #         color: #ffffff;
        #     }
        #     QLineEdit:focus {
        #         border: 1px solid #3b82f6;
        #         background-color: #273449;
        #     }
        #     QPushButton {
        #         background-color: #2563eb;
        #         color: white;
        #         border: none;
        #         border-radius: 8px;
        #         padding: 10px 16px;
        #         font-weight: bold;
        #         font-size: 10pt;
        #     }
        #     QPushButton:hover {
        #         background-color: #1d4ed8;
        #     }
        #     QPushButton:pressed {
        #         background-color: #1e40af;
        #     }
        #     QPushButton:disabled {
        #         background-color: #475569;
        #         color: #cbd5e1;
        #     }
        # """)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Card frame
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)

        # Current password
        current_pass_label = QLabel("Current Password:")
        current_pass_label.setFont(QFont("Segoe UI", 10))
        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.Password)
        self.current_password_edit.setPlaceholderText("Enter current password")
        card_layout.addWidget(current_pass_label)
        card_layout.addWidget(self.current_password_edit)

        # New username
        new_username_label = QLabel("New Username:")
        new_username_label.setFont(QFont("Segoe UI", 10))
        self.new_username_edit = QLineEdit()
        self.new_username_edit.setPlaceholderText("Enter new username")
        card_layout.addWidget(new_username_label)
        card_layout.addWidget(self.new_username_edit)

        # Confirm new username
        confirm_username_label = QLabel("Confirm New Username:")
        confirm_username_label.setFont(QFont("Segoe UI", 10))
        self.confirm_username_edit = QLineEdit()
        self.confirm_username_edit.setPlaceholderText("Confirm new username")
        card_layout.addWidget(confirm_username_label)
        card_layout.addWidget(self.confirm_username_edit)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFont(QFont("Segoe UI", 10))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.close)
        
        change_username_btn = QPushButton("Change Username")
        change_username_btn.setObjectName("changeUsernameBtn")
        change_username_btn.setFont(QFont("Segoe UI", 10))
        change_username_btn.setMinimumHeight(35)
        change_username_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        change_username_btn.setFixedWidth(220)
        change_username_btn.clicked.connect(self.change_username)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(change_username_btn, alignment=Qt.AlignRight)
        card_layout.addLayout(buttons_layout)

        layout.addWidget(card)
        layout.addStretch()

        button_width_style = """
            QPushButton#changeUsernameBtn {
                max-width: 220px;
                min-width: 220px;
            }
            QPushButton#cancelBtn {
                max-width: none;
            }
        """
        self.setStyleSheet(self.styleSheet() + button_width_style)

        # Allow Enter key to trigger username change
        self.current_password_edit.returnPressed.connect(self.new_username_edit.setFocus)
        self.new_username_edit.returnPressed.connect(self.confirm_username_edit.setFocus)
        self.confirm_username_edit.returnPressed.connect(self.change_username)

    def centerOnScreen(self):
        screen = self.screen()
        if screen is None:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y)

    def change_username(self):
        current_pass = self.current_password_edit.text()
        new_username = self.new_username_edit.text()
        confirm_username = self.confirm_username_edit.text()
        
        # Validation
        if not current_pass or not new_username or not confirm_username:
            QMessageBox.warning(self, "Error", "All fields must be filled!")
            return
        
        if new_username != confirm_username:
            QMessageBox.warning(self, "Error", "New usernames do not match!")
            return
        
        if new_username == self.user_name:
            QMessageBox.warning(self, "Error", "New username must be different from current username!")
            return
        
        # First, update all JSON files with the new username
        try:
            self.update_json_files(self.user_name, new_username)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update data files: {e}")
            return
        
        # Then update username in database (this also updates Addresses table)
        result = DatabaseManager.update_username(self.user_name, current_pass, new_username)
        
        if result == "success":
            QMessageBox.information(self, "Success", "Username changed successfully! The application will restart now.")
            self.current_password_edit.clear()
            self.new_username_edit.clear()
            self.confirm_username_edit.clear()
            
            # Restart the application
            self.restart_application()
        elif result == "wrong_password":
            QMessageBox.warning(self, "Error", "Current password is incorrect!")
        elif result == "taken":
            QMessageBox.warning(self, "Error", "Username is already taken!")
        else:
            QMessageBox.critical(self, "Error", "An error occurred while changing the username.")
    
    def update_json_files(self, old_username: str, new_username: str):
        """Update all JSON/JSONL files to change username from old to new."""
        BASE_DIR = Path(__file__).resolve().parent
        CACHE_DIR = (BASE_DIR / ".." / "VT_Cache").resolve()
        
        # Files that use "user" field
        files_with_user_field = [
            CACHE_DIR / "vt_history.jsonl",
            CACHE_DIR / "vt_whiteList.jsonl",
            CACHE_DIR / "vt_blackList.jsonl",
        ]
        
        # Files that use "username" field
        files_with_username_field = [
            CACHE_DIR / "logging_mode_history.jsonl",
            CACHE_DIR / "scan_requests.jsonl",
        ]
        
        # Update files with "user" field
        for file_path in files_with_user_field:
            if not file_path.exists():
                continue
            
            lines = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("user") == old_username:
                            entry["user"] = new_username
                        lines.append(json.dumps(entry) + "\n")
                    except json.JSONDecodeError:
                        # Keep corrupted lines as-is
                        lines.append(line + "\n")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        
        # Update files with "username" field
        for file_path in files_with_username_field:
            if not file_path.exists():
                continue
            
            lines = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("username") == old_username:
                            entry["username"] = new_username
                        lines.append(json.dumps(entry) + "\n")
                    except json.JSONDecodeError:
                        # Keep corrupted lines as-is
                        lines.append(line + "\n")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
    
    def restart_application(self):
        """Restart the application by quitting and launching a new instance."""
        app = QApplication.instance()
        if app is None:
            return
        
        # Get the script path
        if getattr(sys, 'frozen', False):
            # If running as compiled executable
            script_path = sys.executable
            args = []
        else:
            # If running as script, try to find main.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            main_py = os.path.join(current_dir, "..", "main.py")
            main_py = os.path.abspath(main_py)
            
            if os.path.exists(main_py):
                script_path = main_py
                args = []
            else:
                # Fallback to original script
                script_path = sys.argv[0]
                if not os.path.isabs(script_path):
                    script_path = os.path.abspath(script_path)
                args = sys.argv[1:]
        
        # Start new instance first
        try:
            if sys.platform == "win32":
                # Windows
                subprocess.Popen([sys.executable, script_path] + args)
            else:
                # Unix-like
                subprocess.Popen([sys.executable, script_path] + args, 
                               start_new_session=True)
            
            # Close this window and quit the application after a short delay
            self.close()
            QTimer.singleShot(200, app.quit)
        except Exception as e:
            QMessageBox.critical(self, "Restart Error", f"Failed to restart application: {e}\nPlease restart manually.")
            self.close()

