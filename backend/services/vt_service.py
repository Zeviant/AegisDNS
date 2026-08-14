import os
import time
import base64
import json
import ipaddress
import re
from datetime import datetime

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CACHE_DIR = os.path.join(_BACKEND_DIR, "VT_Cache")
CACHE_DIR = os.getenv("VT_CACHE_DIR", _DEFAULT_CACHE_DIR)
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_FILE = os.path.join(CACHE_DIR, "vt_cache.json")
HISTORY_FILE = os.path.join(CACHE_DIR, "vt_history.jsonl")
WHITELIST_FILE = os.path.join(CACHE_DIR, "vt_whiteList.jsonl")
BLACKLIST_FILE = os.path.join(CACHE_DIR, "vt_blackList.jsonl")
VIRUSTOTAL_RATELIMIT = 15
_STATE_MEMO = {"last_call": 0, "cache": {}}
_HISTORY_FILE_NOT_FOUND_WARNED = False
_WHITELIST_FILE_NOT_FOUND_WARNED = False
_BLACKLIST_FILE_NOT_FOUND_WARNED = False

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,63}\.?$"
)


def _load_state() -> dict:
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


def _save_state(state: dict) -> None:
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


def normalize_target(s: str) -> str:
    return s.strip().lower().rstrip(".")


def classify_kind(raw_text: str) -> tuple[str, str]:
    """
    Returns (kind, target):
      kind in {'url','domain','ip'}
      target is the normalized value to query
    """
    text = raw_text.strip()
    if text.lower().startswith(("http://", "https://")):
        return "url", text
    try:
        ipaddress.ip_address(text)
        return "ip", text
    except ValueError:
        pass
    if DOMAIN_RE.match(normalize_target(text)):
        return "domain", normalize_target(text)
    raise ValueError("Input is not a valid URL, domain, or IP.")


