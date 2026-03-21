# Capstone

Desktop DNS and network-security analysis tool built with Python + PySide6.

It combines:
- Manual domain/IP/URL checks (VirusTotal + local scoring rules)
- User history, whitelist/blacklist workflows
- Live packet monitoring with rolling network statistics
- Real-time safety notifications (including high packet rate and DNS anomaly heuristics)

---

## What this project does

This app helps you evaluate whether browsing/network activity looks risky by using two complementary layers:

1. **Indicator scanning (on-demand)**  
   You enter a domain, IP, or URL and the app evaluates it using:
   - VirusTotal reputation/results
   - WHOIS signals (age, registrar, privacy, expiration)
   - DNS posture signals (A/AAAA, NS, MX/SPF/DMARC patterns)
   - Web/TLS/header signals

2. **Live traffic monitoring (continuous)**  
   A background packet sniffer aggregates traffic into short time windows and can alert on:
   - High packet-rate bursts
   - Suspicious DNS behavior patterns over time

---

## Key features

- **GUI app** with authentication and multiple analysis pages
- **VirusTotal integration** with built-in cooldown/rate-limit handling
- **Local scan history** stored in JSONL cache files
- **Whitelist / blacklist management**
- **Live packet analytics** (TCP/UDP/DNS counts, unique senders, bytes in/out)
- **Packet-rate alerting** (edge-triggered + cooldown)
- **DNS anomaly alerting** with conservative heuristics to reduce false positives
- **System tray notifications** with mute support from app settings

---

## Repository structure (high level)

- `src/main.py` - GUI entry point
- `src/gui/` - Windows/pages/widgets for the desktop app
- `src/logic/vt_service.py` - VirusTotal calls, caching, history helpers
- `scanner/` - Feature extraction + scoring rules (WHOIS/DNS/WEB/IP)
- `sniffer_test/packet_sniffer.py` - Scapy packet capture + metadata extraction
- `sniffer_test/aggregator.py` - Rolling per-second traffic aggregation
- `sniffer_test/sniffer_worker.py` - Emits snapshots to UI thread
- `src/VT_Cache/` - Runtime cache/history/settings files

---

## Requirements

- Python 3.10+
- Windows/Linux/macOS (developed on Windows)
- Network capture permissions (may require elevated privileges for sniffing)
- VirusTotal API key for scanning features

Install Python packages used by the project (if you do not already have them):

```bash
pip install PySide6 scapy requests python-dotenv sqlalchemy tldextract dnspython python-whois
```

---

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/Zeviant/Capstone.git
   cd Capstone
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   ```

3. Install dependencies (see command above)

4. Set your VirusTotal API key  
   The app reads `VIRUSTOTAL_API_KEY` from environment variables (or `.env` if present).

   **Windows PowerShell**
   ```powershell
   $env:VIRUSTOTAL_API_KEY="your_api_key_here"
   ```

   **Linux/macOS**
   ```bash
   export VIRUSTOTAL_API_KEY="your_api_key_here"
   ```

---

## Run

From the repository root:

```bash
python -m src.main
```

---

## Notifications and anomaly logic

### 1) High packet-rate notification
- Evaluates total packets in the last 10 seconds
- Default threshold: `12,000` packets / 10s
- Edge-triggered:
  - Alerts when crossing from below threshold to above threshold
  - Does not repeatedly notify while traffic remains above threshold
  - Re-arms only after traffic goes back below threshold
- Cooldown supported via settings

### 2) DNS anomaly notification (heuristic)
- Evaluates rolling DNS behavior over 60 seconds
- Designed to be conservative and avoid noisy alerts
- Looks for combinations of suspicious signals such as:
  - High unique DNS qname count
  - High NXDOMAIN ratio
  - High TXT query bursts
  - High-entropy long subdomain labels
  - New destination-IP spikes
- Requires multiple strong signals simultaneously before alerting

---

## Settings (runtime JSON)

Notification and anomaly values can be configured in:
- `src/VT_Cache/settings.json`

Example keys:

```json
{
  "mute_notifications": false,
  "packet_alert_enabled": true,
  "packet_alert_threshold_10s": 12000,
  "packet_alert_cooldown_seconds": 60,
  "dns_alert_enabled": true,
  "dns_alert_cooldown_seconds": 300,
  "dns_alert_min_queries_60s": 140,
  "dns_unique_qnames_threshold_60s": 120,
  "dns_nxdomain_rate_threshold": 0.35,
  "dns_suspicious_label_threshold_60s": 25,
  "dns_txt_query_threshold_60s": 40,
  "dst_ip_spike_threshold_60s": 300
}
```

---

## Quick testing ideas

- **Packet-rate alert**: generate heavy traffic (large download/stream) and tune threshold.
- **DNS anomaly alert**: generate many DNS lookups in PowerShell (e.g., NXDOMAIN burst) and verify tray notifications.

Use conservative defaults first, then calibrate thresholds to your normal browsing profile.

---

## Notes and limitations

- Most web traffic is encrypted (TLS), so detection relies on metadata/behavioral signals.
- Heuristic alerts are indicators, not proof of compromise.
- Capture quality depends on interface permissions and local network setup.

---

## Disclaimer

This project is for defensive security monitoring and educational use.  
Only capture/analyze traffic on networks and systems you own or are authorized to test.
