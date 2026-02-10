from features.whois import (
    fetch_whois,
    extract_creation_date,
    extract_registrar,
    extract_privacy,
    extract_expiration_date
    )
from scoring.rules_whois import (
    score_domain_age,
    score_registrar,
    score_privacy,
    score_expiration_date
    )
from features.dns import(
    fetch_dns,
    extract_A_AAAA_metrics,
    extract_ns_records,
    extract_mx_records,
    extract_txt_records,
    has_spf,
    has_dmarc
    
)
from scoring.rules_dns import(
    score_dns_A_AAAA,
    score_ns_records,
    score_mail_configuration
)
from features.web import (
    fetch_tls_certificate,
    fetch_http_security_headers
)
from scoring.rules_web import (
    score_tls_certificate,
    score_http_security_headers
)
from scoring.rules_ip import score_ip_indicator

from urllib.parse import urlparse
import tldextract
import ipaddress

def is_apex_domain(indicator: str) -> bool:
    """
    Returns True if the indicator is an apex/root domain like example.com or example.co.uk
    Returns False for subdomains like docs.github.com
    """
    ext = tldextract.extract(indicator)
    return bool(ext.domain and ext.suffix) and not ext.subdomain

def normalize_indicator(indicator: str) -> dict:
    host = None
    domain = None
    url = None
    is_ip = False

    if "://" in indicator:
        parsed = urlparse(indicator)
        host = parsed.hostname
        url = indicator
    else:
        host = indicator

    # --- IP detection ---
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except Exception:
        is_ip = False

    if not is_ip:
        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            domain = f"{ext.domain}.{ext.suffix}"

    return {
        "input_type": "ip" if is_ip else ("url" if url else "domain"),
        "domain": domain,
        "host": host,
        "url": url,
        "is_ip": is_ip
    }

def scan_domain(indicator: str):
    ctx = normalize_indicator(indicator)

    domain = ctx["domain"]
    host = ctx["host"]
    url = ctx["url"]
    is_ip = ctx["is_ip"]

    signals = []
    risk_score = 30

    # |-------------------------|
    # |*** ------ IPs ------ ***|
    # |-------------------------|

    if is_ip:
        score, reason = score_ip_indicator(
            ip=host,
            url=url
        )

        risk_score += score
        signals.append({
            "name": "ip_indicator",
            "risk_score": score,
            "reason": reason
        })

        return {
            "indicator": indicator,
            "type": "indicator",
            "domain": None,
            "total_risk_score": max(min(risk_score, 100), 0),
            "signals": signals
        }

    # |-------------------------|
    # |*** ----- WHOIS ----- ***|
    # |-------------------------|

    who = fetch_whois(domain)
    if not who:
        risk_score += 3
        signals.append({
            "name": "whois_failure",
            "risk_score": 3,
            "reason": "WHOIS lookup failed."
        })

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

    # --- EXPIRATION DATE ---
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

    # |-------------------------|
    # |*** ------ DNS ------ ***|
    # |-------------------------|

    # --- TTL + A/AAAA RECORDS ---
    dns_data = fetch_dns(domain)
    dns_metrics = extract_A_AAAA_metrics(dns_data)

    dns_result = score_dns_A_AAAA(dns_metrics)
    if dns_result:
        score, reason = dns_result
        risk_score += score

        signals.append({
            "name": "dns_A_AAAA",
            "record_count": dns_metrics["record_count"],
            "min_ttl": dns_metrics["min_ttl"],
            "risk_score": score,
            "reason": reason
        })
    else:
        risk_score += 3
        signals.append({
            "name": "dns_failure",
            "risk_score": 3,
            "reason": "DNS resolution failed."
        })

    # --- NS RECORDS ---
    ns_records = extract_ns_records(domain)

    ns_result = score_ns_records(ns_records)
    if ns_result:
        score, reason = ns_result
        risk_score += score
        signals.append({
            "name": "dns_ns",
            "nameservers": ns_records,
            "risk_score": score,
            "reason": reason
        })

    # --- MAIL CONFIGURATION
    if is_apex_domain(domain):
        txt_records = extract_txt_records(domain)
        spf_present = has_spf(txt_records)
        dmarc_present = has_dmarc(domain)
        mx_records = extract_mx_records(domain)

        mail_score, mail_reason = score_mail_configuration(
            mx_records,
            spf_present,
            dmarc_present
        )
    else:
        mail_score, mail_reason = 0, "Mail configuration not evaluated for subdomains"
        mx_records = None
        spf_present = False
        dmarc_present = False

    risk_score += mail_score
    signals.append({
        "name": "dns_mail",
        "mx_records": mx_records,
        "spf_present": spf_present,
        "dmarc_present": dmarc_present,
        "risk_score": mail_score,
        "reason": mail_reason
    })

    # |-------------------------|
    # |*** ------ WEB ------ ***|
    # |-------------------------|

    web_url = None

    if url:
        web_url = url
    else:
        # domain input
        web_url = f"https://{domain}"
    
    # --- TLS ---
    tls_metrics = fetch_tls_certificate(host)

    tls_result = score_tls_certificate(
        tls_metrics,
        creation_date
    )

    if tls_result:
        score, reason = tls_result
        risk_score += score
        signals.append({
            "name": "tls_certificate",
            "risk_score": score,
            "details": {
                "issuer": tls_metrics.get("issuer") if tls_metrics else None,
                "issue_date": tls_metrics.get("not_before").date().isoformat() if tls_metrics and tls_metrics.get("not_before") else None,
                "validity_days": tls_metrics.get("validity_days") if tls_metrics else None,
            },
            "reason": reason
        })

    # --- HTTP SECURITY HEADERS ---
    headers = fetch_http_security_headers(web_url)
    headers_result = score_http_security_headers(headers)

    if headers_result:
        score, reason = headers_result
        risk_score += score
        signals.append({
            "name": "http_security_headers",
            "present": headers,
            "risk_score": score,
            "reason": reason
        })
    else:
        risk_score += 1
        signals.append({
            "name": "headers_failure",
            "risk_score": 1,
            "reason": "HTTP security headers could not be retrieved"
        })

    # |-------------------------|
    # |*** ---- RESULTS ---- ***|
    # |-------------------------|

    return {
        "indicator": indicator,
        "domain": domain,
        "total_risk_score": max(min(risk_score, 100), 0),
        "signals": signals
    }

if __name__ == "__main__":
    print(scan_domain("netflix.com"))
