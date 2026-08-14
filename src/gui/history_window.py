import json
import os
from datetime import datetime

from PySide6 import QtGui
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QHBoxLayout,
)
from src.gui.BlackList_Window import BlackList_Window
from src.gui.main_window import show_scan_box, show_ai_overview_box
from src.gui.WhiteList_Window import WhiteList_Window
from src.gui.model_download_dialog import ModelDownloadDialog
from src.logic import api_client
from src.logic.vt_service import (
    add_entry_to_blacklist,
    add_entry_to_whitelist,
    delete_blackList_entry,
    delete_history_entry,
    delete_whiteList_entry,
    get_sorted_history,
)
from src.logic.llm_service import (
    LLMExplainThread,
    get_cached_ai_overview,
    model_is_downloaded,
)
from PySide6.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout

"""
TO BE ADDED:
 * SORTING
 * COPY OPTION
 * IMPROVE SELECTION APPEARANCE
 * AUTOMATIC CACHE DELETION (AFTER CERTAIN TIME)
 * MANUAL ENTRY DELETION
 * MAYBE BEING ABLE TO VIEW ADDITIONAL ENTRY INFO BY CLICKING ON AN ENTRY (e.g. detailed VT results)
"""


class History_Window(QWidget):
    def __init__(self, user_name: str, sidebar_reference=None):
        super().__init__()
        self.user_name = user_name
        self.sidebar = sidebar_reference
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

        # Settings file path
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SETTINGS_FILE = os.path.join(BASE_DIR, "..", "VT_Cache", "settings.json")

        # -- Title --
        title = QLabel(f"History Log")
        title.setObjectName("TitleTables")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # To make the filters persirst
        self._filters: list[QLineEdit] = []
        self._filter_values: list[str] = ["", "", "", ""]  

        filter_bar = QWidget()
        self._filter_layout = QHBoxLayout(filter_bar)
        self._filter_layout.setContentsMargins(0, 2, 0, 2)
        self._filter_layout.setSpacing(4)

        column_labels = ["Timestamp", "Kind", "Target", "Verdict"]
        for col_idx, col_label in enumerate(column_labels):
            edit = QLineEdit()
            edit.setPlaceholderText(f"{col_label}...")
            edit.setClearButtonEnabled(True)
            edit.setVisible(False)  # hidden until activated
            edit.textChanged.connect(self._apply_filters)
            edit.returnPressed.connect(lambda idx=col_idx: self._commit_filter(idx))
            self._filters.append(edit)
            self._filter_layout.addWidget(edit)

        layout.addWidget(filter_bar)
        self._filter_bar = filter_bar

        # -- Table --
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setSortingEnabled(True)
        self.table.setColumnWidth(0, 25)
        self.table.verticalHeader().setMinimumWidth(30)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Kind", "Target", "Verdict"])

        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(self._header_context_menu)
        layout.addWidget(self.table)

        # Create reset button
        self.corner_btn = QPushButton("-", self.table)
        self.corner_btn.setFixedSize(24, 30)
        self.update_corner()
        self.corner_btn.clicked.connect(self.reset_scan_history)

        # -- Table Styling  --
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)

        # Keep filter bar widths in sync with column widths
        self.table.horizontalHeader().sectionResized.connect(self._sync_filter_widths)

        # -- Load Table --
        self.load_history()

        # -- Options in the table --
        self.table.cellClicked.connect(self.show_options)

        # Start periodic refresh
        self._refresh_timer.start()

    def _header_context_menu(self, pos):
        col = self.table.horizontalHeader().logicalIndexAt(pos)
        if col < 0:
            return

        menu = QMenu(self)

        search_action = menu.addAction("Search")
        asc_action = menu.addAction("Sort Ascending")
        desc_action = menu.addAction("Sort Descending")
        if self._filter_values[col]:
            font = search_action.font()
            font.setBold(True)
            search_action.setFont(font)

        selected = menu.exec_(self.table.horizontalHeader().mapToGlobal(pos))
        if selected is None:
            return

        if selected == search_action:
            self._toggle_search(col)
        elif selected == asc_action:
            self.table.sortItems(col, Qt.SortOrder.AscendingOrder)
        elif selected == desc_action:
            self.table.sortItems(col, Qt.SortOrder.DescendingOrder)

    def _toggle_search(self, col: int):
        edit = self._filters[col]
        edit.blockSignals(True)
        edit.setText(self._filter_values[col])
        edit.blockSignals(False)
        edit.setVisible(True)
        self._sync_filter_widths()
        edit.setFocus()
        edit.selectAll()

    def _commit_filter(self, col: int):
        edit = self._filters[col]

        # This keeps the text that was written when hide
        self._filter_values[col] = edit.text()
        edit.setVisible(False)
        self._apply_filters()

    def _apply_filters(self):
        terms = []
        for col, edit in enumerate(self._filters):
            if edit.isVisible():
                self._filter_values[col] = edit.text()
            terms.append(self._filter_values[col].strip().lower())

        for row in range(self.table.rowCount()):
            visible = True
            for col, term in enumerate(terms):
                if not term:
                    continue
                item = self.table.item(row, col)
                if term not in (item.text() if item else "").lower():
                    visible = False
                    break
            self.table.setRowHidden(row, not visible)

    def _sync_filter_widths(self):
        for col, edit in enumerate(self._filters):
            edit.setFixedWidth(self.table.columnWidth(col))

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

    def reset_scan_history(self):
        try:
            api_client.reset_history()
        except api_client.BackendUnavailable:
            pass

    # -- Function to load rows in the table --
    def load_history(self):
        vbar = self.table.verticalScrollBar()
        previous_scroll = vbar.value()

        self.table.setSortingEnabled(False)

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
                "MALICIOUS": "#dc2626",
                "DANGEROUS": "#ef4444",
                "SUSPICIOUS": "#f97316",
                "CAUTION": "#eab308",
                "NEUTRAL": "#94a3b8",
                "SAFE": "#22c55e",
                "SECURE": "#059669",
                "BLOCK": "#ef4444",
                "WHITELISTED": "#3b82f6",
                "BLACKLISTED": "#991b1b",
                "TEST": "#3667ab",
            }.get(verdict, "#64748b")

            formatted_ts_item = QTableWidgetItem(formatted_ts)
            formatted_ts_item.setData(Qt.UserRole, ts)
            self.table.setItem(row, 0, formatted_ts_item)

            kind_item = QTableWidgetItem(kind)
            kind_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop
            )
            self.table.setItem(row, 1, kind_item)

            target_item = QTableWidgetItem(target)
            target_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop
            )
            self.table.setItem(row, 2, target_item)

            verdict_item = QTableWidgetItem(verdict)
            verdict_item.setBackground(QtGui.QColor(color))

            verdict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, verdict_item)

        self.table.setSortingEnabled(True)

        # -- Column & Row size adjustments  --
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(2, 400)  # Target
        self.table.setColumnWidth(3, 80)
        # self.table.resizeRowsToContents()
        self._apply_filters()
        self._sync_filter_widths()

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
            "user": self.user_name,
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
        menu.addAction("Copy")
        menu.addAction("View additional info")
        menu.addAction("AI Overview")
        menu.addAction("White List")
        menu.addAction("Black List")
        menu.addAction("Delete")

        # Get mouse position
        cursor_pos = self.mapToGlobal(
            self.table.viewport().mapFromGlobal(QCursor.pos())
        )
        selected = menu.exec_(cursor_pos)
        if selected is None:
            return

        action = selected.text()
        if action == "Copy":
            self.copy_target(row)
        elif action == "View additional info":
            self.view_additional_info(row)
        elif action == "AI Overview":
            self.view_ai_overview(row)
        elif action == "White List":
            self.addWhiteList(row)
        elif action == "Black List":
            self.addBlackList(row)
        elif action == "Delete":
            self.delete_item(row)

    def copy_target(self, row: int):
        target_item = self.table.item(row, 2)
        if not target_item:
            return
        target = target_item.text()
        if target:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(target)

    def view_ai_overview(self, row: int):
        target_item = self.table.item(row, 2)
        kind_item = self.table.item(row, 1)
        if not target_item or not kind_item:
            return

        target = target_item.text()
        kind = kind_item.text()
        if not target or not kind:
            return

        # If we already generated an overview for this target, show it instantly.
        cached = get_cached_ai_overview(kind, target)
        if cached:
            show_ai_overview_box(self, cached.get("explanation", ""), cached.get("recommendation", ""))
            return

        # Otherwise we need the underlying scan data to feed the model.
        scan = api_client.get_cached_scan(kind, target)
        if not scan:
            QMessageBox.warning(
                self, "AI Overview",
                "No scan data is available for this entry, so an AI overview cannot be generated.",
            )
            return

        if not model_is_downloaded():
            dlg = ModelDownloadDialog(self)
            if dlg.exec() != ModelDownloadDialog.Accepted:
                return

        verdict = scan.get("verdict", "UNKNOWN")
        stats = scan.get("stats", {}) or {"risk_score": scan.get("risk_score", 0)}
        signals = scan.get("signals", [])

        self._ai_loading_box = QDialog(self)
        self._ai_loading_box.setWindowTitle("AI Overview")
        self._ai_loading_box.setModal(True)
        self._ai_loading_box.setFixedWidth(360)

        layout = QVBoxLayout(self._ai_loading_box)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        loading_label = QLabel("Generating AI overview...\nthis may take a moment.")
        loading_label.setWordWrap(True)
        loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(loading_label)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._cancel_ai_overview)
        layout.addWidget(cancel_btn)

        self._ai_loading_box.show()

        self._llm_worker = LLMExplainThread(
            verdict, stats, signals, kind=kind, target=target, parent=self,
        )
        self._llm_worker.result.connect(self._on_ai_overview_result)
        self._llm_worker.start()

    def _cancel_ai_overview(self):
        # Detach the result handler so a late completion can't pop up after cancel.
        if getattr(self, "_llm_worker", None):
            try:
                self._llm_worker.result.disconnect(self._on_ai_overview_result)
            except Exception:
                pass
        if getattr(self, "_ai_loading_box", None):
            self._ai_loading_box.reject()
            self._ai_loading_box.deleteLater()
            self._ai_loading_box = None

    def _on_ai_overview_result(self, payload: dict):
        # Close the loading dialog before doing anything else.
        loading_box = self._ai_loading_box
        self._ai_loading_box = None
        if loading_box is not None:
            loading_box.accept()
            loading_box.deleteLater()

        # Properly retire the worker thread. run() has already returned by now,
        # so quit/wait return immediately; this just lets Qt clean up the QObject.
        worker = getattr(self, "_llm_worker", None)
        self._llm_worker = None
        if worker is not None:
            worker.quit()
            worker.wait(1000)
            worker.deleteLater()

        if not payload.get("ok"):
            QMessageBox.critical(self, "AI Error", payload.get("message", "Unknown error"))
            return

        show_ai_overview_box(
            self,
            payload.get("explanation", ""),
            payload.get("recommendation", ""),
        )

    def view_additional_info(self, row: int):
        target_item = self.table.item(row, 2)
        kind_item = self.table.item(row, 1)
        if not target_item or not kind_item:
            return

        target = target_item.text()
        kind = kind_item.text()
        if not target or not kind:
            return

        # Try to load from scanner cache
        cache_entry = api_client.get_cached_scan(kind, target)
        if cache_entry:
            verdict = cache_entry.get("verdict", "UNKNOWN")
            stats = cache_entry.get("stats", {}) or {
                "risk_score": cache_entry.get("risk_score", 0),
                "signal_count": len(cache_entry.get("signals", [])),
            }
            signals = cache_entry.get("signals", [])
            show_scan_box(self, verdict, stats, signals, silent=True)
            return

