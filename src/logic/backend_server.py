import os
import json
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from PySide6.QtCore import QThread

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = (BASE_DIR / ".." / "VT_Cache").resolve()
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOGGING_FILE = CACHE_DIR / "logging_mode_history.jsonl"

CURRENT_MODE = "logging"
FLASK_USERNAME = "UNAUTHENTICATED"
SERVER_THREAD: Optional["BackendServer"] = None
SERVER_PORT = 5005

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

def append_logging_entry(entry: dict):
    if not LOGGING_FILE.exists():
        LOGGING_FILE.write_text("", encoding="utf-8")
    with LOGGING_FILE.open("a", encoding="utf-8") as fp:
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
    print(f"(LOG_FILE) Entries found: {len(entries)}")
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

    entry = {
        "username": FLASK_USERNAME,
        "mode": CURRENT_MODE,
        "indicator": url,
        "timestamp": data.get("timestamp"),
        "verdict": "pending",
    }
    
    append_logging_entry(entry)
    return jsonify({"accepted": True, "verdict": "pending"})