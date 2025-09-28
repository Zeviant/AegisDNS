#!/usr/bin/env python3

"""
The statement above is called a shebang line, which tells a 
Unix system to run this program with python3
"""

"""
vt_lookup.py
This script performs a VirusTotal scan lookup for a given
domain or IP address.

Note: Virustotal will be abbreviated as VT in code.
"""

"""
|*------USAGE------*|

In your terminal, set the environment variable for the API key:
export VT_API_KEY="api_key"

Then run the script with a domain or IP address, as follows:
python3 vt_lookup.py 'domain/ip'

A 15 second cooldown is implemented to align with VirusTotal's rate limits.
(4 requests per minute max, 500 requests a day max)

"""

import os, sys, time, json, requests, ipaddress, re

CACHE_FILE = "vt_cache.json"        # Saves results to avoid redundant lookups
HISTORY_FILE = "vt_history.json"    # Logs all address lookups and time of lookup
VIRUSTOTAL_RATELIMIT = 15           # seconds of cooldown between requests

VT_IP_ENDPOINT = "https://www.virustotal.com/api/v3/ip_addresses/{}"
VT_DOMAIN_ENDPOINT = "https://www.virustotal.com/api/v3/domains/{}"

# -------- Cache I/O --------

# Loads existing cache file. If none exists, creates one.
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_call": 0, "cache": {}}

# Writes analysis information to cache file
def save_to_cache(state):
    with open(CACHE_FILE, "w") as f:
        json.dump(state, f)

# -------- Scan rate limiting --------

# Limits scan rate to 4 per minute
def wait_for_cooldown(last_call):
    elapsed = time.time() - last_call
    if elapsed < VIRUSTOTAL_RATELIMIT:
        remaining = int(VIRUSTOTAL_RATELIMIT - elapsed) + 1
        print(f"[rate-limit] Waiting ~{remaining}s for next analysis...")
        while time.time() - last_call < VIRUSTOTAL_RATELIMIT:
            time.sleep(1)

# -------- Input validation --------

# Regex used to check whether a string can be a domain name
DOMAIN_RE = re.compile(
     r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,63}\.?$"
)

# Cleans user input (lowercase, blank space removal, trailing period removal)
def normalize_target(s: str) -> str:
    s = s.strip()
    return s.lower().rstrip(".")

# Checks whether the user input is an IP address, domain, or neither
def classify_kind(target: str) -> str:
    try:
        # Python function that tries to parse the input as an IPv4 or IPv6 address
        ipaddress.ip_address(target)
        return "ip"
    except ValueError:
        pass
        # If not an IP address, try to parse it as a domain name.
    if DOMAIN_RE.match(target):
        return "domain"
    raise ValueError("Input is not a valid IP or domain.")

# -------- VirusTotal scan request --------

# Performs VirusTotal scan
def vt_ip_lookup(apikey: str, target: str, kind: str) -> dict:
    url = VT_IP_ENDPOINT.format(target) if kind == "ip" else VT_DOMAIN_ENDPOINT.format(target)  # Attach ip/domain into the {} part of the url 
    headers = {"x-apikey": apikey}                                                              # Format required by VirusTotal to send API key
    resp = requests.get(url, headers=headers, timeout=20)                                       # Attach API key, send HTTP GET request to URL. Store results.

    # REQUEST SUCCESFUL
    if resp.status_code == 200:
        return resp.json()
    
    # REQUEST FAILED
    elif resp.status_code == 401:
        raise RuntimeError("401 Unauthorized — check your VT API key (x-apikey).")
    elif resp.status_code == 404:
        raise RuntimeError(f"404 Not found — VT has no report for {kind} '{target}'.")
    elif resp.status_code == 429:
        raise RuntimeError("429 Too Many Requests — you hit VT rate limits/quota.")
    else:
        raise RuntimeError(f"VT API error: {resp.status_code} {resp.text}")

# -------- Scan summaries -------- 

