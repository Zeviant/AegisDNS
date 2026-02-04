from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from src.SQL_Alchemy.database_manager import DatabaseManager
import sys
import subprocess
import os
import json
from pathlib import Path

class DeleteAccountWindow(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle("Delete Account")
        self.setWindowIcon(sidebar_reference.windowIcon() if sidebar_reference else None)
        self.resize(450, 350)
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
        #     QPushButton#deleteAccountBtn {
        #         background-color: #dc2626;
        #     }
        #     QPushButton#deleteAccountBtn:hover {
        #         background-color: #b91c1c;
        #     }
        #     QPushButton#deleteAccountBtn:pressed {
        #         background-color: #991b1b;
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

        # Warning label
        warning_label = QLabel("WARNING: This action is permanent.")
        warning_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        warning_label.setStyleSheet("color: #ffffff;")
        warning_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(warning_label)

        # Password
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Segoe UI", 10))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_edit)

        # Confirm text
        confirm_label = QLabel("Type CONFIRM to delete your account:")
        confirm_label.setFont(QFont("Segoe UI", 10))
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setPlaceholderText("Type CONFIRM")
        card_layout.addWidget(confirm_label)
        card_layout.addWidget(self.confirm_edit)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFont(QFont("Segoe UI", 10))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.close)
        
        delete_account_btn = QPushButton("Delete Account")
        delete_account_btn.setObjectName("deleteAccountBtn")
        delete_account_btn.setFont(QFont("Segoe UI", 10))
        delete_account_btn.setMinimumHeight(35)
        delete_account_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        delete_account_btn.setFixedWidth(220)
        delete_account_btn.clicked.connect(self.delete_account)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(delete_account_btn, alignment=Qt.AlignRight)
        card_layout.addLayout(buttons_layout)

        layout.addWidget(card)
        layout.addStretch()

        button_width_style = """
            QPushButton#deleteAccountBtn {
                max-width: 220px;
                min-width: 220px;
            }
            QPushButton#cancelBtn {
                max-width: none;
            }
        """
        self.setStyleSheet(self.styleSheet() + button_width_style)

        self.password_edit.returnPressed.connect(self.confirm_edit.setFocus)
        self.confirm_edit.returnPressed.connect(self.delete_account)

    def centerOnScreen(self):
        screen = self.screen()
        if screen is None:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y)

    def delete_account(self):
        password = self.password_edit.text()
        confirm_text = self.confirm_edit.text()
        
        # Validation
        if not password or not confirm_text:
            QMessageBox.warning(self, "Error", "All fields must be filled!")
            return
        
        if confirm_text != "CONFIRM":
            QMessageBox.warning(self, "Error", "Please type CONFIRM exactly to confirm account deletion.")
            return
        
        # Confirm with user one more time
        reply = QMessageBox.question(
            self,
            "Final Confirmation",
            f"Are you sure you want to delete account '{self.user_name}'?\n\n"
            "This will permanently delete and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # First, delete all user data from JSON files
        try:
            self.delete_user_json_data(self.user_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete user data files: {e}")
            return
        
        # Then delete user from database
        result = DatabaseManager.delete_user(self.user_name, password)
        
        if result == "success":
            QMessageBox.information(
                self,
                "Account Deleted",
                "Your account has been permanently deleted.\nThe application will now close."
            )
            self.password_edit.clear()
            self.confirm_edit.clear()
            
            # Restart the application (back to login screen)
            self.restart_application()
        elif result == "wrong_password":
            QMessageBox.warning(self, "Error", "Password is incorrect!")
        else:
            QMessageBox.critical(self, "Error", "An error occurred while deleting the account.")
    
    def delete_user_json_data(self, username: str):
        """Delete all user data from JSON/JSONL files."""
        BASE_DIR = Path(__file__).resolve().parent
        CACHE_DIR = (BASE_DIR / ".." / "VT_Cache").resolve()
        
        # This is ur fault nico (user/username)
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
        
        # Delete entries from files with "user" field
        for file_path in files_with_user_field:
            if not file_path.exists():
                continue
            
            kept_lines = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        # Keep entries that don't belong to this user
                        if entry.get("user") != username:
                            kept_lines.append(line + "\n")
                    except json.JSONDecodeError:
                        # Keep corrupted lines as-is
                        kept_lines.append(line + "\n")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
        
        # Delete entries from files with "username" field
        for file_path in files_with_username_field:
            if not file_path.exists():
                continue
            
            kept_lines = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        # Keep entries that don't belong to this user
                        if entry.get("username") != username:
                            kept_lines.append(line + "\n")
                    except json.JSONDecodeError:
                        kept_lines.append(line + "\n")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
    
    def restart_application(self):
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

