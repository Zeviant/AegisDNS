from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame, QPushButton, QSizePolicy, QStyle, QStyleOption, QStyleOptionButton, QListWidget, QComboBox, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor
import os
import json
from src.gui.change_password_window import ChangePasswordWindow
from src.gui.change_username_window import ChangeUsernameWindow
from src.gui.delete_account_window import DeleteAccountWindow
from src.gui.log_window import Log_Window
from PySide6.QtWidgets import QApplication

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
        
        self.setObjectName("SectionContent")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # Title (styled like table headers)
        title = QLabel("Settings")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignHCenter)
        layout.addWidget(title)

        # Scrollable area for settings
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        # Settings card
        card = QFrame(content)
        card.setObjectName("cardSettings")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 0, 48, 48)
        card_layout.setSpacing(24)

        # User Layout
        user_layout = QVBoxLayout()

        # Theme Layout
        theme_layout = QVBoxLayout()

        # Notification Layout
        notify_layout = QVBoxLayout()

        # History / Cache Layout
        history_layout = QVBoxLayout()

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

        # User section title
        user_section = QLabel()
        user_section.setText("User")
        user_section.setObjectName("SectionDivider")
        user_layout.addWidget(user_section)

        # Username change button
        card_layout.addSpacing(32)
        change_username_btn = QPushButton("Change Username")
        change_username_btn.setObjectName("changeUsernameBtn")
        change_username_btn.setFont(QFont("Segoe UI", 11))
        change_username_btn.setMinimumHeight(40)
        change_username_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        change_username_btn.setFixedWidth(220)
        change_username_btn.clicked.connect(self.open_change_username_window)
        user_layout.addWidget(change_username_btn)
        
        # Password change button
        user_layout.addSpacing(16)
        change_password_btn = QPushButton("Change Password")
        change_password_btn.setObjectName("changePasswordBtn")
        change_password_btn.setFont(QFont("Segoe UI", 11))
        change_password_btn.setMinimumHeight(40)
        change_password_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        change_password_btn.setFixedWidth(220)
        change_password_btn.clicked.connect(self.open_change_password_window)
        user_layout.addWidget(change_password_btn)
        
        # Delete account button
        user_layout.addSpacing(16)
        delete_account_btn = QPushButton("Delete Account")
        delete_account_btn.setObjectName("deleteAccountBtn")
        delete_account_btn.setFont(QFont("Segoe UI", 11))
        delete_account_btn.setMinimumHeight(40)
        delete_account_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        delete_account_btn.setFixedWidth(220)
        delete_account_btn.clicked.connect(self.open_delete_account_window)
        user_layout.addWidget(delete_account_btn)
        
        # Add sections to the card layout
        card_layout.addLayout(user_layout)
        card_layout.addLayout(theme_layout)
        card_layout.addLayout(notify_layout)
        card_layout.addLayout(history_layout)

        card_layout.addStretch()

        # Place the card inside a vertical layout in the scroll content
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(card)
        content_layout.addStretch()

        # Theme section title
        theme_section = QLabel()
        theme_section.setText("Themes")
        theme_section.setObjectName("SectionDivider")
        theme_layout.addWidget(theme_section)

        theme_selector = QComboBox()
        theme_selector.addItems(["Default", "Dark", "Light", "Dracula", "Cyberpunk"])
        theme_selector.setObjectName("themeDropDown")
        theme_selector.currentTextChanged.connect(self.changeTheme)
        theme_layout.addWidget(theme_selector)

        # Notifications section title
        notify_section = QLabel()
        notify_section.setText("Notifications")
        notify_section.setObjectName("SectionDivider")
        notify_layout.addWidget(notify_section)

        # Notifications: mute checkbox
        notify_layout.addSpacing(16)
        notify_layout.addWidget(self.mute_notifications_checkbox)

        # --- History & Cache Section ---
        history_section = QLabel()
        history_section.setText("History & Cache")
        history_section.setObjectName("SectionDivider")
        history_layout.addWidget(history_section)

        # Reset scan history button
        history_layout.addSpacing(16)
        reset_scan_btn = QPushButton("Reset scan history")
        reset_scan_btn.setObjectName("resetScanHistoryBtn")
        reset_scan_btn.setFont(QFont("Segoe UI", 11))
        reset_scan_btn.setMinimumHeight(40)
        reset_scan_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        reset_scan_btn.setFixedWidth(220)
        reset_scan_btn.clicked.connect(self.reset_scan_history)
        history_layout.addWidget(reset_scan_btn)

        # Reset navigation history button
        history_layout.addSpacing(16)
        reset_nav_btn = QPushButton("Reset navigation history")
        reset_nav_btn.setObjectName("resetNavigationHistoryBtn")
        reset_nav_btn.setFont(QFont("Segoe UI", 11))
        reset_nav_btn.setMinimumHeight(40)
        reset_nav_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        reset_nav_btn.setFixedWidth(220)
        reset_nav_btn.clicked.connect(self.reset_navigation_history)
        history_layout.addWidget(reset_nav_btn)

    def changeTheme(self, theme_name):
        print(theme_name)
        with open("src/gui/Style_Sheet/themes.json", "r") as f:
            themes = json.load(f)
            current_theme_data = themes.get(theme_name)

        with open("src/gui/Style_Sheet/SettingsStyle.qss", "r") as f:
            template_content = f.read()

        final_style = template_content.format(**current_theme_data)

        QApplication.instance().setStyleSheet(final_style)

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

    def open_change_username_window(self):
        self.username_window = ChangeUsernameWindow(self.user_name, self.sidebar)
        self.username_window.show()

    def open_change_password_window(self):
        self.password_window = ChangePasswordWindow(self.user_name, self.sidebar)
        self.password_window.show()

    def open_delete_account_window(self):
        self.delete_account_window = DeleteAccountWindow(self.user_name, self.sidebar)
        self.delete_account_window.show()

    # --- History & Cache reset ---
    def _vt_cache_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "..", "VT_Cache")

    def reset_scan_history(self):
        cache_dir = self._vt_cache_dir()
        try:
            os.makedirs(cache_dir, exist_ok=True)
            scanner_cache = os.path.join(cache_dir, "scanner_cache.json")
            vt_history = os.path.join(cache_dir, "vt_history.jsonl")
            scan_requests = os.path.join(cache_dir, "scan_requests.jsonl")

            # Reset scanner cache
            if os.path.exists(scanner_cache):
                with open(scanner_cache, "w", encoding="utf-8") as f:
                    json.dump({"last_call": 0, "cache": {}}, f)

            # Clear history & request logs
            for path in (vt_history, scan_requests):
                if os.path.exists(path):
                    with open(path, "w", encoding="utf-8"):
                        pass
        except Exception:
            pass

    def reset_navigation_history(self):
        cache_dir = self._vt_cache_dir()
        logging_file = os.path.join(cache_dir, "logging_mode_history.jsonl")
        # Reset logging history
        try:
            if os.path.exists(logging_file):
                with open(logging_file, "w", encoding="utf-8"):
                    pass
        except Exception:
            pass

