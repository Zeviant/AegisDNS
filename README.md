# VirusTotal Lookup Tool

A Python script that performs VirusTotal scans for domains and IP addresses.

## Features

- Lookup domains and IP addresses using VirusTotal API
- Rate limiting to comply with VirusTotal API limits (15-second cooldown)
- Caching system to avoid redundant lookups
- Detailed scan results with engine-specific information
- Support for both IPv4 and IPv6 addresses

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeviant/Capstone.git
   cd Capstone
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your VirusTotal API key:
   ```bash
   export VT_API_KEY="your_api_key_here"
   ```

## Usage

```bash
python3 vt_lookup.py 'domain_or_ip'
```

### Examples

```bash
# Check a domain
python3 vt_lookup.py 'google.com'

# Check an IP address
python3 vt_lookup.py '8.8.8.8'
```

## Rate Limiting

The script implements a 15-second cooldown between requests to comply with VirusTotal's rate limits:
- 4 requests per minute (free tier)
- 500 requests per day (free tier)

## Files

- `vt_lookup.py` - Main script
- `vt_cache.json` - Cache file for scan results (auto-generated)
- `vt_history.json` - History log for lookups (auto-generated)
- `requirements.txt` - Python dependencies

## License

This project is part of a Capstone course project.