"""HTTPS enforcement — reject plain HTTP except for localhost.

All enrichment plugins MUST use this to validate URLs before making
requests. Localhost HTTP is allowed for Ollama and local services.
"""

from __future__ import annotations

from urllib.parse import urlparse

_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


def enforce_https(url: str) -> None:
    """Raise ``ValueError`` if *url* uses plain HTTP to a non-localhost host.

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
