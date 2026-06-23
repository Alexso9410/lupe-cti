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


# ---------------------------------------------------------------------------
# PII header redaction (CRITICAL #2)
# ---------------------------------------------------------------------------
#
# Email headers contain PII that must NOT be sent to LLM providers
# (OpenAI / Anthropic / OpenRouter / Ollama) verbatim. This map defines
# which header names map to which placeholder token.
#
# Intentionally KEPT (allowed to reach the LLM):
#   - Subject, Date, Content-Type
#   - Received (needed for hop chain analysis)
#   - Authentication-Results (SPF / DKIM / DMARC verdict + domain)
#
# REDACTED to a typed token:
#   - [REDACTED_EMAIL] — From, To, Cc, Bcc, Reply-To, Return-Path, Sender
#   - [REDACTED_IP]    — X-Forwarded-For, X-Originating-IP, X-Real-IP,
#                        X-Client-IP, X-Client-IP, Client-IP
#   - [REDACTED_HEADER] — Message-ID, In-Reply-To, References,
#                         DKIM-Signature, ARC-Authentication-Results,
#                         ARC-Message-Signature, ARC-Seal
# ---------------------------------------------------------------------------

_EMAIL_HEADERS: frozenset[str] = frozenset(
    {
        "from",
        "to",
        "cc",
        "bcc",
        "reply-to",
        "return-path",
        "sender",
    }
)

_IP_HEADERS: frozenset[str] = frozenset(
    {
        "x-forwarded-for",
        "x-originating-ip",
        "x-real-ip",
        "x-client-ip",
        "client-ip",
    }
)

# Headers that leak routing / crypto state. Whole header is opaque to the
# forensic analyst when sent to an LLM.
_OTHER_SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        "message-id",
        "in-reply-to",
        "references",
        "dkim-signature",
        "arc-authentication-results",
        "arc-message-signature",
        "arc-seal",
    }
)

# Headers that are ARC-* but not in the explicit set above (future-proof).
_ARC_PREFIX = "arc-"

_REDACT_EMAIL = "[REDACTED_EMAIL]"
_REDACT_IP = "[REDACTED_IP]"
_REDACT_HEADER = "[REDACTED_HEADER]"


def redact_pii_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with PII values replaced by typed tokens.

    The original dict is not mutated. Header name matching is
    case-insensitive but the original casing of kept headers is preserved
    in the returned dict.

    >>> redact_pii_headers({"From": "a@b.com", "Subject": "Hi"})
    {'From': '[REDACTED_EMAIL]', 'Subject': 'Hi'}
    >>> redact_pii_headers({"X-Forwarded-For": "1.2.3.4"})
    {'X-Forwarded-For': '[REDACTED_IP]'}
    >>> redact_pii_headers({})
    {}
    """
    if not headers:
        return dict(headers) if headers else {}

    redacted: dict[str, str] = {}
    for name, value in headers.items():
        lower = name.lower()
        if lower in _EMAIL_HEADERS:
            redacted[name] = _REDACT_EMAIL
        elif lower in _IP_HEADERS:
            redacted[name] = _REDACT_IP
        elif lower in _OTHER_SENSITIVE_HEADERS or lower.startswith(_ARC_PREFIX):
            redacted[name] = _REDACT_HEADER
        else:
            redacted[name] = value
    return redacted
