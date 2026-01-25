from features.whois import (
    fetch_whois,
    extract_domain_age,
    extract_registrar,
    extract_privacy_flag,
    extract_expiration_date
    )
from scoring.rules import (
    score_domain_age,
    score_registrar,
    score_privacy,
    score_expiration_date
    )
from datetime import datetime, timezone, timedelta

def scan_domain(domain: str):
    signals = []
    risk_score = 0

    who = fetch_whois(domain)
    age = extract_domain_age(who)
    registrar = extract_registrar(who)
    privacy = extract_privacy_flag(who)
    expiration = extract_expiration_date(who)

    # --- DOMAIN AGE ---
    age_result = score_domain_age(age)
    if age_result:
        score, reason = age_result
        risk_score += score

        # This is just used to get a well-formated creation date. Maybe can be used in the application later.
        created_date = None
        if age is not None:
            created_date = (
                datetime.now(timezone.utc) - timedelta(days=age)
            ).date().isoformat()

        signals.append({
            "name": "domain_age",
            "value_days": age,
            "created_date": created_date,
            "score": score,
            "reason": reason
        })

    # --------------- WIP ----------------

    # --- REGISTRAR ---
    registrar_result = score_registrar(registrar)

    # --- PRIVACY ---
    privacy_result = score_privacy(privacy)

    # --- EXPIRTAION DATE ---
    expiration_result = score_expiration_date(expiration)

    return{
        "indicator": domain,
        "type": "domain",
        "risk_score": risk_score,
        "signals": signals
    }

if __name__ == "__main__":
    print(scan_domain("example.com"))

    
