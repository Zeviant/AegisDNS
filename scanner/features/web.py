import ssl
import socket
from datetime import datetime, timezone
import requests

# --- TLS ---
def fetch_tls_certificate(domain: str, port=443) -> dict | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                not_before = datetime.strptime(cert['notBefore'], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                not_after = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                validity_days = (not_after - not_before).days

                # Detect wildcard by checking subjectAltName or CN
                is_wildcard = False
                san = cert.get('subjectAltName', [])
                for typ, val in san:
                    if typ == 'DNS' and val.startswith('*.'):
                        is_wildcard = True
                        break

                # fallback check for CN
                if not is_wildcard:
                    cn = dict(x[0] for x in cert['subject']).get('commonName', '')
                    if cn.startswith('*.'):
                        is_wildcard = True

                issuer = dict(x[0] for x in cert['issuer']).get('organizationName', 'Unknown')

                return {
                    "issuer": issuer,
                    "not_before": not_before,
                    "not_after": not_after,
                    "validity_days": validity_days,
                    "is_wildcard": is_wildcard
                }

    except Exception:
        return None

# --- SECURITY HEADERS ---
def fetch_http_security_headers(url: str) -> dict | None:
    try:
        resp = requests.get(
            url,
            timeout=8,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        headers = resp.headers

        return {
            "hsts": "strict-transport-security" in headers,
            "csp": "content-security-policy" in headers,
            "x_frame": "x-frame-options" in headers
        }

    except Exception:
        return None

