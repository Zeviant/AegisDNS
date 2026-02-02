# scoring/rules_ip.py

from features.ip import classify_ip, has_nonstandard_port

def score_ip_indicator(ip: str, url: str | None = None) -> tuple[int, str]:
    score = 20
    reasons = ["Direct IP address encountered during browsing"]

    # --- IP classification ---
    suspicious_ip, ip_reason = classify_ip(ip)
    if suspicious_ip:
        score += 20
        reasons.append(ip_reason)

    # --- Port analysis ---
    if url:
        nonstandard, port = has_nonstandard_port(url)
        if nonstandard:
            score += 10
            reasons.append(f"Non-standard web port detected ({port})")

    return score, "; ".join(reasons)
