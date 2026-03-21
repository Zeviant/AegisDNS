# Capstone

**DNS-level connection interception, analysis, and maliciousness scoring system.**

A full-stack security monitoring solution consisting of:

- **Desktop app** (Python + PySide6) — manual scans, history, whitelist/blacklist, packet monitoring, and notifications
- **Browser extension** (Chrome/Chromium) — navigates together with the app and can log, scan, or intercept browsing
- **Local backend** (Flask) — bridges the extension and the desktop app

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Chrome Extension (dns-protect)                                      │
│  • Popup: mode selector (None / Logging / Silent / Safe)             │
│  • Background: navigation interception, blacklist enforcement        │
│  • Interstitials: Safe-mode review page, blacklist block page        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP (127.0.0.1:5005)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Flask Backend (backend_server.py)                                   │
│  • /health, /log, /scan, /is_whitelisted, /is_blacklisted            │
│  • /add_to_whitelist, /add_to_blacklist                              │
│  • Started on app login, bound to current user                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Desktop App (PySide6)                                               │
│  • Authentication → Scanner, History, Logs, Packets, Lists, Settings │
│  • VirusTotal integration, local scanner (WHOIS/DNS/Web), DB         │
│  • Packet sniffer (Scapy) → rolling stats, tray notifications        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Desktop application

### Authentication
- Login / Create account
- SQLite database (`UserInformation.db`) for users and scan history
- On successful login, the Flask backend starts and the current username is set

### Analyze Address (Scanner)
- Enter a URL, domain, or IP address
- **Custom Scan**: local scoring engine (WHOIS, DNS, Web/TLS, IP rules)
- **Deep Scan**: VirusTotal API + local scanner (toggle)
- Results: total risk score, WHOIS/DNS/Web sub-scores, verdict (SECURE → MALICIOUS)
- Scan history saved to JSONL and database; system tray notification for new scan results

### History File
- Table of past scans (timestamp, kind, target, verdict)
- Context menu: add to whitelist or blacklist, delete entry
- Reset scan history button
- Live refresh every 3 seconds

### Navigation Logs
- Table of navigations recorded by the extension (timestamp, target, action)
- Entries come from Logging, Silent, and Safe modes
- Reset navigation history button
- Live refresh every 3 seconds

### Packets
Two views:

1. **Sniffer Graph** — rolling chart of network activity (bytes in/out) over the last 60 seconds
2. **Protocol Animation** — TCP vs UDP packet counts (last 10s) with animated indicators

Packet capture runs in the background via Scapy; data is aggregated per second in a rolling window.

### White/Black List
- **White List**: domains/URLs allowed without blocking (e.g. in Safe mode)
- **Black List**: domains/URLs always blocked by the extension (interstitial)
- Lists are per-user and used by the extension when the backend is reachable

### Settings
- Themes: Default, Dark, Light, Dracula, Cyberpunk
- Mute notifications (tray popups)
- Reset scan history / Reset navigation history
- User account: change username, change password, delete account

---

## Browser extension (dns-protect)

A Chrome/Chromium extension that connects to the local Flask backend. It requires the desktop app to be running and the user to be logged in.

### Extension modes

| Mode   | Behavior                                                                 |
|--------|---------------------------------------------------------------------------|
| **None**   | Extension effectively disabled; no logging or blocking                   |
| **Logging**| Logs each main-frame navigation to the app (no blocking, no auto-scan)   |
| **Silent** | Logs navigations and triggers background scans for each visited URL     |
| **Safe**   | Intercepts every navigation; user must approve or deny before continuing |

### Safe mode flow
1. User navigates to a URL
2. Extension redirects to an interstitial page (“Check this site before proceeding”)
3. User can:
   - **Continue** — visit the site once
   - **Send scan** — request a VirusTotal + local scan (queued by the app)
   - **Go back** — cancel navigation
   - **Whitelist** — add to whitelist and proceed
   - **Blacklist** — add to blacklist and show block page

### Blacklist enforcement
- In **Logging** and **Silent** modes, blacklisted URLs are blocked with a red interstitial (“Blocked Website”)
- User can “Go Back” or “Continue Anyway” (one-time bypass)
- In **Safe** mode, blacklist is checked before showing the review interstitial

### Popup
- Connection status (Connected / Disconnected to backend)
- Mode selector: None, Logging, Silent, Safe
- Short hint for each mode

### Backend dependency
- Extension polls `/health` to check if the app is running
- All list checks, logging, and scan requests go through the backend

---

## Scanner module (local scoring)

The `scanner/` package evaluates domains and URLs using:

| Category | Signals |
|----------|---------|
| **WHOIS** | Domain age, registrar reputation, privacy status, expiration |
| **DNS**   | A/AAAA records, TTL, nameservers, MX/SPF/DMARC |
| **Web**   | TLS certificate validity, HTTP security headers |
| **IP**    | IP-based risk indicators (if input is an IP) |

