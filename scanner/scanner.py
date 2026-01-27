from features.whois import (
    fetch_whois,
    extract_creation_date,
    extract_registrar,
    extract_privacy,
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
    print(who)
    creation_date = extract_creation_date(who)
    registrar = extract_registrar(who)
    privacy = extract_privacy(who)
    expiration_date = extract_expiration_date(who)

    # --- DOMAIN AGE ---
    age_result = score_domain_age(creation_date)
    if age_result:
        score, reason = age_result
        risk_score += score

        signals.append({
            "name": "domain_age",
            "created_date": creation_date.date().isoformat(),
            "risk_score": score,
            "reason": reason
        })

    # --- REGISTRAR ---
    registrar_result = score_registrar(registrar)
    if registrar_result:
        score, reason = registrar_result
        risk_score += score
        signals.append({
            "name": "registrar",
            "value": registrar,
            "risk_score": score,
            "reason": reason
        })

    # --- PRIVACY ---
    privacy_result = score_privacy(privacy)
    if privacy_result:
        score, reason = privacy_result
        risk_score += score
        signals.append({
            "name": "privacy",
            "private_elements": privacy,
            "risk_score": score,
            "reason": reason
        })

    # --- EXPIRTAION DATE ---
    expiration_date_result = score_expiration_date(expiration_date)
    if expiration_date_result:
        score, reason = expiration_date_result
        risk_score += score
        signals.append({
            "name": "domain_expiration",
            "expiration_date": expiration_date.date().isoformat(),
            "risk_score": score,
            "reason": reason
        })

    return{
        "indicator": domain,
        "type": "domain",
        "total_risk_score": risk_score,
        "signals": signals
    }

if __name__ == "__main__":
    print(scan_domain("example.com"))

    
