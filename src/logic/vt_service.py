# --- Logic/Data Libraries ---
import os, time, base64, requests, json, ipaddress, re
from datetime import datetime
from PySide6.QtCore import QThread, Signal

# Import the Database Manager for logging
from src.SQL_Alchemy.database_manager import DatabaseManager

# --- Importando load_dotenv, it read the .env ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Cache / Rate Limit Configuration ---

# Defining the variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "..", "VT_Cache/vt_cache.json")
HISTORY_FILE = os.path.join(BASE_DIR, "..", "VT_Cache/vt_history.jsonl")
VIRUSTOTAL_RATELIMIT = 15
_STATE_MEMO = {"last_call": 0, "cache": {}}

# Saving the data in the chache
def _load_state() -> dict:
    global _STATE_MEMO
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if isinstance(state, dict):
                state.setdefault("last_call", 0)
                for entry in state.get("cache", {}).values():
                    pass 
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

def append_history(kind: str, target: str, verdict: str, stats: dict, source: str, userName: str = "N/A") -> None:
    # Get the timestamp as a datetime object
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
        # 1. Log to JSONL file (VT-specific logging remains here)
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
        
    # 2. Log to SQLAlchemy DB (Delegated to DatabaseManager)
    DatabaseManager.log_address_scan(target, verdict, userName)


# --- Inputs (if URL, IP or Domain) ---
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

def url_to_vt_id(url: str) -> str:
    """VirusTotal URL ID is base64url of the URL without '=' padding."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii")
    return b64.strip("=")

def cache_key(kind: str, target: str) -> str:
    if kind == "url":
        norm = target if target.lower().startswith(("http://", "https://")) else f"http://{target}"
        return f"url:{norm}"
    return f"{kind}:{target}"

def get_sorted_history(user_name: str) -> list[dict]:
    """ Used to filter and sort the JSON history log """
    
    entries = []
    count = 0
    try:
        with open(HISTORY_FILE, "r", encoding = "utf-8") as f:
            for line in f:
                entry = json.loads(line)
                # Filter entries by username
                if entry.get("user") == user_name:
                    entries.append(entry)
                    count = count + 1
    except Exception:
        print("HISTORY_FILE_ERROR")
        pass

    # Reverse sorting because we want newest --> oldest :)
    entries.sort(key = lambda x: x.get('ts', ''), reverse = True)
    return entries

# --- Sending the input to VT API (The Thread/Worker) ---
class VTScanThread(QThread):
    result = Signal(dict)     
    tick = Signal(int)         
    
    def __init__(self, kind: str, target: str, userName: str, parent=None):
        super().__init__(parent)
        self.kind = kind         
        self.target = target
        self.userName = userName  
        
        self.api_key = os.environ.get("VIRUSTOTAL_API_KEY") 
        
        self.base = "https://www.virustotal.com/api/v3"
        self.headers = {"x-apikey": self.api_key} if self.api_key else {}

    def _verdict_from_stats(self, stats: dict) -> str:
        mal = int(stats.get("malicious", 0))
        susp = int(stats.get("suspicious", 0))
        return "BLOCK" if mal > 0 else "CAUTION" if susp > 0 else "SAFE"

    def _enforce_cooldown(self) -> float:
        state = _load_state()
        last = float(state.get("last_call", 0) or 0)
        wait = int(max(0, VIRUSTOTAL_RATELIMIT - (time.time() - last)))
        while wait > 0:
            self.tick.emit(wait)
            time.sleep(1)
            wait -= 1
            
        start_ts = time.time()
        state["last_call"] = start_ts
        _save_state(state)
        self.tick.emit(0)
        return start_ts

    def run(self):
        try:
            if not self.api_key:
                self.result.emit({"ok": False, "message": "Missing API key. Set VIRUSTOTAL_API_KEY in your environment or .env file."})
                return

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

                for _ in range(40):
                    ra = requests.get(f"{self.base}/analyses/{analysis_id}", headers=self.headers, timeout=20)
                    if ra.status_code == 200 and ra.json().get("data", {}).get("attributes", {}).get("status") == "completed":
                        break
                    time.sleep(1)
                else:
                    self.result.emit({"ok": False, "message": "Timed out waiting for VirusTotal analysis to complete."})
                    return

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