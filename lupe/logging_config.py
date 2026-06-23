"""Centralized logging setup for Lupe CTI.

Adds a stdout :class:`logging.StreamHandler` and installs
:class:`SecretRedactingFilter` so that API keys and tokens never leak
to logs / stderr.

Idempotent: calling :func:`setup_logging` more than once replaces
existing handlers on the root ``lupe`` logger without duplicating output.
"""

from __future__ import annotations

import logging
import sys

from lupe.security.redact import redact_secrets

_LOGGER_NAME = "lupe"
_INITIALIZED = False


class SecretRedactingFilter(logging.Filter):
    """Logging filter that runs :func:`redact_secrets` over every log record.

    Applied to a handler (not the root logger) so we only redact once,
    even if a record propagates up the hierarchy.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            if msg:
                redacted = redact_secrets(msg)
                if redacted != msg:
                    record.msg = redacted
                    record.args = ()
        except Exception:
            # Never let the redaction filter break logging
            pass
        return True


def setup_logging(level: str | int = "INFO") -> logging.Logger:
    """Configure the ``lupe`` logger with stdout + secret redaction.

    Args:
        level: Log level name (e.g. ``"INFO"``, ``"DEBUG"``) or numeric
            level. Defaults to ``"INFO"``.

    Returns:
        The configured ``lupe`` logger.
    """
    global _INITIALIZED

    if isinstance(level, str):
        level_value = logging.getLevelName(level.upper())
        if not isinstance(level_value, int):
            level_value = logging.INFO
    else:
        level_value = level

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level_value)
    logger.propagate = False  # avoid duplicate output via root

    # Remove handlers we previously added (idempotency across reloads)
    for h in list(logger.handlers):
        if getattr(h, "_lupe_owned", False):
            logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level_value)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    handler.addFilter(SecretRedactingFilter())
    handler._lupe_owned = True  # type: ignore[attr-defined]
    logger.addHandler(handler)

    _INITIALIZED = True
    return logger


def is_logging_configured() -> bool:
    """Return True if :func:`setup_logging` has been called."""
    return _INITIALIZED
