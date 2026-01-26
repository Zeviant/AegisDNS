from datetime import datetime
from scoring.registrar_list import HIGH_RISK_REGISTRARS, MEDIUM_RISK_REGISTRARS, LOW_RISK_REGISTRARS, normalize_registrar

# --- DOMAIN AGE ---
def score_domain_age(age_days: int | None) -> tuple[int, str] | None:
    """
    Scores domain age. Older = likely safer. Newer = sus.
    """
    
    if age_days is None:
        return None
    
    # CAN ADD MORE CASES // BE MORE SPECIFIC
    if age_days < 7:
        return (30, "Domain registered less than 7 days ago")
    elif age_days < 30:
        return (15, "Domain registered less than 30 days ago")
    elif age_days < 365:
        return (5, "Domain registered less than 1 year ago")
    
    return(0, "Domain age does not indicate any particular risk (Registered more than a year ago).")

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
        return (5, "Registrar has high abuse density.")
    elif r in MEDIUM_RISK_REGISTRARS:
        return (3, "Registrar has elevated abuse density.")
    elif r in LOW_RISK_REGISTRARS:
        return (1, "Registrar has above average abuse density.")
    
    return (0, "Registrar does not indicate malicious activity.")

def score_privacy(privacy : bool | None) -> tuple[int, str] | None:
    """
    Some registrars offer WHOIS privacy protection. Often used by individuals who want privacy, companies that don't want spam, etc.
    However, it is also very often used by malicious actors 😒.
    """
    return

def score_expiration_date(edt : datetime | None) -> tuple [int, str] | None:
    """
    Domains are rented from registrars for a given amount of time. Malicious or 'disposable' domains tend to register for short durations,
    and often cycle through many different domains to avoid detection. A domain rented for 5 years, for example, is likely to be more reputable
    than one rented for a month.
    """
    return