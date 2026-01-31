from datetime import datetime, timezone
from scoring.registrar_list import HIGH_RISK_REGISTRARS, MEDIUM_RISK_REGISTRARS, LOW_RISK_REGISTRARS, normalize_registrar

# --- DOMAIN AGE ---
def score_domain_age(created: datetime | None) -> tuple[int, str] | None:
    """
    Scores domain age. Older = likely safer. Newer = sus.
    """
    if not created:
        return None
    
    now = datetime.now(timezone.utc)
    age_days = (now - created).days
    if age_days < 7:
        return (30, "Domain registered less than 7 days ago")
    elif age_days < 30:
        return (15, "Domain registered less than 30 days ago")
    elif age_days < 365:
        return (5, "Domain registered less than 1 year ago")
    elif age_days >= 365 and age_days < 730:
        return (0, "Domain age does not indicate any particular risk")
    elif age_days >= 730 and age_days < 1095:
        return(-6, "Domain registered more than 2 years ago")
    elif age_days >= 1095 and age_days < 1825:
        return(-8, "Domain registered more than 3 years ago")
    elif age_days >= 1825:
        return(-10, "Domain registered more than 5 years ago")
    
    return None

# --- REGISTRAR ---
# NOTE: SERIOUSLY CONSIDER REBALANCING RISK CLASSES IN registrar_list.py.
def score_registrar(registrar : str | None) -> tuple[int, str] | None:
    """
    Registrar: A domain registrar is a company authorized to register domain names on behalf of individuals or organizations.
    A lot of cases can be handled here, some registrars are more reputable and others are more sus 🤪.
    """
    if not registrar:
        return None
    
    r = normalize_registrar(registrar)

    if r in HIGH_RISK_REGISTRARS:
        return (5, "Registrar has high abuse density")
    elif r in MEDIUM_RISK_REGISTRARS:
        return (3, "Registrar has elevated abuse density")
    elif r in LOW_RISK_REGISTRARS:
        return (1, "Registrar has above average abuse density")
    
    return (0, "Registrar does not indicate malicious activity")

def score_privacy(privacy : bool | None) -> tuple[int, str] | None:
    """
    Some registrars offer WHOIS privacy protection. Often used by individuals who want privacy, companies that don't want spam, etc.
    However, it is also very often used by malicious actors 😒.
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
    elif remaining < 365:
        return(0, "Domain expires in less than a year")
    elif remaining >= 365 and remaining < 730:
        return(-1, "Domain expiration date is more than a year from current date")
    elif remaining >= 730 and remaining < 1095:
        return(-5, "Domain expiration date is more than two years from current date")
    elif remaining >= 1095:
        return(-10, "Domain expiration date is more than three years from current date")