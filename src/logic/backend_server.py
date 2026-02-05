import os
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from PySide6.QtCore import QThread

from src.logic.vt_service import (
    classify_kind,
    add_entry_to_blacklist,
    add_entry_to_whitelist,
)
from src.logic.scanner_service import ScannerScanThread

from urllib.parse import urlparse
import re

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = (BASE_DIR / ".." / "VT_Cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGGING_FILE = CACHE_DIR / "logging_mode_history.jsonl"
SCAN_REQUESTS_FILE = CACHE_DIR / "scan_requests.jsonl"

CURRENT_MODE = "logging"
FLASK_USERNAME = "UNAUTHENTICATED"
SERVER_THREAD: Optional["BackendServer"] = None
SERVER_PORT = 5005


# Pending scan requests list
SCAN_THREADS: list[ScannerScanThread] = []

# Initialize Flask app (CORS enables cross-origin requests like from extensions)
app = Flask(__name__)
CORS(app, supports_credentials=True)


def set_current_user(username: str):
    global FLASK_USERNAME
    FLASK_USERNAME = username

def start_server_if_needed():
    global SERVER_THREAD
    if SERVER_THREAD is None or not SERVER_THREAD.isRunning():
        SERVER_THREAD = BackendServer()
        SERVER_THREAD.daemon = True
        SERVER_THREAD.start()

class BackendServer(QThread):
    def run(self):
        app.run(host="127.0.0.1", port=SERVER_PORT, threaded=True, use_reloader=False)
        print("❌ BACKEND SERVER STOPPED (this should never print)")

def append_logging_entry(entry: dict):
    if not LOGGING_FILE.exists():
        LOGGING_FILE.write_text("", encoding="utf-8")
    with LOGGING_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")

# CAN REMOVE LATER: Just logs user requests made from the extension (@NicoVegaPortaluppi)
def append_scan_request(username: str, url: str, timestamp: int | None):
    if not SCAN_REQUESTS_FILE.exists():
        SCAN_REQUESTS_FILE.write_text("", encoding="utf-8")
    entry = {
        "username": username,
        "url": url,
        "timestamp": timestamp or 0,
    }
    with SCAN_REQUESTS_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")

def get_sorted_logs(user_name: str) -> list[dict]:
    entries: list[dict] = []

    try:
        if not LOGGING_FILE.exists():
            return entries

        with LOGGING_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("username") == user_name:
                    entries.append(entry)
    except Exception:
        print("LOG_FILE_ERROR")

    entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return entries

# Server condition endpoint (used by the extension to see if server is up)
@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "mode": CURRENT_MODE,
            "user": FLASK_USERNAME,
        }
    )

# Server logging endpoint (used by the extension to send navigations)
@app.route("/log", methods=["POST"])
def log_event():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"accepted": False, "reason": "url required"}), 400

    mode = data.get("mode") or CURRENT_MODE

    entry = {
        "username": FLASK_USERNAME,
        "mode": mode,
        "indicator": url,
        "timestamp": data.get("timestamp"),
        "verdict": "pending",
    }
    
    append_logging_entry(entry)
    return jsonify({"accepted": True, "verdict": "pending"})


# Endpoint used by the extension Safe Mode to trigger VT scan
@app.route("/scan", methods=["POST"])
def scan_event():
    data = request.get_json(force=True, silent=True) or {}
    raw_url = data.get("url") or data.get("target")
    if not raw_url:
        return jsonify({"ok": False, "reason": "url required"}), 400

    ts = data.get("timestamp")

    try:
        append_scan_request(FLASK_USERNAME, raw_url, ts)
    except Exception:
        pass

    try:
        kind, target = classify_kind(raw_url)
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400

    try:
        worker = ScannerScanThread(kind, target, FLASK_USERNAME)
        SCAN_THREADS.append(worker)
        worker.start()

    except Exception as e:
        print("SCAN_THREAD_ERROR", e)
        return jsonify({"ok": False, "reason": "failed to start scan"}), 500

    return jsonify({"ok": True})

# -- Whitelist exeption --
def core_domain(host: str) -> str:
    host = (host or "").lower().strip()
    if not host:
        return ""

    parts = host.split(".")
    if len(parts) >= 2:
        # Second level domain 
        sld = parts[-2]
    else:
        sld = parts[0]

    # Keep only letters
    return re.sub(r"[^a-z]", "", sld)


