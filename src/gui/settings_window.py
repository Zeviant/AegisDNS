from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame, QPushButton, QSizePolicy, QStyle, QStyleOptionButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor
import os
import json
from src.gui.change_password_window import ChangePasswordWindow

class Settings_Window(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle(f"Settings - {self.user_name}")
        self.resize(1024, 682)

        # Settings file path
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SETTINGS_FILE = os.path.join(BASE_DIR, "..", "VT_Cache", "settings.json")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Set base styling with button and checkbox styles
        self.setStyleSheet("""
            QWidget {
                background-color: #101e29;
                color: #e5e7eb;
            }
            QLabel#settingsTitle {
                font-size: 22px;
                font-weight: 700;
                padding: 12px 10px;
                color: #ffffff;
                background-color: #1c2839;
                border-radius: 4px;
                margin: 2px;
                border-bottom: 2px solid #2d4a6e;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #cbd5e1;
            }
            QCheckBox {
                color: #e5e7eb;
                font-size: 11pt;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #334155;
                border-radius: 4px;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #2563eb;
            }
            QCheckBox::indicator:hover {
                border-color: #3b82f6;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1d4ed8;
                border-color: #1d4ed8;
            }
        """)

        # Title (styled like table headers)
        title = QLabel("Settings")
        title.setObjectName("settingsTitle")
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)

        # Settings card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(24)

        # Mute notifications checkbox with custom checkmark
        class CheckBoxWithCheckmark(QCheckBox):
            def paintEvent(self, event):
                super().paintEvent(event)
                if self.isChecked():
                    opt = QStyleOptionButton()
                    self.initStyleOption(opt)
                    rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, opt, self)
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setPen(QColor(255, 255, 255))
                    font = QFont("Segoe UI", 12, QFont.Weight.Bold)
                    painter.setFont(font)
                    metrics = painter.fontMetrics()
                    check_text = "✓"
                    text_width = metrics.horizontalAdvance(check_text)
                    text_height = metrics.height()
                    # Center the checkmark both horizontally and vertically
                    check_x = rect.x() + (rect.width() - text_width) // 2
                    check_y = rect.y() + (rect.height() + text_height) // 2 - metrics.descent()
                    painter.drawText(check_x, check_y, check_text)
        
        self.mute_notifications_checkbox = CheckBoxWithCheckmark("Mute notifications (disable system popups and sounds)")
        self.mute_notifications_checkbox.setFont(QFont("Segoe UI", 11))
        
        # Load saved setting
        self.mute_notifications_checkbox.setChecked(self.load_mute_setting())
        
        # Connect checkbox to save function
        self.mute_notifications_checkbox.toggled.connect(self.on_mute_toggled)
        
        card_layout.addWidget(self.mute_notifications_checkbox)
        
        # Password change button
        card_layout.addSpacing(32)
        change_password_btn = QPushButton("Change Password")
        change_password_btn.setObjectName("changePasswordBtn")
        change_password_btn.setFont(QFont("Segoe UI", 11))
        change_password_btn.setMinimumHeight(40)
        change_password_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        change_password_btn.setFixedWidth(220)
        change_password_btn.clicked.connect(self.open_change_password_window)
        card_layout.addWidget(change_password_btn)
        
        card_layout.addStretch()

        layout.addWidget(card)
        layout.addStretch()

        # Apply button width constraint after creating button (so object name is set)
        button_width_style = """
            QPushButton#changePasswordBtn {
                max-width: 220px;
                min-width: 220px;
            }
        """
        self.setStyleSheet(self.styleSheet() + button_width_style)

    def load_mute_setting(self) -> bool:
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    return settings.get("mute_notifications", False)
        except Exception:
            pass
        return False

    def save_mute_setting(self, muted: bool):
        try:
            settings = {}
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            
            settings["mute_notifications"] = muted
            
            os.makedirs(os.path.dirname(self.SETTINGS_FILE), exist_ok=True)
            
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass

    # Checkbox toggle
    def on_mute_toggled(self, checked: bool):
        self.save_mute_setting(checked)

    # Mute state
    def is_notifications_muted(self) -> bool:
        return self.mute_notifications_checkbox.isChecked()

    def open_change_password_window(self):
        self.password_window = ChangePasswordWindow(self.user_name, self.sidebar)
        self.password_window.show()

