# --- Libraries ---
# Qt Libraries
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel

# Other Libraries
import os, sys, time, base64, requests, json, ipaddress, re
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Sequence, CHAR, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import select

# Connection with other modules
from src.SQL_Alchemy.database import User, Addresses, session

# --- Importando load_dotenv, it read the .env ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Cache ---

# Defining the variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "VT_Cache/vt_cache.json")
HISTORY_FILE = os.path.join(BASE_DIR, "VT_Cache/vt_history.jsonl")
VIRUSTOTAL_RATELIMIT = 15
_STATE_MEMO = {"last_call": 0, "cache": {}}


# Saving the data in the chache
def _load_state() -> dict:
    global _STATE_MEMO
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if isinstance(state, dict):
                # Convert 'last_call' back to float if it was saved as a string (it shouldn't be)
                # Ensure 'last_call' is present
                state.setdefault("last_call", 0)
                # Convert 'ts' in cache entries back to datetime or just leave it as string for simplicity
                for entry in state.get("cache", {}).values():
                    # If we decide to keep 'ts' as string in cache, no need to convert back here.
                    pass 
                _STATE_MEMO = state
                return state
    except Exception:
        pass
    # fallback to last known good in memory
    return dict(_STATE_MEMO)


def _save_state(state: dict) -> None:
    global _STATE_MEMO
    # Create a deep copy to modify for saving without affecting the in-memory state
    state_to_save = dict(state) 
    state_to_save.setdefault("cache", {})
    
    # Convert datetime objects in cache entries to strings (ISO 8601 format)
    for key, cached_entry in state_to_save["cache"].items():
        if isinstance(cached_entry.get("ts"), datetime):
            # Format: 'YYYY-MM-DDTHH:MM:SS.mmmmmm'
            cached_entry["ts"] = cached_entry["ts"].isoformat()
            
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state_to_save, f) # Use state_to_save here
    os.replace(tmp, CACHE_FILE)
    _STATE_MEMO = state


def append_history(kind: str, target: str, verdict: str, stats: dict, source: str, userName: str = "N/A") -> None:
    # Get the timestamp as a datetime object
    now = datetime.now() 
    
    entry = {
        # Convert datetime object to ISO format string for JSON serialization
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

    # Open database
    db = QSqlDatabase.addDatabase("QSQLITE")
    # Use relative path from the project structure
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "src" / "SQL_Alchemy" / "UserInformation.db"
    db.setDatabaseName(str(db_path))

    if not db.open(): 
        print("Error: Could not open database connection.")
            
    else:
        # Check if address already exists
        existing_address = session.query(Addresses).filter_by(address=target).first()
        
        if existing_address:
            # Update existing record
            existing_address.date = datetime.now()
            existing_address.veredict = verdict
            existing_address.owner = userName
        else:
            # Create new record
            address = Addresses(target, datetime.now(), verdict, owner= userName)
            session.add(address)
        
        session.commit()


# --- Inputs (if URL, IP or Domain)
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,63}\.?$"
)

def normalize_target(s: str) -> str:
    return s.strip().lower().rstrip(".")

def classify_kind(raw_text: str) -> tuple[str, str]:
    """
    Returns (kind, target):
      kind ∈ {'url','domain','ip'}
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

# Normalizador de URL 
def url_to_vt_id(url: str) -> str:
    """VirusTotal URL ID is base64url of the URL without '=' padding."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")
    return b64.strip("=")

# VT key
def cache_key(kind: str, target: str) -> str:
    if kind == "url":
        norm = target if target.lower().startswith(("http://", "https://")) else f"http://{target}"
        return f"url:{norm}"
    return f"{kind}:{target}"

