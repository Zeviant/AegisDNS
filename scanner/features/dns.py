import dns.resolver

# --- TTL + A/AAAA RECORDS ---
def fetch_dns(domain: str) -> dict[str, list]:

    data = {
        "A": [],
        "AAAA": []
    }

    resolver = dns.resolver.Resolver()

    try:
        data["A"] = resolver.resolve(domain, "A")
    except Exception:
        pass

    try:
        data["AAAA"] = resolver.resolve(domain, "AAAA")
    except Exception:
        pass

    return data

def extract_A_AAAA_metrics(dns_data : dict) -> dict[str, int | None] | None:
    records = []
    ttls = []

    for record_type in ("A", "AAAA"):
        answers = dns_data.get(record_type, [])
        for r in answers:
            records.append(str(r))
            ttls.append(answers.rrset.ttl)
    
    if not records:
        return None
    
    return {
        "record_count": len(records),
        "min_ttl": min(ttls) if ttls else None
    }


# --- NS RECORDS ---
def extract_ns_records(domain: str) -> list[str] | None:
    try:
        answers = dns.resolver.resolve(domain, "NS")
        return sorted({
            str(rdata.target).rstrip(".").lower()
            for rdata in answers
        })
    except Exception:
        return None

KNOWN_DNS_PROVIDERS = {
    "cloudflare": ["cloudflare.com"],
    "aws_route53": ["awsdns"],
    "google": ["googledomains.com", "google.com"],
    "azure": ["azure-dns"],
    "verisign": ["verisign"],
    "godaddy": ["domaincontrol.com"],
}

SUSPICIOUS_DNS_PROVIDERS = [
    "freedns",
    "afraid.org",
    "duckdns",
    "no-ip",
    "dynu",
]

def classify_ns_provider(ns_records: list[str]) -> str:
    joined = " ".join(ns_records)

    for provider, patterns in KNOWN_DNS_PROVIDERS.items():
        for p in patterns:
            if p in joined:
                return provider

    for suspicious in SUSPICIOUS_DNS_PROVIDERS:
        if suspicious in joined:
            return "suspicious_free_dns"

    return "unknown"

# --- MAIL CONFIGURATION ---
def extract_mx_records(domain: str) -> list[str] | None:
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return sorted(
            str(r.exchange).rstrip(".").lower()
            for r in answers
        )
    except Exception:
        return None


def extract_txt_records(domain: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, "TXT")
        return [
            "".join(part.decode() if isinstance(part, bytes) else part)
            for r in answers
            for part in r.strings
        ]
    except Exception:
        return []
    
def has_spf(txt_records: list[str]) -> bool:
    return any(
        r.lower().startswith("v=spf1")
        for r in txt_records
    )

def has_dmarc(domain: str) -> bool:
    try:
        dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
        return True
    except Exception:
        return False
    