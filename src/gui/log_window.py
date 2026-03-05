import json
import os
from datetime import datetime

from PySide6 import QtGui
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from src.logic.backend_server import get_sorted_logs


class Log_Window(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
        self.setWindowTitle(f"Navigation Logs - {self.user_name}")
        self.resize(1024, 682)

        # Timer for live updates
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(3000)
        self._refresh_timer.timeout.connect(self.load_logs)

        layout = QVBoxLayout(self)

        # Settings file path
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SETTINGS_FILE = os.path.join(BASE_DIR, "..", "VT_Cache", "settings.json")

        # -- Title --
        title = QLabel(f"Navigation Logs")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # -- Table --
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setColumnWidth(0, 25)
        self.table.verticalHeader().setMinimumWidth(30)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Target", "Action"])
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Create reset button
        self.corner_btn = QPushButton("-", self.table)
        self.corner_btn.setFixedSize(24, 30)
        self.update_corner()
        self.corner_btn.clicked.connect(self.reset_navigation_history)

        # -- Table Styling  --
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)

        # -- Load Table --
        self.load_logs()

        # Start periodic refresh
        self._refresh_timer.start()

    def update_corner(self):
        corner_w = self.table.verticalHeader().width()
        corner_h = self.table.horizontalHeader().height()

        btn_w = self.corner_btn.width()
        btn_h = self.corner_btn.height()

        x = (corner_w - btn_w) // 2
        y = (corner_h - btn_h) // 2
        print(y)
        self.corner_btn.move(3, 3)
        self.corner_btn.raise_()

    def _vt_cache_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "..", "VT_Cache")

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

    def load_logs(self):
        vbar = self.table.verticalScrollBar()
        previous_scroll = vbar.value()

        self.table.setSortingEnabled(False)

        entries = get_sorted_logs(self.user_name)
        self.table.setRowCount(0)

        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # -- Timestamp formatting --
            timestamp = entry.get("timestamp", 0)
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                formatted_ts = dt.strftime("%b %d, %Y %H:%M:%S")
            except Exception:
                formatted_ts = str(timestamp) if timestamp else "N/A"

            # -- Target column --
            target = entry.get("indicator", "")

            timestamp_item = QTableWidgetItem(formatted_ts)
            self.table.setItem(row, 0, timestamp_item)

            target_item = QTableWidgetItem(target)
            target_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            self.table.setItem(row, 1, target_item)

            # -- SCAN button  --
            scan_btn = QPushButton("SCAN")
            scan_btn.setObjectName("ScanButton")
            scan_btn.clicked.connect(
                lambda checked, addr=target: self.scan_address(addr)
            )

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addStretch()
            btn_layout.addWidget(scan_btn)
            btn_layout.addStretch()
            self.table.setCellWidget(row, 2, btn_container)

        self.table.setSortingEnabled(True)
        # -- Column & Row size adjustments  --
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 420)
        self.table.resizeRowsToContents()

        QTimer.singleShot(0, lambda: vbar.setValue(previous_scroll))

    def scan_address(self, address: str):
        # Update sidebar menu
        self.sidebar.sideMenu.setCurrentRow(0)
        self.sidebar.sideMenuIcon.setCurrentRow(0)

        # Switch to main window
        self.sidebar.mainContent.setCurrentIndex(0)

        # Get the main window widget
        main_window = self.sidebar.mainContent.widget(0)
        if hasattr(main_window, "input_edit"):
            # Set address & scan
            main_window.input_edit.setText(address)
            main_window.on_ok()
