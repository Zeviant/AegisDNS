from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton, QHeaderView
from PySide6.QtCore import Qt, QTimer
from PySide6 import QtGui
from datetime import datetime
from src.logic.backend_server import get_sorted_logs
import json


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

        # -- Title --
        title = QLabel(f"Navigation Logs")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # -- Table --
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Target", "Action"])
        layout.addWidget(self.table)

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

    def load_logs(self):
        vbar = self.table.verticalScrollBar()
        previous_scroll = vbar.value()

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
            target_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.table.setItem(row, 1, target_item)

            # -- SCAN button  --
            scan_btn = QPushButton("SCAN")
            scan_btn.setObjectName("ScanButton")
            scan_btn.clicked.connect(lambda checked, addr=target: self.scan_address(addr))
            
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addStretch()
            btn_layout.addWidget(scan_btn)
            btn_layout.addStretch()
            self.table.setCellWidget(row, 2, btn_container)
            
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
        if hasattr(main_window, 'input_edit'):
            # Set address & scan
            main_window.input_edit.setText(address)
            main_window.on_ok()

