import os, json
from datetime import datetime
from PySide6.QtCore import QThread, Signal
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCANNER_PARENT = os.path.join(BASE_DIR, "..", "..")
SCANNER_DIR = os.path.join(SCANNER_PARENT, "scanner")


if SCANNER_DIR not in sys.path:
    sys.path.insert(0, SCANNER_DIR)

if SCANNER_PARENT not in sys.path:
    sys.path.insert(0, SCANNER_PARENT)

from scanner import scan_domain

from src.SQL_Alchemy.database_manager import DatabaseManager

CACHE_DIR = os.path.join(BASE_DIR, "..", "VT_Cache")
CACHE_FILE = os.path.join(CACHE_DIR, "scanner_cache.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "vt_history.jsonl")
_STATE_MEMO = {"last_call": 0, "cache": {}}

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_key(kind: str, target: str) -> str:
    """Generate cache key for scanner results"""
    if kind == "url":
        norm = target if target.lower().startswith(("http://", "https://")) else f"http://{target}"
        return f"url:{norm}"
    return f"{kind}:{target}"

def append_history(kind: str, target: str, verdict: str, stats: dict, source: str, userName: str = "N/A") -> None:
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

def risk_score_to_verdict(risk_score: int) -> str:
    if risk_score < 10:
        return "SAFE"
    elif risk_score < 20:
        return "CAUTION"
    else:
        return "BLOCK"

# --- Scanner Thread ---
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
            # 0) Cache check
            state = _load_scanner_state()
            cache = state.get("cache", {})
            key = cache_key(self.kind, self.target)
            
            cached = cache.get(key)
            if cached:
                stats = cached.get("stats", {}) or {}
                verdict = cached.get("verdict", "UNKNOWN")
                risk_score = cached.get("risk_score", 0)
                signals = cached.get("signals", [])
                
                state["last_call"] = datetime.now().isoformat()
                _save_scanner_state(state)
                
                append_history(self.kind, self.target, verdict, stats, source="cache", userName=self.userName)
                self.result.emit(
                    {
                        "ok": True,
                        "message": "cache",
                        "stats": stats,
                        "verdict": verdict,
                        "kind": self.kind,
                        "target": self.target,
                        "risk_score": risk_score,
                        "signals": signals,
                    }
                )
                return

            # 1) Run the scanner
            self.tick.emit(0)
            
            scan_result = scan_domain(self.target)
            
            # Extract results
            risk_score = scan_result.get("total_risk_score", 0)
            verdict = risk_score_to_verdict(risk_score)
            signals = scan_result.get("signals", [])
            
            # Create stats dict
            stats = {
                "risk_score": risk_score,
                "signal_count": len(signals),
            }
            
            # 2) Save to cache + history
            state = _load_scanner_state()
            state.setdefault("cache", {})
            state["cache"][key] = {
                "stats": stats,
                "verdict": verdict,
                "risk_score": risk_score,
                "signals": signals,
                "ts": datetime.now().isoformat()
            }
            state["last_call"] = datetime.now().isoformat()
            _save_scanner_state(state)
            
            append_history(self.kind, self.target, verdict, stats, source="scanner", userName=self.userName)
            
            self.result.emit(
                {
                    "ok": True,
                    "message": "OK",
                    "stats": stats,
                    "verdict": verdict,
                    "kind": self.kind,
                    "target": self.target,
                    "risk_score": risk_score,
                    "signals": signals,
                }
            )

        except Exception as e:
            self.result.emit({"ok": False, "message": f"Scanner error: {e}"})

