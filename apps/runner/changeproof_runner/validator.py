import ipaddress
import socket
from urllib.parse import urlparse


class TargetSecurityError(ValueError):
    """Raised when an HTTP target violates security boundaries."""

    pass


def is_private_or_local_host(hostname: str) -> bool:
    if not hostname:
        return False
    lower = hostname.lower()
    if lower in ("localhost", "127.0.0.1", "::1") or lower.endswith(".internal") or lower.endswith(".local"):
        return True

    # Check if direct IP address
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback
    except ValueError:
        pass

    # Resolve DNS to check if it points to a private network
    try:
        resolved_ips = socket.gethostbyname_ex(hostname)[2]
        for rip in resolved_ips:
            ip = ipaddress.ip_address(rip)
            if not (ip.is_private or ip.is_loopback):
                return False
        return True
    except Exception:
        # If unable to resolve safely, refuse
        return False


def validate_target_url(target_url: str) -> str:
    """Validate that the target URL is strictly within local/private dev boundaries."""
    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https"):
        raise TargetSecurityError(
            f"Invalid target URL scheme '{parsed.scheme}': only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise TargetSecurityError(f"Target URL '{target_url}' missing hostname.")

    if not is_private_or_local_host(hostname):
        raise TargetSecurityError(
            f"Target '{hostname}' is not a local or private environment. "
            "ChangeProof Runner strictly refuses public domains/IPs to prevent misuse as a DDoS tool."
        )

    return target_url.rstrip("/")
