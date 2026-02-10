from datetime import datetime, timezone

# --- Free / low-cost certificate authorities ---
FREE_TLS_ISSUERS = ["let's encrypt", "zerossl", "buypass"]

# --- TLS ---
def score_tls_certificate(tls: dict | None, domain_creation_date: datetime | None) -> tuple[int, str] | None:
    
    if not tls:
        return 15, "No HTTPS certificate found; site served over HTTP only"

    score = 0
    reasons = []

    # --- Free TLS issuer check  ---
    issuer = (tls.get("issuer") or "").lower()
    if any(free in issuer for free in FREE_TLS_ISSUERS):
        score += 3
        reasons.append("TLS certificate issued by a free certificate authority")

    now = datetime.now(timezone.utc)

    # --- Timing-based checks (require domain_creation_date) ---
    if domain_creation_date:
        domain_age_days = (now - domain_creation_date).days

        # --- Certificate issued very soon after domain registration ---
        delta_days = (tls["not_before"] - domain_creation_date).days
        if 0 <= delta_days <= 3 and domain_age_days <= 90:
            score += 6
            reasons.append("TLS certificate issued within 3 days of domain registration")
        elif 0 <= delta_days <= 7 and domain_age_days <= 365:
            score += 3
            reasons.append("TLS certificate issued shortly after domain registration")
    
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

    if headers.get("hsts"):
        score -= 2
        present.append("HSTS")
    else:
        score += 2
        missing.append("HSTS")

    if headers.get("csp"):
        score -= 2
        present.append("CSP")
    else:
        score += 2
        missing.append("CSP")

    if headers.get("x_frame"):
        score -= 1
        present.append("X-Frame-Options")
    else:
        score += 1
        missing.append("X-Frame-Options")

    if headers.get("x_content_type"):
        score -= 1
        present.append("X-Content-Type-Options")
    else:
        missing.append("X-Content-Type-Options")

    if headers.get("referrer_policy"):
        score -= 1
        present.append("Referrer-Policy")
    else:
        missing.append("Referrer-Policy")

    if headers.get("permissions_policy"):
        score -= 1
        present.append("Permissions-Policy")
    else:
        missing.append("Permissions-Policy")


    reasons = []
    if present:
        reasons.append(f"Security headers present: {', '.join(present)}")
    if missing:
        reasons.append(f"Security headers missing: {', '.join(missing)}")
    if not present and not missing:
        reasons.append("No security headers info available")

    # Bonus score if more than 3 headers set
    if len(present) >= 3:
        score -= 1

    # ADD BONUS PENALTY HERE IF ALL HEADERS ARE MISSING (MAYBE)

    reason = "; ".join(reasons)

    return score, reason



