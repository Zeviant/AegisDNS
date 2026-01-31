def score_html_credentials(metrics: dict | None) -> tuple[int, str] | None:
    if not metrics or not metrics.get("has_form"):
        return None

    pw_count = metrics.get("password_input_count", 0)
    external_actions = metrics.get("external_form_actions", 0)

    # No credential exfiltration possible → no risk
    if pw_count < 1 or external_actions < 1:
        return 0, ""
    
    score = 0
    reasons = []

    score += 10
    reasons.append("Password submitted to external domain")

    if pw_count > 1:
        score += 3
        reasons.append("Multiple password fields detected")

    if metrics.get("login_keywords"):
        score += 2
        reasons.append("Login-related keywords present")

    if metrics.get("brand_keywords"):
        score += 4
        reasons.append("Brand impersonation keywords detected")

    return score, "; ".join(reasons)
