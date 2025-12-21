from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import os
import json

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

        # Load styling
        try:
            with open("src/gui/Style_Sheet/table_style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

        # Title
        title = QLabel("Settings")
        tfont = QFont()
        tfont.setPointSize(24)
        tfont.setBold(True)
        title.setFont(tfont)
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)

        # Settings card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(24)

        # Mute notifications checkbox
        self.mute_notifications_checkbox = QCheckBox("Mute notifications (disable system popups and sounds)")
        self.mute_notifications_checkbox.setFont(QFont("Segoe UI", 11))
        
        # Load saved setting
        self.mute_notifications_checkbox.setChecked(self.load_mute_setting())
        
        # Connect checkbox to save function
        self.mute_notifications_checkbox.toggled.connect(self.on_mute_toggled)
        
        card_layout.addWidget(self.mute_notifications_checkbox)
        card_layout.addStretch()

        layout.addWidget(card)
        layout.addStretch()

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

