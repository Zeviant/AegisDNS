"""
AegisDNS backend — standalone Flask service.

This replaces src/logic/backend_server.py's role for anything beyond the native
GUI process: it used to run as a QThread *inside* the PySide6 app, started only
after login. Here it's a plain WSGI app with no PySide6/Qt dependency at all, run
in its own Docker container (see docker-compose.yml) so the exact same backend
runs identically on every host OS.

Endpoints in the first block below (/health, /log, /scan, /is_whitelisted,
/is_blacklisted, /add_to_whitelist, /add_to_blacklist) are byte-for-byte
behavior-compatible with the original backend_server.py — the browser extension
needs zero changes and can keep talking to 127.0.0.1:5005 exactly as before.

Everything after that block is new: it's what src/logic/api_client.py (the native
GUI's HTTP client) calls instead of importing DatabaseManager/scanner_service/
vt_service/llm_service directly in-process.
"""
import os
import re
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from flask_cors import CORS

from backend.services import scanner_service, vt_service, llm_service
from backend.db.database_manager import DatabaseManager

# --- Paths (env-configurable, same VT_CACHE_DIR the services use) ---
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = Path(os.getenv("VT_CACHE_DIR", os.path.join(_BACKEND_DIR, "VT_Cache")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGGING_FILE = CACHE_DIR / "logging_mode_history.jsonl"
SCAN_REQUESTS_FILE = CACHE_DIR / "scan_requests.jsonl"

CURRENT_MODE = "logging"
FLASK_USERNAME = "UNAUTHENTICATED"
SERVER_PORT = int(os.getenv("BACKEND_PORT", "5005"))

# Pending fire-and-forget scan threads triggered by the extension's /scan route
SCAN_THREADS: list[threading.Thread] = []

app = Flask(__name__)
CORS(app, supports_credentials=True)


def set_current_user(username: str):
    global FLASK_USERNAME
    FLASK_USERNAME = username


def append_logging_entry(entry: dict):
    if not LOGGING_FILE.exists():
        LOGGING_FILE.write_text("", encoding="utf-8")
    with LOGGING_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")


def append_scan_request(username: str, url: str, timestamp: Optional[int]):
    if not SCAN_REQUESTS_FILE.exists():
        SCAN_REQUESTS_FILE.write_text("", encoding="utf-8")
    entry = {"username": username, "url": url, "timestamp": timestamp or 0}
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


# -- JSONL housekeeping for change_username / delete_account, ported from the
# GUI's old direct-file-access versions (change_username_window.py /
# delete_account_window.py) — now server-side since the backend owns this data. --
_USER_FIELD_FILES = [vt_service.HISTORY_FILE, vt_service.WHITELIST_FILE, vt_service.BLACKLIST_FILE]
_USERNAME_FIELD_FILES = [str(LOGGING_FILE), str(SCAN_REQUESTS_FILE)]


def _rewrite_jsonl(file_path: str, transform):
    """Read every line of a JSONL file, apply transform(entry) -> entry|None
    (None drops the line), and rewrite the file. Corrupted lines are kept as-is."""
    if not os.path.exists(file_path):
        return
    lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                lines.append(line + "\n")
                continue
            entry = transform(entry)
            if entry is not None:
                lines.append(json.dumps(entry) + "\n")
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def rename_user_in_jsonl_files(old_username: str, new_username: str) -> None:
    def rename_user(entry):
        if entry.get("user") == old_username:
            entry["user"] = new_username
        return entry

    def rename_username(entry):
        if entry.get("username") == old_username:
            entry["username"] = new_username
        return entry

    for path in _USER_FIELD_FILES:
        _rewrite_jsonl(path, rename_user)
    for path in _USERNAME_FIELD_FILES:
        _rewrite_jsonl(path, rename_username)


def delete_user_from_jsonl_files(username: str) -> None:
    for path in _USER_FIELD_FILES:
        _rewrite_jsonl(path, lambda e: None if e.get("user") == username else e)
    for path in _USERNAME_FIELD_FILES:
        _rewrite_jsonl(path, lambda e: None if e.get("username") == username else e)


# =====================================================================
# Existing extension-facing endpoints — unchanged behavior/signatures
# =====================================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mode": CURRENT_MODE, "user": FLASK_USERNAME})


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


@app.route("/scan", methods=["POST"])
def scan_event():
    """Fire-and-forget scan trigger used by the browser extension's Silent/Safe modes."""
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
        kind, target = vt_service.classify_kind(raw_url)
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400

    try:
        username = FLASK_USERNAME
        worker = threading.Thread(target=scanner_service.run_scan, args=(kind, target, username), daemon=True)
        SCAN_THREADS.append(worker)
        worker.start()
    except Exception as e:
        print("SCAN_THREAD_ERROR", e)
        return jsonify({"ok": False, "reason": "failed to start scan"}), 500

    return jsonify({"ok": True})


# -- Whitelist/blacklist domain-equivalence helpers (unchanged from original) --
def core_domain(host: str) -> str:
    host = (host or "").lower().strip()
    if not host:
        return ""
    parts = host.split(".")
    sld = parts[-2] if len(parts) >= 2 else parts[0]
    return re.sub(r"[^a-z]", "", sld)


ALIASES = {"youtu": "youtube", "yt": "youtube", "x": "twitter", "fb": "facebook"}


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
    kind, target = vt_service.classify_kind(url)
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

    if not os.path.exists(vt_service.WHITELIST_FILE):
        return jsonify({"whitelisted": False})

    with open(vt_service.WHITELIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("user") != FLASK_USERNAME:
                continue
            target = entry.get("target", "").strip()
            if not target:
                continue
            target_norm = normalize_url(target)
            t_parsed = urlparse(target)
            t_host = t_parsed.hostname or ""
            t_base = get_base_domain(t_host.lower())

            if target_norm == url_norm:
                return jsonify({"whitelisted": True})
            if domains_equivalent(url_host, t_host):
                return jsonify({"whitelisted": True})
            if url_base == t_base:
                return jsonify({"whitelisted": True})

    return jsonify({"whitelisted": False})


@app.route("/is_blacklisted", methods=["POST"])
def is_blacklisted():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "")
    url_norm = normalize_url(url)
    parsed = urlparse(url)
    url_host = parsed.hostname or ""

    if not os.path.exists(vt_service.BLACKLIST_FILE):
        return jsonify({"blacklisted": False})

    with open(vt_service.BLACKLIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
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
    try:
        entry = make_list_entry(url, "whitelisted")
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400
    try:
        vt_service.add_entry_to_whitelist(entry)
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
    try:
        entry = make_list_entry(url, "blacklisted")
    except ValueError as e:
        return jsonify({"ok": False, "reason": str(e)}), 400
    try:
        vt_service.add_entry_to_blacklist(entry)
    except Exception as e:
        print("ADD_BLACKLIST_ERROR", e)
        return jsonify({"ok": False, "reason": "failed to write"}), 500
    return jsonify({"ok": True})


# =====================================================================
# New endpoints — used by the native GUI's api_client.py
# =====================================================================

@app.route("/session/set_user", methods=["POST"])
def session_set_user():
    """Called by the GUI right after a successful login (replaces the old
    in-process set_current_user() call), so extension-facing routes above know
    which user is currently active."""
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    if not username:
        return jsonify({"ok": False, "reason": "username required"}), 400
    set_current_user(username)
    return jsonify({"ok": True})


@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(force=True, silent=True) or {}
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        return jsonify({"ok": False, "reason": "username and password required"}), 400
    ok = DatabaseManager.authenticate_user(username, password)
    return jsonify({"ok": ok})


@app.route("/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(force=True, silent=True) or {}
    required = ("username", "password", "first_name", "last_name")
    if not all(data.get(k) for k in required):
        return jsonify({"ok": False, "reason": "username, password, first_name and last_name required"}), 400
    result = DatabaseManager.create_new_user(data["username"], data["password"], data["first_name"], data["last_name"])
    return jsonify({"ok": result == "success", "reason": result})


@app.route("/auth/change_password", methods=["POST"])
def auth_change_password():
    data = request.get_json(force=True, silent=True) or {}
    result = DatabaseManager.update_password(data.get("username"), data.get("current_password"), data.get("new_password"))
    return jsonify({"ok": result == "success", "reason": result})


@app.route("/auth/change_username", methods=["POST"])
def auth_change_username():
    data = request.get_json(force=True, silent=True) or {}
    old_username, new_username = data.get("username"), data.get("new_username")
    result = DatabaseManager.update_username(old_username, data.get("current_password"), new_username)
    if result == "success":
        try:
            rename_user_in_jsonl_files(old_username, new_username)
        except Exception as e:
            print("RENAME_JSONL_ERROR", e)
        set_current_user(new_username)
    return jsonify({"ok": result == "success", "reason": result})


@app.route("/auth/delete_account", methods=["POST"])
def auth_delete_account():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    result = DatabaseManager.delete_user(username, data.get("password"))
    if result == "success":
        try:
            delete_user_from_jsonl_files(username)
        except Exception as e:
            print("DELETE_JSONL_ERROR", e)
    return jsonify({"ok": result == "success", "reason": result})


@app.route("/scan/local", methods=["POST"])
def scan_local():
    """Synchronous local scan for the GUI's scan button (unlike /scan above,
    which is fire-and-forget for the extension)."""
    data = request.get_json(force=True, silent=True) or {}
    raw = data.get("indicator") or data.get("target")
    username = data.get("username", FLASK_USERNAME)
    try:
        if raw and not data.get("kind"):
            kind, target = vt_service.classify_kind(raw)
        else:
            kind, target = data.get("kind"), data.get("target")
    except ValueError as e:
        return jsonify({"ok": False, "message": str(e)}), 400

    result = scanner_service.run_scan(kind, target, username)
    return jsonify(result)


@app.route("/scan/deep", methods=["POST"])
def scan_deep():
    data = request.get_json(force=True, silent=True) or {}
    raw = data.get("indicator") or data.get("target")
    try:
        if raw and not data.get("kind"):
            kind, target = vt_service.classify_kind(raw)
        else:
            kind, target = data.get("kind"), data.get("target")
    except ValueError as e:
        return jsonify({"ok": False, "message": str(e)}), 400

    result = vt_service.run_deep_scan(kind, target)
    return jsonify(result)


@app.route("/ai/overview/cached", methods=["GET"])
def ai_overview_cached():
    """Pure cache check — unlike POST /ai/overview, never generates a new one.
    Used to decide whether to show an instant result or fall through to the
    (potentially model-download-gated) generation flow."""
    kind = request.args.get("kind", "")
    target = request.args.get("target", "")
    cached = llm_service.get_cached_ai_overview(kind, target)
    return jsonify({"cached": cached})


@app.route("/ai/overview", methods=["POST"])
def ai_overview():
    data = request.get_json(force=True, silent=True) or {}
    result = llm_service.run_ai_overview(
        verdict=data.get("verdict", ""),
        stats=data.get("stats", {}) or {},
        signals=data.get("signals", []) or [],
        kind=data.get("kind", ""),
        target=data.get("target", ""),
    )
    return jsonify(result)


@app.route("/ai/model/status", methods=["GET"])
def ai_model_status():
    return jsonify({"downloaded": llm_service.model_is_downloaded()})


@app.route("/ai/model/download", methods=["POST"])
def ai_model_download():
    return jsonify(llm_service.start_model_download())


@app.route("/ai/model/download/progress", methods=["GET"])
def ai_model_download_progress():
    return jsonify(llm_service.get_download_progress())


@app.route("/whitelist/entry", methods=["POST"])
def whitelist_add_entry():
    """Unlike /add_to_whitelist (URL-only, used by the extension), this accepts a
    fully-formed entry dict as-is — used by the GUI's history window, which already
    knows the target/kind/ts/user from the row being whitelisted."""
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("target"):
        return jsonify({"ok": False, "reason": "target required"}), 400
    try:
        vt_service.add_entry_to_whitelist(data)
    except Exception as e:
        return jsonify({"ok": False, "reason": str(e)}), 500
    return jsonify({"ok": True})


@app.route("/blacklist/entry", methods=["POST"])
def blacklist_add_entry():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("target"):
        return jsonify({"ok": False, "reason": "target required"}), 400
    try:
        vt_service.add_entry_to_blacklist(data)
    except Exception as e:
        return jsonify({"ok": False, "reason": str(e)}), 500
    return jsonify({"ok": True})


@app.route("/scan/cache", methods=["GET"])
def scan_cache_lookup():
    """Looks up a previously cached scan result for (kind, target) — backs the
    GUI's 'View additional info' / AI-overview-source lookups, which used to read
    scanner_cache.json directly off disk."""
    kind = request.args.get("kind", "")
    target = request.args.get("target", "")
    state = scanner_service._load_scanner_state()
    entry = (state.get("cache", {}) or {}).get(scanner_service.cache_key(kind, target))
    return jsonify({"entry": entry})


@app.route("/history", methods=["GET"])
def history_list():
    username = request.args.get("username", FLASK_USERNAME)
    return jsonify({"entries": vt_service.get_sorted_history(username)})


@app.route("/history", methods=["DELETE"])
def history_reset():
    """Wipes scan history: scanner cache, VT history JSONL, and pending scan
    requests log — same reset behavior settings_window.py / history_window.py
    perform locally today."""
    for path in (scanner_service.CACHE_FILE, vt_service.HISTORY_FILE, str(SCAN_REQUESTS_FILE)):
        try:
            open(path, "w", encoding="utf-8").close()
        except Exception:
            pass
    return jsonify({"ok": True})


@app.route("/history/entry", methods=["DELETE"])
def history_delete_entry():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", FLASK_USERNAME)
    vt_service.delete_history_entry(username, data.get("ts"), data.get("target"))
    return jsonify({"ok": True})


@app.route("/logs", methods=["GET"])
def logs_list():
    username = request.args.get("username", FLASK_USERNAME)
    return jsonify({"entries": get_sorted_logs(username)})


@app.route("/logs", methods=["DELETE"])
def logs_reset():
    try:
        LOGGING_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass
    return jsonify({"ok": True})


@app.route("/whitelist", methods=["GET"])
def whitelist_list():
    username = request.args.get("username", FLASK_USERNAME)
    return jsonify({"entries": vt_service.get_sorted_white_list(username)})


@app.route("/whitelist", methods=["DELETE"])
def whitelist_delete():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", FLASK_USERNAME)
    vt_service.delete_whiteList_entry(username, data.get("ts"), data.get("target"))
    return jsonify({"ok": True})


@app.route("/blacklist", methods=["GET"])
def blacklist_list():
    username = request.args.get("username", FLASK_USERNAME)
    return jsonify({"entries": vt_service.get_sorted_black_list(username)})


@app.route("/blacklist", methods=["DELETE"])
def blacklist_delete():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", FLASK_USERNAME)
    vt_service.delete_blackList_entry(username, data.get("ts"), data.get("target"))
    return jsonify({"ok": True})


if __name__ == "__main__":
    # 0.0.0.0 so the port published by docker-compose (5005:5005) reaches Flask;
    # the original in-process version bound 127.0.0.1 only, which only worked
    # because it ran inside the same host as its callers.
    app.run(host="0.0.0.0", port=SERVER_PORT, threaded=True, use_reloader=False)