# Displays relevant engines
def print_engines(attributes: dict):
    engines = attributes.get("last_analysis_results", {}) or {}
    
    # Filters engines that found address to be malicious or suspicious
    malicious = [(eng, info) for eng, info in engines.items() if info.get("category") == "malicious"]
    suspicious = [(eng, info) for eng, info in engines.items() if info.get("category") == "suspicious"]

    if malicious:
        print("\nEngines that flagged this as MALICIOUS:")
        for eng, info in malicious:
            print(f" - {eng}: {info.get('category')}")
        
    if suspicious:
        print("\nEngines that flagged this as SUSPICIOUS:")
        for eng, info in suspicious:
            print(f" - {eng}: {info.get('category')}")
    
    if not malicious and not suspicious:
        print("\nNo engines flagged this IP as malicious or suspicious.")
    
# Formats VirusTotal report in a more human-readable way
def summarize_response(target: str, data: str, kind: str):
    attributes = data.get("data", {}).get("attributes", {})
    stats = attributes.get("last_analysis_stats", {})
    dt = attributes.get("last_analysis_date", None)
    whois = attributes.get("whois", "")
    reputation = attributes.get("reputation", None)

    title = "IP" if kind == "ip" else "Domain"
    print(f"\n=== VirusTotal {title} summary ===")
    print(f"{title}: {target}")

    if dt:
        print(f"Last analysis timestamp: {dt}")

    if reputation is not None and kind == "domain":
        print(f"Reputation (VT): {reputation}")
    
    print("Last analysis stats:", stats)

    # Domain-specific additional info
    if kind == "domain":
        registrar = attributes.get("registrar")
        creation_date = attributes.get("creation_date")  # epoch seconds if present
        last_dns = attributes.get("last_dns_records", [])
        if registrar:
            print(f"Registrar: {registrar}")
        if creation_date:
            print(f"Creation date (epoch): {creation_date}")
        if last_dns:
            # print a few recent DNS records compactly
            print("\nRecent DNS records (truncated):")
            for rec in last_dns[:5]:
                rtype = rec.get("type")
                rval = rec.get("value")
                print(f" - {rtype}: {rval}")

    if whois:
        print("\nWHOIS:")
        print(whois[:1500] + ("..." if len(whois) > 1500 else ""))

    print_engines(attributes)
    
    print("==========================\n")

# -------- MAIN --------

def main():
    # get API key
    api_key = os.environ.get("VT_API_KEY")
    if not api_key:
        api_key = input("API key not found in environment. Please enter VirusTotal API key: ").strip()
        if not api_key:
            print("ERROR_000 — API key failure. Exiting...")
            sys.exit(1)

    # get IP/domain
    if len(sys.argv) >= 2:
        raw = sys.argv[1]
    else:
        raw = input("Domain or IP to lookup: ")
    target = normalize_target(raw)
    if not target:
        print("ERROR_001 — No target provided. Exiting...")
        sys.exit(1)

    
    # detect type (ip/domain)
    try:
        kind = classify_kind(target)
    except ValueError as e:
        print(f"ERROR_002 — {e}")
        sys.exit(1)

    state = load_cache()

    # Check for the IP in state
    cache = state.get("cache", {})
    if target in cache:
        print("[cache] Found cached result — using cached data.")
        summarize_response(target, cache[target], kind)
        return
    
    # Check cooldown
    last_call = state.get("last_call", 0)
    wait_for_cooldown(last_call)

    # Perform VirusTotal analysis
    try:
        print(f"[VirusTotal] Querying VirusTotal for {kind} '{target}' ...")
        data = vt_ip_lookup(api_key, target, kind)
    except Exception as e:
        print("Error during lookup:", e)
        sys.exit(1)

    state["cache"][target] = data
    state["last_call"] = time.time()
    save_to_cache(state)

    summarize_response(target, data, kind)

if __name__ == "__main__":
    main()
