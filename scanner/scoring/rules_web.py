from datetime import datetime, timezone

# --- TLS ---
def score_tls_certificate(tls: dict | None, domain_creation_date: datetime | None) -> tuple[int, str] | None:
    
    if not tls:
        return 10, "No HTTPS certificate found; site served over HTTP only"

    if not domain_creation_date:
        return None

    score = 0
    reasons = []

    now = datetime.now(timezone.utc)
    domain_age_days = (now - domain_creation_date).days
    cert_age_days = (now - tls["not_before"]).days

    # --- Certificate issued very soon after domain registration ---
    delta_days = (tls["not_before"] - domain_creation_date).days
    if 0 <= delta_days <= 3 and domain_age_days <= 90:
        score += 6
        reasons.append("TLS certificate issued within 3 days of domain registration")
    elif 0 <= delta_days <= 7 and domain_age_days <= 365:
        score += 3
        reasons.append("TLS certificate issued shortly after domain registration")

    # --- Wildcard certificate ---
    if tls.get("is_wildcard", False) and domain_age_days <= 730:
        score += 1
        reasons.append("Wildcard TLS certificate detected")

    # --- Very young certificate  ---
    if cert_age_days <= 7:
        score += 3
        reasons.append("TLS certificate issued within the last 7 days")

    if score == 0:
        reasons.append("TLS certificate characteristics appear normal")

    return score, "; ".join(reasons)

# --- SECURITY HEADERS ---
def score_http_security_headers(headers: dict | None) -> tuple[int, str] | None:
    if not headers:
        return None

    score = 0
    present = []
    missing = []

    # --- per-header scoring ---
    if headers.get("hsts"):
        score -= 2
        present.append("HSTS")
    else:
        score += 2
        missing.append("HSTS")

    if headers.get("csp"):
        score -= 1
        present.append("CSP")
    else:
        score += 1
        missing.append("CSP")

    if headers.get("x_frame"):
        score -= 1
        present.append("X-Frame-Options")
    else:
        score += 1
        missing.append("X-Frame-Options")

    reasons = []
    if present:
        reasons.append(f"Security headers present: {', '.join(present)}")
    if missing:
        reasons.append(f"Security headers missing: {', '.join(missing)}")
    if not present and not missing:
        reasons.append("No security headers info available")

    if len(present) == 3:
        score -= 1
    
    if len(missing) == 3:
        score += 1

    reason = "; ".join(reasons)

    return score, reason



