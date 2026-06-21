from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import whois

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity


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
    w = whois.whois(ioc_value)
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

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Run WHOIS lookup for a domain or IPv4 address."""
        loop = asyncio.get_event_loop()
        try:
            raw = await loop.run_in_executor(None, _run_whois, ioc.value)
        except Exception:
            return None

        if not any(raw.values()):
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
