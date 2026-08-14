"""
GUI-side scanner service.

The actual scan logic (WHOIS/DNS/TLS/HTTP heuristics) now runs in the backend
container (see backend/services/scanner_service.py) — this module keeps the same
public names the GUI already imports (`risk_score_to_verdict`, `ScannerScanThread`)
so Scanner_Window.py / main_window.py need no changes beyond what already talks to
these names. ScannerScanThread.run() now calls the backend over HTTP instead of
running the scan in-process.
"""

import json
import os
from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal
from src.logic import api_client
from src.SQL_Alchemy.database_manager import DatabaseManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "..", "VT_Cache")
CACHE_FILE = os.path.join(CACHE_DIR, "scanner_cache.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "vt_history.jsonl")
_STATE_MEMO = {"last_call": 0, "cache": {}}

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


def cache_key(kind: str, target: str) -> str:
    """Generate cache key for scanner results"""
    if kind == "url":
        norm = (
            target
            if target.lower().startswith(("http://", "https://"))
            else f"http://{target}"
        )
        return f"url:{norm}"
    return f"{kind}:{target}"


def append_history(
    kind: str,
    target: str,
    verdict: str,
    stats: dict,
    source: str,
    userName: str = "N/A",
) -> None:
    """Log scan results to history file and database"""
    now = datetime.now()

    entry = {
        "ts": now.isoformat(),
        "kind": kind,
        "target": target,
        "verdict": verdict,
        "stats": stats,
        "source": source,
        "user": userName,
    }

    try:
        # Log to JSONL file
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    # Log to SQLAlchemy DB
    DatabaseManager.log_address_scan(target, verdict, userName)


def _load_scanner_state() -> dict:
    """Load scanner cache state"""
    global _STATE_MEMO
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if isinstance(state, dict):
                state.setdefault("last_call", 0)
                _STATE_MEMO = state
                return state
    except Exception:
        pass
    return dict(_STATE_MEMO)


def _save_scanner_state(state: dict) -> None:
    """Save scanner cache state"""
    global _STATE_MEMO
    state_to_save = dict(state)
    state_to_save.setdefault("cache", {})

    for key, cached_entry in state_to_save["cache"].items():
        if isinstance(cached_entry.get("ts"), datetime):
            cached_entry["ts"] = cached_entry["ts"].isoformat()

    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f)
    os.replace(tmp, CACHE_FILE)
    _STATE_MEMO = state


def prune_stale_cache_entries(max_age_days: int) -> int:
    """Remove cache entries older than max_age_days. Returns count removed."""
    if max_age_days <= 0:
        return 0

    state = _load_scanner_state()
    cache = state.get("cache", {})
    if not cache:
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    for key in list(cache.keys()):
        ts_str = (cache[key] or {}).get("ts", "")
        try:
            entry_ts = datetime.fromisoformat(ts_str)
        except Exception:
            continue
        if entry_ts < cutoff:
            del cache[key]
            removed += 1

    if removed > 0:
        _save_scanner_state(state)
    return removed


def risk_score_to_verdict(risk_score: int) -> str:
    if risk_score >= 60:
        return "MALICIOUS"
    elif risk_score >= 51:
        return "DANGEROUS"
    elif risk_score >= 41:
        return "SUSPICIOUS"
    elif risk_score >= 31:
        return "CAUTION"
    elif risk_score >= 21:
        return "NEUTRAL"
    elif risk_score >= 11:
        return "SAFE"
    else:
        return "SECURE"


class ScannerScanThread(QThread):
    result = Signal(dict)
    tick = Signal(int)

    def __init__(self, kind: str, target: str, userName: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.target = target
        self.userName = userName

    def run(self):
        try:
            self.tick.emit(0)
            payload = api_client.scan_local(self.kind, self.target, self.userName)
            self.result.emit(payload)
        except api_client.BackendUnavailable as e:
            self.result.emit({"ok": False, "message": f"Backend unavailable: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": f"Scanner error: {e}"})
