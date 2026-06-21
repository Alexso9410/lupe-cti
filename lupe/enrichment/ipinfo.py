from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity

_IPINFO_URL = "https://ipinfo.io/{ip}/json"


class IpInfoPlugin(EnrichmentPlugin):
    name = "ipinfo"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4, IOCType.ipv6}
    requires_api_key = False

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Fetch geolocation and ASN data from ipinfo.io."""
        url = _IPINFO_URL.format(ip=ioc.value)
        try:
            response = await client.get(url, timeout=10.0)
        except httpx.RequestError:
            return None

        if response.status_code == 429:
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="ipinfo.io rate limit reached — try again later",
                raw_data={"error": "rate_limited"},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        if response.status_code != 200:
            return None

        data: dict = response.json()

        parts: list[str] = []
        if country := data.get("country"):
            parts.append(f"Country: {country}")
        if city := data.get("city"):
            parts.append(f"City: {city}")
        if org := data.get("org"):
            parts.append(f"Org: {org}")
        if hostname := data.get("hostname"):
            parts.append(f"Hostname: {hostname}")

        summary = " | ".join(parts) if parts else "No geolocation data returned"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=Severity.info,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )
