from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
import whois

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

logger = logging.getLogger(__name__)


def _coerce_date(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0]
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _run_whois(ioc_value: str) -> dict:
    import os
    import sys

    # python-whois prints transient socket errors directly to stderr (not via
    # exceptions). Suppress that noise while the lookup runs; a failed lookup
    # still returns an all-None dict, which the caller handles.
    saved_stderr_fd = os.dup(2) if sys.platform == "win32" else None
    try:
        if sys.platform == "win32":
            devnull_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull_fd, 2)
            w = whois.whois(ioc_value)
            assert saved_stderr_fd is not None
            os.dup2(saved_stderr_fd, 2)
            os.close(devnull_fd)
        else:
            w = whois.whois(ioc_value)
    finally:
        if saved_stderr_fd is not None:
            try:
                os.dup2(saved_stderr_fd, 2)
                os.close(saved_stderr_fd)
            except OSError:
                pass

    return {
        "registrar": w.registrar,
        "creation_date": _coerce_date(w.creation_date),
        "expiration_date": _coerce_date(w.expiration_date),
        "name_servers": _coerce_list(w.name_servers),
        "org": w.org,
    }


class WhoisPlugin(EnrichmentPlugin):
    name = "whois"
    supported_ioc_types: set[IOCType] = {IOCType.domain, IOCType.ipv4}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Run WHOIS lookup for a domain or IPv4 address."""
        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(None, _run_whois, ioc.value)
        except Exception:
            return None

        if not any(raw.values()):
            logger.debug("whois returned empty for %s", ioc.value)
            return None

        parts: list[str] = []
        if raw.get("registrar"):
            parts.append(f"Registrar: {raw['registrar']}")
        if raw.get("creation_date"):
            parts.append(f"Created: {raw['creation_date']}")
        if raw.get("expiration_date"):
            parts.append(f"Expires: {raw['expiration_date']}")
        if raw.get("org"):
            parts.append(f"Org: {raw['org']}")

        summary = " | ".join(parts) if parts else "WHOIS data retrieved"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=Severity.info,
            summary=summary,
            raw_data=raw,
            enriched_at=datetime.now(tz=timezone.utc),
        )
