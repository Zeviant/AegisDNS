from bs4 import BeautifulSoup
from urllib.parse import urlparse
import tldextract
import requests

def fetch_web_page(url: str):
    try:
        return requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
    except Exception:
        return None

LOGIN_KEYWORDS = [
    "login", "sign in", "signin", "verify", "account",
    "password", "secure", "update", "authenticate"
]

BRAND_KEYWORDS = [
    "paypal", "google", "apple", "microsoft",
    "facebook", "amazon", "bank", "crypto", "wallet"
]

def get_registrable_domain(hostname: str | None) -> str | None:
    if not hostname:
        return None
    ext = tldextract.extract(hostname)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}"

def extract_html_credential_features(
    html: str,
    page_url: str
) -> dict | None:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None

    forms = soup.find_all("form")
    if not forms:
        return {
            "has_form": False
        }

    parsed_url = urlparse(page_url)
    page_domain = get_registrable_domain(parsed_url.hostname)

    password_inputs = soup.find_all("input", {"type": "password"})
    text = soup.get_text(" ", strip=True).lower()
    title = (soup.title.string.lower() if soup.title else "")

    login_keywords_found = [
        k for k in LOGIN_KEYWORDS if k in text or k in title
    ]

    brand_keywords_found = [
        b for b in BRAND_KEYWORDS if b in text or b in title
    ]

    external_form_actions = 0

    for form in forms:
        action = form.get("action")
        if not action:
            continue

        action_host = urlparse(action).hostname
        action_domain = get_registrable_domain(action_host)

        if action_domain and page_domain and action_domain != page_domain:
            external_form_actions += 1

    return {
        "has_form": True,
        "password_input_count": len(password_inputs),
        "login_keywords": login_keywords_found,
        "brand_keywords": brand_keywords_found,
        "external_form_actions": external_form_actions,
        "form_count": len(forms)
    }
