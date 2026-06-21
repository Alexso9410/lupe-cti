from __future__ import annotations

import re

from lupe.models import IOC, IOCType

_RE_HASH_MD5 = re.compile(r"^[0-9a-fA-F]{32}$")
_RE_HASH_SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")
_RE_HASH_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_RE_URL = re.compile(r"^https?://", re.IGNORECASE)
_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_RE_PHONE = re.compile(r"^\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?[\s\-.]?\d{3,5}[\s\-.]?\d{4,7}$")
_RE_DOMAIN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}$"
)
_RE_IPV4_LOOSE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_RE_IPV6 = re.compile(
    r"^("
    r"([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
    r"|([0-9a-fA-F]{1,4}:){1,7}:"
    r"|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"
    r"|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}"
    r"|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}"
    r"|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}"
    r"|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}"
    r"|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})"
    r"|:((:[0-9a-fA-F]{1,4}){1,7}|:)"
    r"|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+"
    r"|::(ffff(:0{1,4})?:)?(25[0-5]|(2[0-4]|1?[0-9])?[0-9])"
    r"(\.(25[0-5]|(2[0-4]|1?[0-9])?[0-9])){3}"
    r"|([0-9a-fA-F]{1,4}:){1,4}:(25[0-5]|(2[0-4]|1?[0-9])?[0-9])"
    r"(\.(25[0-5]|(2[0-4]|1?[0-9])?[0-9])){3}"
    r")$"
)


def _is_valid_ipv4(value: str) -> bool:
    m = _RE_IPV4_LOOSE.match(value)
    if not m:
        return False
    return all(0 <= int(m.group(i)) <= 255 for i in range(1, 5))


def detect_ioc(value: str) -> IOC | None:
    """Detect the IOC type of a string value using regex heuristics."""
    value = value.strip()

    # Hashes must be checked before domains and IPs because hex strings
    # could otherwise be misidentified.
    if _RE_HASH_SHA256.match(value):
        return IOC(type=IOCType.hash_sha256, value=value)

    if _RE_HASH_SHA1.match(value):
        return IOC(type=IOCType.hash_sha1, value=value)

    if _RE_HASH_MD5.match(value):
        return IOC(type=IOCType.hash_md5, value=value)

    # URL before domain so "https://evil.com/path" is not parsed as domain.
    if _RE_URL.match(value):
        return IOC(type=IOCType.url, value=value)

    # Email before domain — "user@evil.com" contains a dot like a domain.
    if _RE_EMAIL.match(value):
        return IOC(type=IOCType.email, value=value)

    if _RE_PHONE.match(value):
        return IOC(type=IOCType.phone, value=value)

    # IPv4 before domain — "1.2.3.4" would match the domain regex.
    if _is_valid_ipv4(value):
        return IOC(type=IOCType.ipv4, value=value)

    if _RE_IPV6.match(value):
        return IOC(type=IOCType.ipv6, value=value)

    if _RE_DOMAIN.match(value):
        return IOC(type=IOCType.domain, value=value)

    return None
