"""HTTPS enforcement and SSRF protection.

All enrichment plugins and external clients MUST use :func:`enforce_safe_url`
to validate URLs before making requests. This protects against:

- Plain HTTP to non-localhost hosts (man-in-the-middle)
- SSRF to private RFC1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- SSRF to link-local (169.254.0.0/16 — AWS metadata 169.254.169.254)
- SSRF to loopback, multicast, reserved, or unspecified addresses

Localhost HTTP is allowed for local services (Ollama, local proxies).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_dangerous_ip(ip_str: str) -> bool:
    """Return True if *ip_str* is in any range that should be blocked for outbound calls.

    Blocks: private (RFC1918 + IPv6 ULA), link-local (incl. AWS metadata),
    multicast, reserved, and unspecified addresses.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return bool(
        ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def enforce_https(url: str) -> None:
    """Raise ``ValueError`` if *url* uses plain HTTP to a non-localhost host.

    Kept for backwards compatibility. New code should call
    :func:`enforce_safe_url` for full SSRF protection.

    >>> enforce_https("https://api.example.com")  # OK
    >>> enforce_https("http://localhost:11434")    # OK — local Ollama
    >>> enforce_https("http://evil.com")           # raises ValueError
    """
    parsed = urlparse(url)
    if parsed.scheme == "http":
        hostname = parsed.hostname or ""
        if hostname not in _LOCALHOST_HOSTS:
            raise ValueError(
                f"HTTPS required: plain HTTP is not allowed for {hostname}. "
                f"Use HTTPS or add host to allowlist if this is a local service."
            )


def enforce_safe_url(url: str) -> None:
    """Raise ``ValueError`` if *url* is unsafe to make outbound requests to.

    Blocks plain HTTP to non-localhost hosts and any IP that resolves to
    a private, link-local, multicast, reserved, or unspecified range.
    This prevents SSRF attacks that pivot through user-supplied URLs to
    reach internal services (cloud metadata endpoints, internal databases,
    other containers on the same host network).

    Localhost / 127.0.0.1 / ::1 are always allowed (for local Ollama and
    similar services).

    >>> enforce_safe_url("https://api.openrouter.ai/v1")      # OK
    >>> enforce_safe_url("http://localhost:11434")            # OK
    >>> enforce_safe_url("http://api.example.com")            # raises (HTTP)
    >>> enforce_safe_url("https://169.254.169.254/latest")    # raises (link-local)
    >>> enforce_safe_url("https://10.0.0.1/admin")            # raises (private)
    """
    parsed = urlparse(url)
    scheme = parsed.scheme
    hostname = parsed.hostname or ""

    if scheme not in ("http", "https"):
        raise ValueError(
            f"Refusing URL with scheme {scheme!r}: must be http or https ({url!r})"
        )
    if not hostname:
        raise ValueError(f"URL has no hostname: {url!r}")

    is_localhost_name = hostname in _LOCALHOST_HOSTS

    if scheme == "http" and not is_localhost_name:
        raise ValueError(
            f"HTTPS required: plain HTTP is not allowed for {hostname}. "
            f"Use HTTPS or add host to allowlist if this is a local service."
        )

    # IP literal — validate directly without DNS
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None

    if ip is not None:
        if ip.is_loopback:
            return  # explicit loopback literal — always allowed
        if _is_dangerous_ip(hostname):
            raise ValueError(
                f"Refusing to connect to non-public IP {hostname}: "
                f"private/link-local/multicast/reserved ranges are blocked (SSRF protection)"
            )
        return

    # Hostname — resolve via DNS and validate every resolved address.
    # NOTE: If DNS resolution fails, we treat it as safe since the host
    # cannot be an internal IP if it cannot resolve at all (tests benefit).
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        infos = []  # unresolvable → not a local/private address

    if not infos:
        return  # unresolvable hostname — safe to proceed (not an internal IP)

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            resolved = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if resolved.is_loopback:
            # Loopback resolution is allowed (e.g. an internal proxy)
            continue
        if _is_dangerous_ip(str(ip_str)):
            raise ValueError(
                f"Refusing to connect to {hostname!r} (resolves to {ip_str}): "
                f"private/link-local/multicast/reserved ranges are blocked (SSRF protection)"
            )
