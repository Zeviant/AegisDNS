from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from src.SQL_Alchemy.database_manager import DatabaseManager

class ChangePasswordWindow(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle("Change Password")
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

        # New password
        new_pass_label = QLabel("New Password:")
        new_pass_label.setFont(QFont("Segoe UI", 10))
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        self.new_password_edit.setPlaceholderText("Enter new password")
        card_layout.addWidget(new_pass_label)
        card_layout.addWidget(self.new_password_edit)

        # Confirm new password
        confirm_pass_label = QLabel("Confirm New Password:")
        confirm_pass_label.setFont(QFont("Segoe UI", 10))
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("Confirm new password")
        card_layout.addWidget(confirm_pass_label)
        card_layout.addWidget(self.confirm_password_edit)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setFont(QFont("Segoe UI", 10))
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.close)
        
        change_password_btn = QPushButton("Change Password")
        change_password_btn.setObjectName("changePasswordBtn")
        change_password_btn.setFont(QFont("Segoe UI", 10))
        change_password_btn.setMinimumHeight(35)
        change_password_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        change_password_btn.setFixedWidth(220)
        change_password_btn.clicked.connect(self.change_password)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(change_password_btn, alignment=Qt.AlignRight)
        card_layout.addLayout(buttons_layout)

        layout.addWidget(card)
        layout.addStretch()

        button_width_style = """
            QPushButton#changePasswordBtn {
                max-width: 220px;
                min-width: 220px;
            }
            QPushButton#cancelBtn {
                max-width: none;
            }
        """
        self.setStyleSheet(self.styleSheet() + button_width_style)

        # Allow Enter key to trigger password change
        self.current_password_edit.returnPressed.connect(self.new_password_edit.setFocus)
        self.new_password_edit.returnPressed.connect(self.confirm_password_edit.setFocus)
        self.confirm_password_edit.returnPressed.connect(self.change_password)

    def centerOnScreen(self):
        screen = self.screen()
        if screen is None:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        x = (geometry.width() - self.width()) // 2
        y = (geometry.height() - self.height()) // 2
        self.move(x, y)

    def change_password(self):
        current_pass = self.current_password_edit.text()
        new_pass = self.new_password_edit.text()
        confirm_pass = self.confirm_password_edit.text()
        
        # Validation
        if not current_pass or not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Error", "All fields must be filled!")
            return
        
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Error", "New passwords do not match!")
            return
        
        if new_pass == current_pass:
            QMessageBox.warning(self, "Error", "New password must be different from current password!")
            return
        
        # Update password in database
        result = DatabaseManager.update_password(self.user_name, current_pass, new_pass)
        
        if result == "success":
            QMessageBox.information(self, "Success", "Password changed successfully!")
            self.current_password_edit.clear()
            self.new_password_edit.clear()
            self.confirm_password_edit.clear()
            # Update sidebar password
            if self.sidebar and hasattr(self.sidebar, 'password'):
                self.sidebar.password = new_pass
            self.close()
        elif result == "wrong_password":
            QMessageBox.warning(self, "Error", "Current password is incorrect!")
        else:
            QMessageBox.critical(self, "Error", "An error occurred while changing the password.")

