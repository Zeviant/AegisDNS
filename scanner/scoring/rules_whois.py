from datetime import datetime, timezone
from scoring.registrar_list import match_registrar_risk

# --- DOMAIN AGE ---
def score_domain_age(created: datetime | None) -> tuple[int, str] | None:
    """
    Scores domain age. Older = likely safer. Newer = more suspicious.
    """
    if not created:
        return None
    
    now = datetime.now(timezone.utc)
    age_days = (now - created).days
    if age_days < 7:
        return (30, "Domain registered less than 7 days ago")
    elif age_days < 30:
        return (15, "Domain registered less than a month ago")
    elif age_days < 90:
        return (10, "Domain registered less than 3 months ago")
    elif age_days < 365:
        return (5, "Domain registered less than 1 year ago")
    elif age_days >= 365 and age_days < 730:
        return (0, "Domain age does not indicate any particular risk")
    elif age_days >= 730 and age_days < 1825:
        return(-5, "Domain registered more than 2 years ago")
    elif age_days >= 1825:
        return(-10, "Domain registered more than 5 years ago")
    
    return None

# --- REGISTRAR ---
# NOTE: SERIOUSLY CONSIDER REBALANCING RISK CLASSES IN registrar_list.py.
def score_registrar(registrar : str | None) -> tuple[int, str] | None:
    """
    Registrar: A domain registrar is a company authorized to register domain names on behalf of individuals or organizations.
    A lot of cases can be handled here, some registrars are more reputable and others are more suspicious.
    Uses substring matching against known registrar lists to handle varying WHOIS format strings.
    """
    if not registrar:
        return None
    
    risk = match_registrar_risk(registrar)

    if risk == "high":
        return (5, "Registrar has high abuse density")
    elif risk == "medium":
        return (3, "Registrar has elevated abuse density")
    elif risk == "low":
        return (1, "Registrar has above average abuse density")
    
    return (0, "Registrar does not indicate malicious activity")

def score_privacy(privacy : bool | None) -> tuple[int, str] | None:
    """
    Some registrars offer WHOIS privacy protection. Often used by individuals who want privacy, companies that don't want spam, etc.
    However, it is also very often used by malicious actors.
    """
    if privacy is None:
        return None
    
    if privacy:
        return(3, "Privacy protection has been detected by the scanner")
    
    return (0, "No privacy protection has been detected by the scanner")

def score_expiration_date(edt : datetime | None) -> tuple [int, str] | None:
    """
    Domains are rented from registrars for a given amount of time. Malicious or 'disposable' domains tend to register for short durations,
    and often cycle through many different domains to avoid detection. A domain rented for 5 years, for example, is likely to be more reputable
    than one rented for a month.
    """
    if not edt:
        return None
    
    now_utc = datetime.now(timezone.utc)

    remaining = (edt - now_utc).days

    if remaining < 30:
        return(5, "Domain expires in less than 30 days")
    elif remaining < 90:
        return(3, "Domain expires in less than 90 days")
    elif remaining <= 365:
        return(0, "Domain expires in less than a year")
    elif remaining > 365 and remaining < 730:
        return(-3, "Domain expiration date is more than a year from current date")
    elif remaining >= 730:
        return(-7, "Domain expiration date is more than two years from current date")

    return None