def url_to_vt_id(url: str) -> str:
    """VirusTotal URL ID is base64url of the URL without '=' padding."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")
    return b64.strip("=")


def get_sorted_history(user_name: str) -> list[dict]:
    global _HISTORY_FILE_NOT_FOUND_WARNED
    entries: list[dict] = []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("user") == user_name:
                    entries.append(entry)
    except FileNotFoundError:
        if not _HISTORY_FILE_NOT_FOUND_WARNED:
            print("HISTORY_FILE_NOT_FOUND")
            _HISTORY_FILE_NOT_FOUND_WARNED = True
    except Exception:
        print("HISTORY_FILE_ERROR")

    entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return entries


def add_entry_to_whitelist(entry):
    entry = dict(entry)
    entry["verdict"] = "whitelisted"
    with open(WHITELIST_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def add_entry_to_blacklist(entry):
    entry = dict(entry)
    entry["verdict"] = "blacklisted"
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_sorted_white_list(user_name: str) -> list[dict]:
    global _WHITELIST_FILE_NOT_FOUND_WARNED
    entries: list[dict] = []
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("user") == user_name:
                    entries.append(entry)
    except FileNotFoundError:
        if not _WHITELIST_FILE_NOT_FOUND_WARNED:
            print("WHITELIST_FILE_NOT_FOUND")
            _WHITELIST_FILE_NOT_FOUND_WARNED = True
    except Exception:
        print("WHITELIST_FILE_ERROR")

    entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return entries


def get_sorted_black_list(user_name: str) -> list[dict]:
    global _BLACKLIST_FILE_NOT_FOUND_WARNED
    entries: list[dict] = []
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("user") == user_name:
                    entries.append(entry)
    except FileNotFoundError:
        if not _BLACKLIST_FILE_NOT_FOUND_WARNED:
            print("BLACKLIST_FILE_NOT_FOUND")
            _BLACKLIST_FILE_NOT_FOUND_WARNED = True
    except Exception:
        print("BLACKLIST_FILE_ERROR")

    entries.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return entries


def _delete_entry(file_path: str, ts: str, target: str) -> None:
    kept_lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("ts") == ts and entry.get("target") == target:
                continue
            kept_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        for line in kept_lines:
            f.write(line)


def delete_history_entry(user_name: str, ts: str, target: str):
    _delete_entry(HISTORY_FILE, ts, target)


def delete_whiteList_entry(user_name: str, ts: str, target: str):
    _delete_entry(WHITELIST_FILE, ts, target)


def delete_blackList_entry(user_name: str, ts: str, target: str):
    _delete_entry(BLACKLIST_FILE, ts, target)


def _verdict_from_stats(stats: dict) -> str:
    mal = int(stats.get("malicious", 0))
    susp = int(stats.get("suspicious", 0))
    if mal > 3:
        return "BLOCK"
    elif mal > 0 or susp > 0:
        return "CAUTION"
    else:
        return "SAFE"


def deep_scan_cooldown_remaining() -> int:
    """Seconds left before another VirusTotal deep scan is allowed."""
    state = _load_state()
    last = float(state.get("last_call", 0) or 0)
    return int(max(0, VIRUSTOTAL_RATELIMIT - (time.time() - last)))


def run_deep_scan(kind: str, target: str) -> dict:
    """
    Synchronous VirusTotal deep scan — same logic that used to live in
    VTDeepScanThread.run(), minus the QThread/Signal plumbing.

    Unlike the original (which blocked for up to VIRUSTOTAL_RATELIMIT seconds,
    ticking a countdown signal every second), this returns immediately with a
    cooldown notice if called too soon, so a Flask worker thread is never held
    hostage for the wait — callers (the GUI, via api_client) are expected to
    surface `wait_seconds` and retry.
    """
    api_key = os.environ.get("VIRUSTOTAL_API_KEY")
    if not api_key:
        return {"ok": False, "message": "Missing API key. Set VIRUSTOTAL_API_KEY in your environment or .env file."}

    wait = deep_scan_cooldown_remaining()
    if wait > 0:
        return {"ok": False, "reason": "cooldown", "wait_seconds": wait}

    state = _load_state()
    state["last_call"] = time.time()
    _save_state(state)

    headers = {"x-apikey": api_key}
    base = "https://www.virustotal.com/api/v3"

    try:
        if kind == "url":
            submit = requests.post(f"{base}/urls", headers=headers, data={"url": target}, timeout=20)
            if submit.status_code not in (200, 201):
                return {"ok": False, "message": f"Submit failed: {submit.status_code} {submit.text}"}
            analysis_id = submit.json()["data"]["id"]

            for _ in range(40):
                ra = requests.get(f"{base}/analyses/{analysis_id}", headers=headers, timeout=20)
                if ra.status_code == 200 and ra.json().get("data", {}).get("attributes", {}).get("status") == "completed":
                    break
                time.sleep(1)
            else:
                return {"ok": False, "message": "Timed out waiting for VirusTotal analysis to complete."}

            normalized = target if target.lower().startswith(("http://", "https://")) else f"http://{target}"
            url_id = url_to_vt_id(normalized)
            ru = requests.get(f"{base}/urls/{url_id}", headers=headers, timeout=20)
            if ru.status_code != 200:
                return {"ok": False, "message": f"Fetch stats failed: {ru.status_code} {ru.text}"}
            attrs = ru.json().get("data", {}).get("attributes", {}) or {}
            stats = attrs.get("last_analysis_stats", {}) or {}
            engine_results = attrs.get("last_analysis_results", {}) or {}
            verdict = _verdict_from_stats(stats)

        elif kind == "domain":
            rd = requests.get(f"{base}/domains/{target}", headers=headers, timeout=20)
            if rd.status_code != 200:
                return {"ok": False, "message": f"Domain lookup failed: {rd.status_code} {rd.text}"}
            attrs = rd.json().get("data", {}).get("attributes", {}) or {}
            stats = attrs.get("last_analysis_stats", {}) or {}
            engine_results = attrs.get("last_analysis_results", {}) or {}
            verdict = _verdict_from_stats(stats)

        elif kind == "ip":
            ri = requests.get(f"{base}/ip_addresses/{target}", headers=headers, timeout=20)
            if ri.status_code != 200:
                return {"ok": False, "message": f"IP lookup failed: {ri.status_code} {ri.text}"}
            attrs = ri.json().get("data", {}).get("attributes", {}) or {}
            stats = attrs.get("last_analysis_stats", {}) or {}
            engine_results = attrs.get("last_analysis_results", {}) or {}
            verdict = _verdict_from_stats(stats)

        else:
            return {"ok": False, "message": f"Unknown kind: {kind}"}

        return {
            "ok": True,
            "message": "OK",
            "stats": stats,
            "verdict": verdict,
            "kind": kind,
            "target": target,
            "engine_results": engine_results,
        }

    except requests.RequestException as e:
        return {"ok": False, "message": f"Network error: {e}"}
    except Exception as e:
        return {"ok": False, "message": f"Unexpected error: {e}"}