ALIASES = {
    "youtu": "youtube",
    "yt": "youtube",
    "x": "twitter",
    "fb": "facebook",
}

def normalize_core(name: str) -> str:
    return ALIASES.get(name, name)

def domains_equivalent(a: str, b: str) -> bool:
    core_a = normalize_core(core_domain(a))
    core_b = normalize_core(core_domain(b))
    return core_a != "" and core_a == core_b

def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    hostname = (parsed.hostname or "").lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return f"{scheme}://{hostname}{path}"


def get_base_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])

def make_list_entry(url: str, verdict: str) -> dict:
    kind, target = classify_kind(url)
    return {
        "ts": datetime.now().isoformat(),
        "kind": kind,
        "target": target,
        "verdict": verdict,
        "user": FLASK_USERNAME,
        "source": "extension",
    }

@app.route("/is_whitelisted", methods=["POST"])
def is_whitelisted():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "")

    url_norm = normalize_url(url)
    parsed = urlparse(url)
    url_host = parsed.hostname or ""
    url_base = get_base_domain(url_host.lower()) 

    whitelist_path = CACHE_DIR / "vt_whiteList.jsonl"
    if not whitelist_path.exists():
        return jsonify({"whitelisted": False})

    with open(whitelist_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            # Only check entries for the current user
            if entry.get("user") != FLASK_USERNAME:
                continue
                
            target = entry.get("target", "").strip()
            if not target:
                continue

            target_norm = normalize_url(target)
            t_parsed = urlparse(target)
            t_host = t_parsed.hostname or ""
            t_base = get_base_domain(t_host.lower())

            print("CHECK:", repr(target_norm), "vs", repr(url_norm))

            # Normalized the f*****g URL
            if target_norm == url_norm:
                print("MATCH: exact normalized URL")
                return jsonify({"whitelisted": True})

            # Core domain (like youtube = youtu.be)
            if domains_equivalent(url_host, t_host):
                print("MATCH: core-domain equivalence", url_host, t_host)
                return jsonify({"whitelisted": True})

            # plain base domain equality
            if url_base == t_base:
                print("MATCH: base-domain equality", url_base, t_base)
                return jsonify({"whitelisted": True})

    return jsonify({"whitelisted": False})

# -- Blacklist Implementation --
@app.route("/is_blacklisted", methods=["POST"])
def is_blacklisted():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "")

    url_norm = normalize_url(url)
    parsed = urlparse(url)
    url_host = parsed.hostname or ""

    blacklist_path = CACHE_DIR / "vt_blackList.jsonl"
    if not blacklist_path.exists():
        return jsonify({"blacklisted": False})

    with open(blacklist_path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            # Only check entries for the current user
            if entry.get("user") != FLASK_USERNAME:
                continue
                
            target = entry.get("target", "").strip()
            if not target:
                continue

            target_norm = normalize_url(target)
            t_parsed = urlparse(target)
            t_host = t_parsed.hostname or ""

            if target_norm == url_norm:
                return jsonify({"blacklisted": True})

            if domains_equivalent(url_host, t_host):
                return jsonify({"blacklisted": True})

    return jsonify({"blacklisted": False})


@app.route("/add_to_whitelist", methods=["POST"])
def add_to_whitelist():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"ok": False, "reason": "url required"}), 400
    verdict = "whitelisted"
    try:
        entry = make_list_entry(url, verdict)
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400

    try:
        add_entry_to_whitelist(entry)
    except Exception as e:
        print("ADD_WHITELIST_ERROR", e)
        return jsonify({"ok": False, "reason": "failed to write"}), 500
    return jsonify({"ok": True})


@app.route("/add_to_blacklist", methods=["POST"])
def add_to_blacklist():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"ok": False, "reason": "url required"}), 400
    verdict = "blacklisted"
    try:
        entry = make_list_entry(url, verdict)
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400

    try:
        add_entry_to_blacklist(entry)
    except Exception as e:
        print("ADD_BLACKLIST_ERROR", e)
        return jsonify({"ok": False, "reason": "failed to write"}), 500
    return jsonify({"ok": True})

