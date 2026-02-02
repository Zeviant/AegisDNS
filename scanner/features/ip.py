import ipaddress
from urllib.parse import urlparse

def classify_ip(ip: str) -> tuple[bool, str]:
    ip_obj = ipaddress.ip_address(ip)

    if ip_obj.is_private:
        return True, "Private IP address"
    if ip_obj.is_loopback:
        return True, "Loopback IP address"
    if ip_obj.is_link_local:
        return True, "Link-local IP address"
    if ip_obj.is_multicast or ip_obj.is_reserved:
        return True, "Reserved or multicast IP address"

    return False, "Public routable IP address"

def has_nonstandard_port(url: str) -> tuple[bool, int | None]:
    parsed = urlparse(url)
    port = parsed.port

    if port and port not in (80, 443):
        return True, port

    return False, port
