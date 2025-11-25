from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView, QMenu
from PySide6.QtCore import Qt, QTimer
from PySide6 import QtGui
from PySide6.QtGui import QCursor
from datetime import datetime
from src.logic.vt_service import get_sorted_history, delete_history_entry, add_entry_to_whitelist, delete_whiteList_entry, delete_blackList_entry, add_entry_to_blacklist   
from src.gui.WhiteList_Window import WhiteList_Window
from src.gui.BlackList_Window import BlackList_Window

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

        # Instace for whiteblacklist window
        self.white_list_window = WhiteList_Window(user_name)
        self.black_list_window = BlackList_Window(user_name)
        
        layout = QVBoxLayout(self)

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

        # -- Options in the table --
        self.table.cellClicked.connect(self.show_options)

        # Start periodic refresh
        self._refresh_timer.start()

    # -- Function to load rows in the table --
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

            formatted_ts_item = QTableWidgetItem(formatted_ts)
            formatted_ts_item.setData(Qt.UserRole, ts)
            self.table.setItem(row, 0, formatted_ts_item)

            kind_item = QTableWidgetItem(kind)
            kind_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            self.table.setItem(row, 1, QTableWidgetItem(kind_item))
            
            target_item = QTableWidgetItem(target)
            target_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            self.table.setItem(row, 2, target_item)

            verdict_item = QTableWidgetItem(verdict)
            verdict_item.setBackground(QtGui.QColor(color))

            verdict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, verdict_item)

        # -- Column & Row size adjustments  --
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(2, 400) # Target
        self.table.resizeRowsToContents()

        # Singleshot applies value afetr Qt finishes resizing/reloading table
        QTimer.singleShot(0, lambda: vbar.setValue(previous_scroll))

    # -- Delete Item of the Table --
    def delete_item(self, row):
        # Get raw timestamp from data so it matches the entry in the jsonl
        ts_item = self.table.item(row, 0)
        raw_ts = ts_item.data(Qt.UserRole)

        # Target column 
        target = self.table.item(row, 2).text()

        # Remove entry from JSONL
        delete_history_entry(self.user_name, raw_ts, target)
        delete_whiteList_entry(self.user_name, raw_ts, target)
        delete_blackList_entry(self.user_name, raw_ts, target)

        # Remove entry form UI
        self.table.removeRow(row)
        self.white_list_window.delete_item(row)
        self.black_list_window.delete_item(row)

    # -- Add Item to the White List --
    def get_entry_from_row(self, row):
        ts_item = self.table.item(row, 0)
        raw_ts = ts_item.data(Qt.UserRole)

        entry = {
            "ts": raw_ts,
            "kind": self.table.item(row, 1).text(),
            "target": self.table.item(row, 2).text(),
            "verdict": self.table.item(row, 3).text(),
            "user": self.user_name
        }

       
        return entry
    
    def addWhiteList(self, row): 
        entry = self.get_entry_from_row(row)
        
        # Check if entry is already in the json
        if self.white_list_window.check_entry(entry):
            print("Entry already in whitelist table, skipping.")
            return
        
        add_entry_to_whitelist(entry)

    def addBlackList(self, row): 
            entry = self.get_entry_from_row(row)
            
            # Check if entry is already in the json
            if self.black_list_window.check_entry(entry):
                print("Entry already in whitelist table, skipping.")
                return
            
            add_entry_to_blacklist(entry)

    # -- Menu of options --
    def show_options(self, row, col): 
        menu = QMenu(self.table)
        with open("src/gui/Style_Sheet/QMenu_Style.qss") as f: 
            style_str = f.read()
        
        menu.setStyleSheet(style_str)

        menu.addAction("White List")
        menu.addAction("Black List")
        menu.addAction("Delete")

        # Get mouse position
        cursor_pos = self.mapToGlobal(self.table.viewport().mapFromGlobal(QCursor.pos()))
        selected = menu.exec_(cursor_pos)
        if selected is None:
            return   

        match selected.text(): 
            case "White List": 
                self.addWhiteList(row)
                
            case "Black List": 
                self.addBlackList(row)

            case "Delete": 
                self.delete_item(row)
        