import os
import sys
import json
from datetime import datetime

# The `scanner/` package uses absolute imports internally (`from features.whois
# import ...`, `from scoring.rules_whois import ...`), so — same as the original
# src/logic/scanner_service.py — the `scanner/` directory itself (not its parent)
# must be on sys.path for those imports to resolve.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)
_SCANNER_DIR = os.path.join(_REPO_ROOT, "scanner")

if _SCANNER_DIR not in sys.path:
    sys.path.insert(0, _SCANNER_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scanner import scan_domain  # noqa: E402

from backend.db.database_manager import DatabaseManager  # noqa: E402

# VT_CACHE_DIR is env-configurable (default keeps the original relative layout for
# native/dev use) so the container can point it at a mounted volume instead.
_DEFAULT_CACHE_DIR = os.path.join(_BACKEND_DIR, "VT_Cache")
CACHE_DIR = os.getenv("VT_CACHE_DIR", _DEFAULT_CACHE_DIR)
CACHE_FILE = os.path.join(CACHE_DIR, "scanner_cache.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "vt_history.jsonl")
_STATE_MEMO = {"last_call": 0, "cache": {}}

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
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    DatabaseManager.log_address_scan(target, verdict, userName)


def _load_scanner_state() -> dict:
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
    if risk_score >= 60:
        return "MALICIOUS"
    elif risk_score >= 50:
        return "DANGEROUS"
    elif risk_score >= 40:
        return "SUSPICIOUS"
    elif risk_score >= 30:
        return "CAUTION"
    elif risk_score >= 20:
        return "NEUTRAL"
    elif risk_score >= 10:
        return "SAFE"
    else:
        return "SECURE"


def run_scan(kind: str, target: str, userName: str) -> dict:
    """
    Synchronous local scan — same logic that used to live in
    ScannerScanThread.run(), minus the QThread/Signal plumbing. Flask route
    handlers call this directly and return the dict as the JSON response.
    """
    try:
        # 0) Cache check
        state = _load_scanner_state()
        cache = state.get("cache", {})
        key = cache_key(kind, target)

        cached = cache.get(key)
        if cached:
            stats = cached.get("stats", {}) or {}
            verdict = cached.get("verdict", "UNKNOWN")
            risk_score = cached.get("risk_score", 0)
            signals = cached.get("signals", [])

            state["last_call"] = datetime.now().isoformat()
            _save_scanner_state(state)

            append_history(kind, target, verdict, stats, source="cache", userName=userName)
            return {
                "ok": True,
                "message": "cache",
                "stats": stats,
                "verdict": verdict,
                "kind": kind,
                "target": target,
                "risk_score": risk_score,
                "signals": signals,
            }

        # 1) Run the scanner
        scan_result = scan_domain(target)

        risk_score = scan_result.get("total_risk_score", 0)
        verdict = risk_score_to_verdict(risk_score)
        signals = scan_result.get("signals", [])

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
            "ts": datetime.now().isoformat(),
        }
        state["last_call"] = datetime.now().isoformat()
        _save_scanner_state(state)

        append_history(kind, target, verdict, stats, source="scanner", userName=userName)

        return {
            "ok": True,
            "message": "OK",
            "stats": stats,
            "verdict": verdict,
            "kind": kind,
            "target": target,
            "risk_score": risk_score,
            "signals": signals,
        }

    except Exception as e:
        return {"ok": False, "message": f"Scanner error: {e}"}