# --- Qt ---
# VT Box Window Style
def render_vt_html(verdict: str, stats: dict) -> str:
    color = {"BLOCK": "#ef4444", "CAUTION": "#f59e0b", "SAFE": "#10b981"}.get(verdict, "#93a3b1")
    harmless = stats.get("harmless", 0)
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    undetected = stats.get("undetected", 0)
    timeout = stats.get("timeout", 0)
    return f"""
      <div style="font-family:'Segoe UI',Arial; font-size:14px; color:#e5e7eb;">
        <h2 style="margin:0 0 12px; font-size:22px; color:{color};">Verdict: {verdict}</h2>
        <table style="border-collapse:collapse; margin-top:6px;">
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Harmless</td>
              <td style="padding:4px 12px; font-weight:600;">{harmless}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Malicious</td>
              <td style="padding:4px 12px; font-weight:600;">{malicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Suspicious</td>
              <td style="padding:4px 12px; font-weight:600;">{suspicious}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Undetected</td>
              <td style="padding:4px 12px; font-weight:600;">{undetected}</td></tr>
          <tr><td style="padding:4px 12px; color:#9aa5b1;">Timeout</td>
              <td style="padding:4px 12px; font-weight:600;">{timeout}</td></tr>
        </table>
        <p style="margin-top:12px; color:#9aa5b1;">Source: VirusTotal (last_analysis_stats)</p>
      </div>
    """

# VT box Window Content
def show_vt_box(parent, verdict: str, stats: dict):
    icon = (QMessageBox.Critical if verdict == "BLOCK"
            else QMessageBox.Warning if verdict == "CAUTION"
            else QMessageBox.Information)
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle("VirusTotal Result")
    box.setTextFormat(Qt.RichText)
    box.setText(render_vt_html(verdict, stats))
    box.setStandardButtons(QMessageBox.Ok)

    # Bigger + wrapped + selectable
    lbl = box.findChild(QLabel, "qt_msgbox_label")
    if lbl:
        lbl.setWordWrap(True)
        lbl.setMinimumSize(420, 260)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

    box.exec()

