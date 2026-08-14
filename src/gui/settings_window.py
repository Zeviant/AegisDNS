from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QFrame, QPushButton, QSizePolicy, QStyle, QStyleOption, QStyleOptionButton, QListWidget, QComboBox, QScrollArea, QSpinBox, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor
import os
import json
from src.gui.change_password_window import ChangePasswordWindow
from src.gui.change_username_window import ChangeUsernameWindow
from src.gui.delete_account_window import DeleteAccountWindow
from src.gui.log_window import Log_Window
from src.logic import api_client
from PySide6.QtWidgets import QApplication
from src.logic.settings_service import get_setting, set_setting
from src.gui.main_window import apply_theme
from src.logic.vt_service import get_sorted_history
from src.logic.backend_server import get_sorted_logs

import csv
from datetime import datetime

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
        saved_theme = get_setting(self.user_name, "theme", "Default")
        if saved_theme in ["Default", "Dark", "Light", "Dracula", "Cyberpunk"]:
            theme_selector.setCurrentText(saved_theme)
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

        # Cache invalidation: enable + day threshold
        history_layout.addSpacing(16)
        cache_row = QHBoxLayout()
        cache_row.setSpacing(8)

        self.cache_invalidation_checkbox = CheckBoxWithCheckmark(
            "On login, delete cached entries older than"
        )
        self.cache_invalidation_checkbox.setFont(QFont("Segoe UI", 11))
        self.cache_invalidation_checkbox.setChecked(
            bool(get_setting(self.user_name, "cache_invalidation_enabled", True))
        )
        self.cache_invalidation_checkbox.toggled.connect(self.on_cache_invalidation_toggled)
        cache_row.addWidget(self.cache_invalidation_checkbox)

        self.cache_days_spinbox = QSpinBox()
        self.cache_days_spinbox.setRange(1, 365)
        self.cache_days_spinbox.setValue(int(get_setting(self.user_name, "cache_max_age_days", 30)))
        self.cache_days_spinbox.setFixedWidth(70)
        self.cache_days_spinbox.setEnabled(self.cache_invalidation_checkbox.isChecked())
        self.cache_days_spinbox.valueChanged.connect(self.on_cache_days_changed)
        cache_row.addWidget(self.cache_days_spinbox)

        days_label = QLabel("days")
        days_label.setFont(QFont("Segoe UI", 11))
        cache_row.addWidget(days_label)
        cache_row.addStretch()

        history_layout.addLayout(cache_row)

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

        # Export scan history to CSV
        history_layout.addSpacing(16)
        export_history_btn = QPushButton("Export scan history to CSV")
        export_history_btn.setObjectName("exportHistoryBtn")
        export_history_btn.setFont(QFont("Segoe UI", 11))
        export_history_btn.setMinimumHeight(40)
        export_history_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        export_history_btn.setFixedWidth(260)
        export_history_btn.clicked.connect(self.export_history_to_csv)
        history_layout.addWidget(export_history_btn)

        # Export navigation log to CSV
        history_layout.addSpacing(16)
        export_nav_btn = QPushButton("Export navigation log to CSV")
        export_nav_btn.setObjectName("exportNavigationBtn")
        export_nav_btn.setFont(QFont("Segoe UI", 11))
        export_nav_btn.setMinimumHeight(40)
        export_nav_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        export_nav_btn.setFixedWidth(260)
        export_nav_btn.clicked.connect(self.export_navigation_to_csv)
        history_layout.addWidget(export_nav_btn)

    def changeTheme(self, theme_name):
        apply_theme(theme_name)
        set_setting(self.user_name, "theme", theme_name)

    def load_mute_setting(self) -> bool:
        return get_setting(self.user_name, "mute_notifications", False)

    # Checkbox toggle
    def on_mute_toggled(self, checked: bool):
        set_setting(self.user_name, "mute_notifications", checked)

    def on_cache_invalidation_toggled(self, checked: bool):
        set_setting(self.user_name, "cache_invalidation_enabled", checked)
        self.cache_days_spinbox.setEnabled(checked)

    def on_cache_days_changed(self, value: int):
        set_setting(self.user_name, "cache_max_age_days", int(value))

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
    def reset_scan_history(self):
        try:
            api_client.reset_history()
        except api_client.BackendUnavailable:
            pass

    def reset_navigation_history(self):
        try:
            api_client.reset_logs()
        except api_client.BackendUnavailable:
            pass

    # --- CSV exports ---
    def _format_log_timestamp(self, raw) -> str:
        try:
            ts = int(raw)
            if ts > 1e12:  # milliseconds → seconds
                ts = ts // 1000
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(raw) if raw else ""

    def _format_history_timestamp(self, raw: str) -> str:
        try:
            return datetime.fromisoformat(raw).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return raw or ""

    def _ask_save_path(self, suggested_name: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", suggested_name, "CSV files (*.csv)"
        )
        return path or None

    def export_history_to_csv(self):
        entries = get_sorted_history(self.user_name)
        if not entries:
            QMessageBox.information(self, "Export scan history", "No history entries to export.")
            return

        path = self._ask_save_path(f"scan_history_{self.user_name}.csv")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "kind", "target", "verdict", "risk_score", "source"])
                for e in entries:
                    stats = e.get("stats", {}) or {}
                    writer.writerow([
                        self._format_history_timestamp(e.get("ts", "")),
                        e.get("kind", ""),
                        e.get("target", ""),
                        e.get("verdict", ""),
                        stats.get("risk_score", ""),
                        e.get("source", ""),
                    ])
            QMessageBox.information(self, "Export scan history", f"Exported {len(entries)} entries to:\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Export failed", str(ex))

    def export_navigation_to_csv(self):
        entries = get_sorted_logs(self.user_name)
        if not entries:
            QMessageBox.information(self, "Export navigation log", "No navigation entries to export.")
            return

        path = self._ask_save_path(f"navigation_log_{self.user_name}.csv")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "mode", "url", "verdict"])
                for e in entries:
                    writer.writerow([
                        self._format_log_timestamp(e.get("timestamp")),
                        e.get("mode", ""),
                        e.get("indicator", "") or e.get("url", ""),
                        e.get("verdict", ""),
                    ])
            QMessageBox.information(self, "Export navigation log", f"Exported {len(entries)} entries to:\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Export failed", str(ex))

