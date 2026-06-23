"""Compatibility imports for stdlib modules backported to older Python versions."""

from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]  # noqa: F401 — used in Python 3.10 CI