# Main Wiwndow (Where the user puts the input)
class MainWindow(QMainWindow):
    def __init__(self, userName, password):
        super().__init__()
        self.userName = userName 
        self.password = password
        
        self.setWindowTitle(f"Main Window - User: {self.userName}")
        self.resize(450, 450)
        
        # Timer
        self._cooldown_left = 0
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._cooldown_tick)

        # --- layout & style ---
        central = QWidget(self)
        self.setCentralWidget(central)
        page = QVBoxLayout(central)
        page.setContentsMargins(40, 40, 40, 40)

        central.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0, x2:0,y2:1,
                    stop:0 #0f172a, stop:1 #0b1220);
                color: #e5e7eb;
                font-size: 14px;
            }
        """)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card { background: #101e29; border-radius: 16px; }
            QLineEdit {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px;
                padding: 10px 12px;
                color: #e5e7eb;
                selection-background-color: #1e40af;
            }
            QLineEdit:focus { border: 1px solid #60a5fa; background: rgba(255,255,255,0.09); }
            QPushButton {
                border: none; border-radius: 10px; padding: 10px 16px;
                background: #1d4ed8; color: white; font-weight: 600;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:disabled { background: #334155; color: #cbd5e1; }
            QPushButton:pressed { background: #1e40af; }
        """)
        shadow = QGraphicsDropShadowEffect(blurRadius=40, xOffset=0, yOffset=12)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        card_wrap = QVBoxLayout(card)
        card_wrap.setContentsMargins(48, 48, 48, 48)
        card_wrap.setSpacing(24)

        title = QLabel("ENTER A URL / DOMAIN / IP")
        tfont = QFont(); tfont.setPointSize(24); tfont.setBold(True)
        title.setFont(tfont); title.setAlignment(Qt.AlignHCenter)

        prompt = QLabel("Type a full URL, domain or an IP and click OK.")
        prompt.setAlignment(Qt.AlignHCenter)
        pfont = QFont(); pfont.setPointSize(11)
        prompt.setFont(pfont); prompt.setStyleSheet("color: #9aa5b1;")

        row = QHBoxLayout(); row.setSpacing(12)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Example: https://example.com  |  example.com  |  8.8.8.8")
        self.input_edit.setMinimumWidth(420)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.on_ok, userName)
        self.input_edit.returnPressed.connect(self.ok_btn.click)

        row.addWidget(self.input_edit, 1)
        row.addWidget(self.ok_btn)

        card_wrap.addWidget(title)
        card_wrap.addWidget(prompt)
        card_wrap.addLayout(row)

        page.addStretch(1)
        page.addWidget(card, 0, Qt.AlignHCenter)
        page.addStretch(1)

        self._worker = None  

    # Cooldown Functions
    def start_cooldown(self, seconds: int):
        self._cooldown_left = max(1, int(seconds))
        self.ok_btn.setEnabled(False)
        self.ok_btn.setText(f"Cooldown: {self._cooldown_left}s")
        self._cooldown_timer.start()

    def _cooldown_tick(self):
        self._cooldown_left -= 1
        if self._cooldown_left <= 0:
            self._cooldown_timer.stop()
            self.ok_btn.setEnabled(True)
            self.ok_btn.setText("OK")
        else:
            self.ok_btn.setText(f"Cooldown: {self._cooldown_left}s")

    def on_ok(self):
        api_key = os.environ.get("VIRUSTOTAL_API_KEY")
        raw = self.input_edit.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Missing API key",
                                "Set VIRUSTOTAL_API_KEY in your environment or .env file.")
            return
        if not raw:
            QMessageBox.warning(self, "Empty input", "Please enter a URL, domain, or IP.")
            return

        # Enforce cooldown at UI level
        # Enforce cooldown at UI level
        state = _load_state()
        # Ensure last is treated as a float timestamp
        last = float(state.get("last_call", 0) or 0)
        remaining = int(max(0, VIRUSTOTAL_RATELIMIT - (time.time() - last))) # Keep time.time() here
        if remaining > 0:
            self.start_cooldown(remaining)
            return

        try:
            kind, target = classify_kind(raw)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return

        self.ok_btn.setEnabled(False)
        self.ok_btn.setText("Preparing...")

        self._worker = VTScanThread(kind, target, api_key, self.userName, self)
        # you can keep this; if UI gate passed, worker should tick 0 -> "Scanning..."
        self._worker.tick.connect(self.on_cooldown_tick)
        self._worker.result.connect(self.on_result)
        self._worker.start()

    def on_cooldown_tick(self, secs_left: int):
        # secs_left > 0 during cooldown; 0 when the scan is starting
        self.ok_btn.setText(f"Cooldown: {secs_left}s" if secs_left > 0 else "Scanning...")

    def on_result(self, payload: dict):
        self.ok_btn.setEnabled(True)
        self.ok_btn.setText("OK")

        if not payload.get("ok"):
            QMessageBox.critical(self, "VirusTotal Error", payload.get("message", "Unknown error"))
            return

        stats = payload.get("stats", {}) or {}
        verdict = payload.get("verdict", "UNKNOWN")
        show_vt_box(self, verdict, stats)

# --- Sending the input to VT API ---


