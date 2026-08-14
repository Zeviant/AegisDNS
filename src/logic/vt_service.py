"""
GUI-side VirusTotal / history / whitelist / blacklist service.

All actual I/O (VirusTotal API calls, JSONL reads/writes) now happens in the
backend container (see backend/services/vt_service.py) — this module keeps the
same public names the GUI already imports so history_window.py, WhiteList_Window.py,
BlackList_Window.py, Scanner_Window.py and main_window.py need no changes to their
imports, only what happens inside these functions changed (HTTP call instead of
local file access).
"""
import time

from PySide6.QtCore import QThread, Signal

from src.logic import api_client
from src.logic.api_client import classify_kind, normalize_target  # re-exported, unchanged


def get_sorted_history(user_name: str) -> list[dict]:
    return api_client.get_history(user_name)


def add_entry_to_whitelist(entry: dict) -> None:
    api_client.add_whitelist_entry(entry)


def add_entry_to_blacklist(entry: dict) -> None:
    api_client.add_blacklist_entry(entry)


def get_sorted_white_list(user_name: str) -> list[dict]:
    return api_client.get_whitelist(user_name)


def get_sorted_black_list(user_name: str) -> list[dict]:
    return api_client.get_blacklist(user_name)


def delete_history_entry(user_name: str, ts: str, target: str) -> None:
    api_client.delete_history_entry(user_name, ts, target)


def delete_whiteList_entry(user_name: str, ts: str, target: str) -> None:
    api_client.delete_whitelist_entry(user_name, ts, target)


def delete_blackList_entry(user_name: str, ts: str, target: str) -> None:
    api_client.delete_blacklist_entry(user_name, ts, target)


# --- Deep Scan Thread ---
class VTDeepScanThread(QThread):
    result = Signal(dict)
    tick = Signal(int)

    def __init__(self, kind: str, target: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.target = target

    def run(self):
        try:
            # The backend enforces the rate limit and, if still cooling down,
            # replies immediately with {"reason": "cooldown", "wait_seconds": N}
            # instead of blocking a request thread — count the wait down locally
            # (same tick-per-second UX as before) and retry.
            for _ in range(30):  # safety cap; cooldown is normally <=15s
                response = api_client.scan_deep(self.kind, self.target)
                if response.get("reason") == "cooldown":
                    wait = int(response.get("wait_seconds", 0))
                    while wait > 0:
                        self.tick.emit(wait)
                        time.sleep(1)
                        wait -= 1
                    self.tick.emit(0)
                    continue
                self.result.emit(response)
                return
            self.result.emit({"ok": False, "message": "Still on cooldown, please try again shortly."})
        except api_client.BackendUnavailable as e:
            self.result.emit({"ok": False, "message": f"Backend unavailable: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": f"Unexpected error: {e}"})
