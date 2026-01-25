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

def extract_domain_age(w, now_utc=None) -> int | None:
    if not w:
        return None
    
    created = normalize_datetime(w.creation_date)

    if not created:
        return None
    
    if not now_utc:
        now_utc = datetime.now(timezone.utc)

    return (now_utc - created).days

def extract_registrar(w) -> str | None:
    if not w:
        return None

    return w.registrar

def extract_privacy_flag(w) -> bool | None:
    if not w:
        return None
    
    raw = str(w).lower()
    # Be careful with keywords here. Adding more or broader terms increases the chance of false positives.
    # Also, could maybe research common privacy registrant email domains (e.g. @whoisguard.com, @privacyprotect.org)
    return any(keyword in raw for keyword in ["privacy", "redacted", "whoisguard", "proxy", "protected"])

def extract_expiration_date(w) -> datetime | None:
    if not w:
        return None
    
    return normalize_datetime(w.expiration_date)