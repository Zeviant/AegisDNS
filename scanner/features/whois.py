import whois
from datetime import datetime, timezone

def fetch_whois(domain: str):
    try:
        return whois.whois(domain)
    except Exception:
        return None
    
def normalize_datetime(dt):
    if not dt:
        return None
    
    if isinstance(dt, list):
        dt = dt[0]

    if dt.tzinfo is None:
        return dt.replace(tzinfo = timezone.utc)
    
    return dt.astimezone(timezone.utc)

def extract_creation_date(w, now_utc=None) -> datetime | None:
    if not w:
        return None
    
    return normalize_datetime(w.creation_date)

def extract_registrar(w) -> str | None:
    if not w:
        return None

    return w.registrar

PRIVACY_KEYWORDS = {
    # Generic privacy indicators
    "privacy",
    "protected",
    "proxy",
    "redacted",
    "not disclosed",
    "undisclosed",
    "hidden",
    
    # Known privacy/proxy WHOIS strings
    "withheld for privacy",
    "porkbun privacy",
    "contact privacy",
    "private registration",
    "whoistrustee",
    "perfect privacy",
    "identity protection service",
    "privacyprotect.org",
    "whois privacy service",
    "domains by proxy",
    "whoisguard",
    "registrar lock privacy",
    "anonymize",
    "registrant privacy",
    "whoisproxy",
    "domain privacy service",
    "identity-protect.org",
    "anonymous registrant",
    "privacy protection",
    "whois privacy protection",
    "信息保护",                         # “information protection” (Chinese)
    "隐私保护服务",                     # “privacy protection service” (Chinese)
}

def extract_privacy(w) -> bool | None:
    if not w:
        return None
    
    raw = str(w).lower()
    for kw in PRIVACY_KEYWORDS:
        if kw in raw:
            return True

    return False

def extract_expiration_date(w) -> datetime | None:
    if not w:
        return None
    
    return normalize_datetime(w.expiration_date)