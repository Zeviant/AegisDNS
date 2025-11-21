from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, QTimer
from PySide6 import QtGui
from datetime import datetime
from src.logic.vt_service import get_sorted_history

''' 
TO BE ADDED:
 * SORTING
 * BLACKLIST/WHITELIST FUNCTIONALITY
 * IMPROVE SELECTION APPEARANCE
 * AUTOMATIC CACHE DELETION (AFTER CERTAIN TIME)
 * MANUAL ENTRY DELETION
 * MAYBE BEING ABLE TO VIEW ADDITIONAL ENTRY INFO BY CLICKING ON AN ENTRY (e.g. detailed VT results)
'''

class History_Window(QWidget):
    def __init__(self, user_name: str):
        super().__init__()
        self.user_name = user_name
        self.setWindowTitle(f"History Log - {self.user_name}")
        self.resize(1024, 682)

        # Timer for live updates
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(3000)
        self._refresh_timer.timeout.connect(self.load_history)

        layout = QVBoxLayout(self)

        # Load Sheet Style
        with open("src/gui/Style_Sheet/table_style.qss", "r") as f:
            self.setStyleSheet(f.read())

        # -- Title --
        title = QLabel(f"History Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # -- Table --
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Kind", "Target", "Verdict"])
        layout.addWidget(self.table)

        # -- Table Styling  --
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)

        # Load table styling from QSS file
        with open("src/gui/Style_Sheet/table_style.qss", "r") as f:
            self.table.setStyleSheet(f.read())

        # -- Load Table --
        self.load_history()

        # Start periodic refresh
        self._refresh_timer.start()

    def load_history(self):
        vbar = self.table.verticalScrollBar()
        previous_scroll = vbar.value()

        entries = get_sorted_history(self.user_name)
        self.table.setRowCount(0)

        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # -- Timestamp formatting --
            ts = entry.get("ts", "")
            try:
                dt = datetime.fromisoformat(ts)
                formatted_ts = dt.strftime("%b %d, %Y %H:%M:%S")
            except Exception:
                formatted_ts = ts
            
            # -- Other columns --
            kind = entry.get("kind", "")
            target = entry.get("target", "")
            verdict = entry.get("verdict", "").upper()

            color = {
                "BLOCK": "#e74c3c",
                "CAUTIOUS": "#f18b0f",
                "SAFE": "#2ecc71",
                "TEST": "#3667ab"
            }.get(verdict, "#7f8c8d")

            self.table.setItem(row, 0, QTableWidgetItem(formatted_ts))
            self.table.setItem(row, 1, QTableWidgetItem(kind))
            
            target_item = QTableWidgetItem(target)
            target_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.table.setItem(row, 2, target_item)

            verdict_item = QTableWidgetItem(verdict)
            verdict_item.setBackground(QtGui.QColor(color))

            verdict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, verdict_item)

        # -- Column & Row size adjustments  --
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(2, 400) # Target
        self.table.resizeRowsToContents()

        QTimer.singleShot(0, lambda: vbar.setValue(previous_scroll))
