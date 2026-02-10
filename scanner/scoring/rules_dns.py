from features.dns import classify_ns_provider

# --- A / AAAA records + TTL ---
def score_dns_A_AAAA(metrics: dict) -> tuple[int, str] | None:
    if not metrics:
        return None
    
    record_count = metrics["record_count"]
    min_ttl = metrics["min_ttl"]

    score = 0
    reasons = []

    # --- TTL SCORING ---
    if min_ttl is not None:
        if min_ttl <= 40:
            score += 1
            reasons.append("Low DNS TTL (≤40s)")

    # --- A/AAAA RECORD COUNT SCORING ---
    if record_count >= 10:
        score += 2
        reasons.append("Very high number of A/AAAA records detected (≥10)")
    elif record_count >= 7:
        score += 1
        reasons.append("High number of A/AAAA records detected (≥7)")
    
    # --- FAST-FLUX BEHAVIOR ---
    if min_ttl is not None and min_ttl <= 30 and record_count >= 15:
        score += 10
        reasons.append("Extreme fast-flux behavior detected: ≤30s TTL with ≥15 records")
    elif min_ttl is not None and min_ttl <= 60 and record_count >= 10:
        score += 4
        reasons.append("Possible fast-flux behavior detected: ≤60s TTL with ≥10 records")

    if score == 0:
        reasons.append("TTL and number of A/AAAA records is normal")
    
    return score, "; ".join(reasons)

# --- NS RECORDS ---
def score_ns_records(ns_records: list[str] | None) -> tuple[int, str] | None:
    if not ns_records:
        return None

    provider = classify_ns_provider(ns_records)

    if provider == "suspicious_free_dns":
        return (5, "Domain uses free or abuse-prone DNS provider")

    if provider == "unknown":
        return (2, "Domain uses unknown DNS provider")

    return (0, "DNS provider is well-known or reputable")

# --- MAIL CONFIGURATION ---
def score_mail_configuration(
    mx_records: list[str] | None,
    spf_present: bool,
    dmarc_present: bool
) -> tuple[int, str]:

    score = 0
    reasons = []

    if not mx_records:
        score += 2
        reasons.append("No MX records present")

    if not spf_present:
        score += 1
        reasons.append("No SPF record found")

    if not dmarc_present:
        score += 1
        reasons.append("No DMARC policy found")

    if not mx_records and not spf_present and not dmarc_present:
        score += 2
        reasons.append("No mail configuration detected.")

    if mx_records and spf_present and dmarc_present:
        score -= 6
        reasons.append("Proper mail configuration detected")

    return score, "; ".join(reasons)
