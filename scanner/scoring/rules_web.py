from datetime import datetime, timezone

def score_tls_certificate(tls: dict | None, domain_creation_date: datetime | None) -> tuple[int, str] | None:
    
    if not tls:
        return 5, "No HTTPS certificate found; site served over HTTP only"

    if not domain_creation_date:
        return None

    score = 0
    reasons = []

    now = datetime.now(timezone.utc)
    domain_age_days = (now - domain_creation_date).days
    cert_age_days = (now - tls["not_before"]).days

    # --- Certificate issued very soon after domain registration ---
    delta_days = (tls["not_before"] - domain_creation_date).days
    if 0 <= delta_days <= 3 and domain_age_days <= 365:
        score += 8
        reasons.append("TLS certificate issued within 3 days of domain registration")
    elif 0 <= delta_days <= 7 and domain_age_days <= 730:
        score += 3
        reasons.append("TLS certificate issued shortly after domain registration")

    # --- Wildcard certificate ---
    if tls.get("is_wildcard", False) and domain_age_days <= 730:
        score += 3
        reasons.append("Wildcard TLS certificate detected")

    # --- Very young certificate (cert age alone) ---
    if cert_age_days <= 7:
        score += 3
        reasons.append("TLS certificate issued within the last 7 days")

    if score == 0:
        reasons.append("TLS certificate characteristics appear normal")

    return score, "; ".join(reasons)
