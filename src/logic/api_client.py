"""
HTTP client for the AegisDNS backend (now a Dockerized Flask service — see
docker-compose.yml / backend/app.py).

This replaces the GUI's previous direct, in-process imports of
DatabaseManager / scanner_service / vt_service / llm_service. Every function
here does a plain `requests` call and returns the same dict shape those direct
calls used to return, so callers change *what* they call, not how they use the
result.

BACKEND_URL defaults to the same 127.0.0.1:5005 the browser extension has
always used to reach the backend — it's overridable via the AEGISDNS_BACKEND_URL
env var if the backend is ever reached at a different host/port.
"""
import os
import ipaddress
import re
from typing import Optional

import requests

BACKEND_URL = os.getenv("AEGISDNS_BACKEND_URL", "http://127.0.0.1:5005")
_DEFAULT_TIMEOUT = 10

# --- classify_kind / normalize_target are pure parsing, no I/O — kept local so
# the GUI doesn't need a network round trip just to know if an input looks like
# a URL, domain, or IP (mirrors backend/services/vt_service.py exactly). ---
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,63}\.?$"
)


def normalize_target(s: str) -> str:
    return s.strip().lower().rstrip(".")


def classify_kind(raw_text: str) -> tuple[str, str]:
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


class BackendUnavailable(Exception):
    """Raised when the backend can't be reached at all (connection refused/timeout)."""


def _request(method: str, path: str, **kwargs) -> dict:
    kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
    try:
        resp = requests.request(method, f"{BACKEND_URL}{path}", **kwargs)
        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "message": f"Non-JSON response ({resp.status_code})"}
    except requests.RequestException as e:
        raise BackendUnavailable(str(e)) from e


def is_backend_reachable() -> bool:
    try:
        _request("GET", "/health")
        return True
    except BackendUnavailable:
        return False


# --- Session ---
def set_current_user(username: str) -> dict:
    return _request("POST", "/session/set_user", json={"username": username})


# --- Auth ---
def login(username: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"username": username, "password": password})


def register(username: str, password: str, first_name: str, last_name: str) -> dict:
    return _request("POST", "/auth/register", json={
        "username": username, "password": password,
        "first_name": first_name, "last_name": last_name,
    })


def change_password(username: str, current_password: str, new_password: str) -> dict:
    return _request("POST", "/auth/change_password", json={
        "username": username, "current_password": current_password, "new_password": new_password,
    })


def change_username(username: str, current_password: str, new_username: str) -> dict:
    return _request("POST", "/auth/change_username", json={
        "username": username, "current_password": current_password, "new_username": new_username,
    })


def delete_account(username: str, password: str) -> dict:
    return _request("POST", "/auth/delete_account", json={"username": username, "password": password})


# --- Scanning ---
def scan_local(kind: str, target: str, username: str) -> dict:
    return _request("POST", "/scan/local", json={"kind": kind, "target": target, "username": username},
                     timeout=60)


def scan_deep(kind: str, target: str) -> dict:
    """Returns {"ok": false, "reason": "cooldown", "wait_seconds": N} if called too
    soon after a previous deep scan — callers should surface wait_seconds and retry,
    same UX as the old tick-signal countdown, just polled instead of pushed."""
    return _request("POST", "/scan/deep", json={"kind": kind, "target": target}, timeout=60)


# --- AI overview ---
def get_cached_ai_overview(kind: str, target: str) -> Optional[dict]:
    """Pure cache check — never triggers generation. Returns None if nothing is
    cached yet (or the backend is unreachable)."""
    try:
        return _request("GET", "/ai/overview/cached", params={"kind": kind, "target": target}).get("cached")
    except BackendUnavailable:
        return None


def ai_overview(verdict: str, stats: dict, signals: list, kind: str = "", target: str = "") -> dict:
    return _request("POST", "/ai/overview", json={
        "verdict": verdict, "stats": stats, "signals": signals, "kind": kind, "target": target,
    }, timeout=60)


def model_status() -> dict:
    return _request("GET", "/ai/model/status")


def start_model_download() -> dict:
    return _request("POST", "/ai/model/download")


def get_download_progress() -> dict:
    return _request("GET", "/ai/model/download/progress")


# --- History ---
def get_history(username: str) -> list[dict]:
    return _request("GET", "/history", params={"username": username}).get("entries", [])


def reset_history() -> dict:
    return _request("DELETE", "/history")


def delete_history_entry(username: str, ts: str, target: str) -> dict:
    return _request("DELETE", "/history/entry", json={"username": username, "ts": ts, "target": target})


# --- Navigation logs (populated by the browser extension) ---
def get_logs(username: str) -> list[dict]:
    return _request("GET", "/logs", params={"username": username}).get("entries", [])


def reset_logs() -> dict:
    return _request("DELETE", "/logs")


# --- Whitelist / blacklist ---
def get_whitelist(username: str) -> list[dict]:
    return _request("GET", "/whitelist", params={"username": username}).get("entries", [])


def delete_whitelist_entry(username: str, ts: str, target: str) -> dict:
    return _request("DELETE", "/whitelist", json={"username": username, "ts": ts, "target": target})


def get_blacklist(username: str) -> list[dict]:
    return _request("GET", "/blacklist", params={"username": username}).get("entries", [])


def delete_blacklist_entry(username: str, ts: str, target: str) -> dict:
    return _request("DELETE", "/blacklist", json={"username": username, "ts": ts, "target": target})


def add_to_whitelist(url: str) -> dict:
    return _request("POST", "/add_to_whitelist", json={"url": url})


def add_to_blacklist(url: str) -> dict:
    return _request("POST", "/add_to_blacklist", json={"url": url})


def add_whitelist_entry(entry: dict) -> dict:
    """Appends a fully-formed entry (ts/kind/target/verdict/user already set by the
    caller) as-is — used when whitelisting from an existing history row."""
    return _request("POST", "/whitelist/entry", json=entry)


def add_blacklist_entry(entry: dict) -> dict:
    return _request("POST", "/blacklist/entry", json=entry)


# --- Scan cache lookup (backs "View additional info" / AI overview source data) ---
def get_cached_scan(kind: str, target: str) -> Optional[dict]:
    return _request("GET", "/scan/cache", params={"kind": kind, "target": target}).get("entry")
