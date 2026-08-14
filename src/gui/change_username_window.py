from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from src.logic import api_client
import sys
import subprocess
import os

class ChangeUsernameWindow(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle("Change Username")
        self.setWindowIcon(sidebar_reference.windowIcon() if sidebar_reference else None)
        self.resize(450, 300)
        self.centerOnScreen()

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
        
        # Update username via the backend (it also renames the user's history/
        # whitelist/blacklist/log entries and updates the Addresses table).
        try:
            response = api_client.change_username(self.user_name, current_pass, new_username)
        except api_client.BackendUnavailable:
            QMessageBox.critical(
                self, "Backend Unavailable",
                f"Could not reach the AegisDNS backend at {api_client.BACKEND_URL}.\n\n"
                "Make sure it's running and try again."
            )
            return
        result = response.get("reason")

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