class VTScanThread(QThread):
    result = Signal(dict)     
    tick = Signal(int)         

    
    def __init__(self, kind: str, target: str, api_key: str, userName: str, parent=None):
        super().__init__(parent)
        self.kind = kind         
        self.target = target
        self.api_key = api_key
        self.userName = userName  
        self.base = "https://www.virustotal.com/api/v3"
        self.headers = {"x-apikey": self.api_key}

    def _verdict_from_stats(self, stats: dict) -> str:
        mal = int(stats.get("malicious", 0))
        susp = int(stats.get("suspicious", 0))
        return "BLOCK" if mal > 0 else "CAUTION" if susp > 0 else "SAFE"

    def _enforce_cooldown(self) -> float:
        state = _load_state()
        # Use time.time() for numeric comparison
        last = float(state.get("last_call", 0) or 0)
        wait = int(max(0, VIRUSTOTAL_RATELIMIT - (time.time() - last)))
        while wait > 0:
            self.tick.emit(wait)
            time.sleep(1)
            wait -= 1
            
        start_ts = time.time()              # Mark just before hitting API
        state["last_call"] = start_ts
        _save_state(state)                   # Persist immediately
        self.tick.emit(0)                    # 0 => scanning
        return start_ts

    def run(self):
        try:
            # 0) Cache check (skip cooldown if cache hit)
            state = _load_state()
            cache = state.get("cache", {})
            key = cache_key(self.kind, self.target)
            cached = cache.get(key)
            if cached:
                stats = cached.get("stats", {}) or {}
                verdict = cached.get("verdict", "UNKNOWN")
                
                # mark a “use” to enforce cooldown even for cache
                # Use time.time() for last_call, as decided in step 2.
                state["last_call"] = time.time() 
                _save_state(state)
                
                append_history(self.kind, self.target, verdict, stats, source="cache", userName=self.userName)
                self.result.emit({"ok": True, "message": "cache", "stats": stats, "verdict": verdict})
                return

            # 1) Cooldown (UI stays responsive; main thread shows countdown via tick)
            _ = self._enforce_cooldown()

            # 2) Live API call
            if self.kind == "url":
                submit = requests.post(
                    f"{self.base}/urls",
                    headers=self.headers,
                    data={"url": self.target},
                    timeout=20,
                )
                if submit.status_code not in (200, 201):
                    self.result.emit({"ok": False, "message": f"Submit failed: {submit.status_code} {submit.text}"})
                    return
                analysis_id = submit.json()["data"]["id"]

                # Poll for completion
                for _ in range(40):
                    ra = requests.get(f"{self.base}/analyses/{analysis_id}", headers=self.headers, timeout=20)
                    if ra.status_code == 200 and ra.json().get("data", {}).get("attributes", {}).get("status") == "completed":
                        break
                    time.sleep(1)
                else:
                    self.result.emit({"ok": False, "message": "Timed out waiting for VirusTotal analysis to complete."})
                    return

                # Fetch URL stats
                normalized = self.target if self.target.lower().startswith(("http://", "https://")) else f"http://{self.target}"
                url_id = url_to_vt_id(normalized)
                ru = requests.get(f"{self.base}/urls/{url_id}", headers=self.headers, timeout=20)
                if ru.status_code != 200:
                    self.result.emit({"ok": False, "message": f"Fetch stats failed: {ru.status_code} {ru.text}"})
                    return
                attrs = ru.json().get("data", {}).get("attributes", {}) or {}
                stats = attrs.get("last_analysis_stats", {}) or {}
                verdict = self._verdict_from_stats(stats)

            elif self.kind == "domain":
                rd = requests.get(f"{self.base}/domains/{self.target}", headers=self.headers, timeout=20)
                if rd.status_code != 200:
                    self.result.emit({"ok": False, "message": f"Domain lookup failed: {rd.status_code} {rd.text}"})
                    return
                attrs = rd.json().get("data", {}).get("attributes", {}) or {}
                stats = attrs.get("last_analysis_stats", {}) or {}
                verdict = self._verdict_from_stats(stats)

            elif self.kind == "ip":
                ri = requests.get(f"{self.base}/ip_addresses/{self.target}", headers=self.headers, timeout=20)
                if ri.status_code != 200:
                    self.result.emit({"ok": False, "message": f"IP lookup failed: {ri.status_code} {ri.text}"})
                    return
                attrs = ri.json().get("data", {}).get("attributes", {}) or {}
                stats = attrs.get("last_analysis_stats", {}) or {}
                verdict = self._verdict_from_stats(stats)
            else:
                self.result.emit({"ok": False, "message": f"Unknown kind: {self.kind}"})
                return

            # 3) Save to cache + history, then emit
            state = _load_state()                   
            state.setdefault("cache", {})
            state["cache"][key] = {"stats": stats, "verdict": verdict, "ts": datetime.now().isoformat()}
            _save_state(state)
            append_history(self.kind, self.target, verdict, stats, source="live", userName=self.userName)
            self.result.emit({"ok": True, "message": "OK", "stats": stats, "verdict": verdict})

        except requests.RequestException as e:
            self.result.emit({"ok": False, "message": f"Network error: {e}"})
        except Exception as e:
            self.result.emit({"ok": False, "message": f"Unexpected error: {e}"})


# --- Main Function xd ---

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