Risk score (0–100) is mapped to verdicts: SECURE, SAFE, NEUTRAL, CAUTION, SUSPICIOUS, DANGEROUS, MALICIOUS.

---

## Packet monitoring and notifications

### Rolling aggregator
- Per-second buckets: bytes in/out, TCP/UDP/DNS counts, unique source/destination IPs
- DNS metadata: qnames, qtypes, rcode (for NXDOMAIN), TXT queries

### Notifications (system tray)

1. **High packet rate**
   - Triggers when packets in the last 10s exceed threshold (default 12,000)
   - Edge-triggered: no repeat while traffic stays above threshold
   - Re-arms when traffic drops below, then can alert again (subject to cooldown)

2. **DNS anomaly (heuristic)**
   - Evaluates last 60 seconds
   - Signals: unique DNS names, NXDOMAIN rate, TXT bursts, high-entropy long labels, destination-IP spikes
   - Requires multiple strong signals to reduce false positives
   - Edge-triggered with cooldown

### Configuration
Settings live in `src/VT_Cache/settings.json` (e.g. `packet_alert_threshold_10s`, `dns_alert_enabled`, `dns_unique_qnames_threshold_60s`).

---

## Repository structure

```
Capstone/
├── src/
│   ├── main.py                 # App entry point
│   ├── gui/                    # All windows and widgets
│   │   ├── Autentication_Window.py
│   │   ├── sidebar.py          # Main layout, sniffer wiring, notifications
│   │   ├── Scanner_Window.py
│   │   ├── history_window.py
│   │   ├── log_window.py
│   │   ├── WhiteBlackList_Window.py, WhiteList_Window.py, BlackList_Window.py
│   │   ├── SnifferContainer_Window.py, packet_sniffer_widget.py, ProtocolAnimation_Window.py
│   │   ├── settings_window.py
│   │   └── ...
│   ├── logic/
│   │   ├── vt_service.py       # VirusTotal API, cache, history
│   │   ├── scanner_service.py  # Local scanner thread, cache
│   │   └── backend_server.py   # Flask API for extension
│   ├── SQL_Alchemy/            # User and Addresses tables
│   └── VT_Cache/               # JSONL logs, caches, settings
├── scanner/                    # Domain/URL scoring engine
│   ├── scanner.py
│   ├── features/               # whois, dns, web, ip
│   └── scoring/                # rules_*
├── sniffer_test/
│   ├── packet_sniffer.py       # Scapy capture, metadata extraction
│   ├── aggregator.py           # Rolling per-second buckets
│   └── sniffer_worker.py       # Emits snapshots to UI
└── dns-protect/                # Browser extension
    ├── manifest.json
    ├── html/                   # popup, safe_interstitial, blacklist_interstitial
    ├── scripts_/               # background, popup, interstitials
    └── styles/
```

---

## Requirements

- Python 3.10+
- Chrome or Chromium (for the extension)
- VirusTotal API key (for Deep Scan)
- Network capture permissions for sniffing (may require admin/elevated rights on some systems)

### Python packages

```bash
pip install PySide6 scapy requests python-dotenv sqlalchemy tldextract dnspython python-whois flask flask-cors
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Zeviant/Capstone.git
cd Capstone
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate
pip install PySide6 scapy requests python-dotenv sqlalchemy tldextract dnspython python-whois flask flask-cors
```

### 2. VirusTotal API key

Set `VIRUSTOTAL_API_KEY` in your environment or a `.env` file in the project root.

```powershell
# Windows PowerShell
$env:VIRUSTOTAL_API_KEY="your_api_key_here"
```

```bash
# Linux/macOS
export VIRUSTOTAL_API_KEY="your_api_key_here"
```

### 3. Load the browser extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `dns-protect` folder

The extension expects icon files at `dns-protect/images/` (icon-16.png, icon-32.png, icon-48.png, icon-128.png). Add placeholders if missing.

---

## Run

```bash
python -m src.main
```

1. Log in (or create an account)
2. The Flask backend starts automatically
3. The extension will show “Connected” when it can reach the backend
4. Packet sniffer starts in the background; use the Packets page to view stats and notifications

---

## Testing alerts

- **Packet rate**: Generate heavy traffic (e.g. large download, streaming) and adjust `packet_alert_threshold_10s` if needed.
- **DNS anomaly**: In PowerShell, run many NXDOMAIN lookups to trigger the heuristic:
  ```powershell
  1..400 | ForEach-Object { Resolve-DnsName ("nope-$_.invalid") -ErrorAction SilentlyContinue | Out-Null }
  ```

---

## Notes and limitations

- Most web traffic is TLS-encrypted; detection uses metadata and behavioral patterns.
- Heuristic alerts are indicators, not proof of compromise.
- Packet capture depends on interface and permissions.
- The extension requires the desktop app to be running and the user logged in.

---

## Disclaimer

This project is for defensive security monitoring and educational use. Only capture and analyze traffic on networks and systems you own or are authorized to test.
