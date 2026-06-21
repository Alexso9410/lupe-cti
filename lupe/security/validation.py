"""IOC input validation — length and format guards."""
from __future__ import annotations

# Maximum lengths per IOC type. Exceeding these is always invalid.
_MAX_LENGTHS: dict[str, int] = {
    "ipv4": 15,
    "ipv6": 45,
    "domain": 253,
    "url": 2048,
    "hash_md5": 32,
    "hash_sha1": 40,
    "hash_sha256": 64,
    "email": 254,
    "phone": 20,
    "username": 64,
}

_ABSOLUTE_MAX = 4096


def validate_ioc_value(value: str, *, ioc_type: str) -> None:
    """Validate an IOC value for length constraints.

    Raises ``ValueError`` if the value is empty or exceeds the maximum
    length for the given *ioc_type*.
    """
    if not value:
        raise ValueError("IOC value must not be empty")

    if len(value) > _ABSOLUTE_MAX:
        raise ValueError(
            f"IOC value too long: {len(value)} chars exceeds absolute max {_ABSOLUTE_MAX}"
        )

    max_len = _MAX_LENGTHS.get(ioc_type)
    if max_len and len(value) > max_len:
        raise ValueError(
            f"IOC value too long for {ioc_type}: {len(value)} chars exceeds max {max_len}"
        )
