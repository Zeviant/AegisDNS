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
    has_dmarc,
    extract_cname_records
    
)
from scoring.rules_dns import(
    score_dns_A_AAAA,
    score_ns_records,
    score_mail_configuration,
    score_cname_records
)

def is_apex_domain(domain: str) -> bool:
    """
    Returns True if the domain is an apex/root domain like example.com
    Returns False for subdomains like docs.github.com
    """
    return domain.count(".") == 1

def scan_domain(domain: str):
    signals = []
    risk_score = 0

    # |-------------------------|
    # |*** ----- WHOIS ----- ***|
    # |-------------------------|

    who = fetch_whois(domain)
    # print(who)
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

    # --- CNAME RECORDS ---
    cname_records = extract_cname_records(domain)
    cname_result = score_cname_records(cname_records)

    if cname_result:
        score, reason = cname_result
        risk_score += score
        signals.append({
            "name": "dns_cname",
            "cname_records": cname_records,
            "risk_score": score,
            "reason": reason
        })

    # |-------------------------|
    # |*** ------ WEB ------ ***|
    # |-------------------------|

    # do tmrw

    # |-------------------------|
    # |*** ---- RESULTS ---- ***|
    # |-------------------------|

    return{
        "indicator": domain,
        "type": "domain",
        "total_risk_score": risk_score,
        "signals": signals
    }

if __name__ == "__main__":
    print(scan_domain("bookviewmain24.com"))
