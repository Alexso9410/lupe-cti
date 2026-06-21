"""Secret redaction for log output and display.

Replaces sensitive values (API keys, tokens, passwords) with *** to prevent
credential leakage in logs, tracebacks, and CLI output.
"""
from __future__ import annotations

import re

# Patterns that look like secrets. Each is (compiled_regex, replacement).
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # sk-... keys (OpenAI style)
    (re.compile(r"(sk-[a-zA-Z0-9\-_]{8,})"), "***"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)([a-zA-Z0-9\-_\.]{8,})"), r"\1***"),
    # key=... or secret=... or password=... in query strings / logs
    (
        re.compile(
            r"((?:api_?key|secret|password|token)=(?:[a-zA-Z0-9\-_]{8,}))",
            re.IGNORECASE,
        ),
        "***",
    ),
    # Authorization header values
    (re.compile(r"(Authorization:\s*)([a-zA-Z0-9\-_\.]{8,})", re.IGNORECASE), r"\1***"),
]


def redact_secrets(text: str) -> str:
    """Replace sensitive values in *text* with ``***``.

    >>> redact_secrets("key=sk-abc123def456")
    'key=***'
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
