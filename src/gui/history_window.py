from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt
from PySide6 import QtGui
from datetime import datetime
from src.logic.vt_service import get_sorted_history

''' 
TO BE ADDED:
 * SORTING
 * SIDEBAR CONNECTION
 * BLACKLIST/WHITELIST FUNCTIONALITY
 * FIX RESOLUTION
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

        layout = QVBoxLayout(self)

        # -- Title --
        title = QLabel(f"History Log")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            padding: 10px;
            color: #ffffff;
        """)
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

        self.table.setStyleSheet("""
        QTableWidget {
            background-color: #2b2b2b;
            alternate-background-color: #333333;
            color: #f0f0f0;
            gridline-color: #444444;
            border: 1px solid #3a3a3a;
            font-size: 14px;
            selection-background-color: #555555;
            selection-color: white;
        }
        QHeaderView::section {
            background-color: #1f2937;
            color: #e5e7eb;
            padding: 6px;
            border: none;
            font-weight: bold;
        }
        """)

        # -- Load Table --
        self.load_history()

    def load_history(self):
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
                "SAFE": "#2ecc71"
            }.get(verdict, "#7f8c8d")

            self.table.setItem(row, 0, QTableWidgetItem(formatted_ts))
            self.table.setItem(row, 1, QTableWidgetItem(kind))
            self.table.setItem(row, 2, QTableWidgetItem(target))

            verdict_item = QTableWidgetItem(verdict)
            verdict_item.setBackground(QtGui.QColor(color))

            verdict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, verdict_item)

        self.table.resizeColumnsToContents()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = History_Window("Ben")
    window.show()
    sys.exit(app.exec())
