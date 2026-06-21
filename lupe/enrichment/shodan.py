from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity

_SHODAN_URL = "https://api.shodan.io/shodan/host/{ip}"


def _host_to_severity(ports: list[int], vulns: list[str]) -> Severity:
    if vulns:
        return Severity.high
    if len(ports) > 10:
        return Severity.medium
    return Severity.info


class ShodanPlugin(EnrichmentPlugin):
    name = "shodan"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query Shodan for open ports, vulnerabilities, and host metadata."""
        url = _SHODAN_URL.format(ip=ioc.value)
        try:
            response = await client.get(
                url, params={"key": self._api_key}, timeout=15.0
            )
        except httpx.RequestError:
            return None

        if response.status_code == 404:
            # Host not indexed by Shodan — not an error, just no data
            return None

        if response.status_code != 200:
            return None

        data: dict = response.json()

        ports: list[int] = data.get("ports", [])
        vulns: list[str] = list(data.get("vulns", {}).keys())
        os_name: str = data.get("os", "") or "unknown"
        org: str = data.get("org", "") or "N/A"
        isp: str = data.get("isp", "") or "N/A"
        country: str = data.get("country_code", "N/A")

        ports_str = ", ".join(str(p) for p in sorted(ports)) if ports else "none"
        vuln_count = len(vulns)

        parts: list[str] = [
            f"Ports: {ports_str}",
            f"OS: {os_name}",
            f"Org: {org}",
            f"Vulns: {vuln_count}",
        ]

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_host_to_severity(ports, vulns),
            summary=" | ".join(parts),
            raw_data={
                "ports": ports,
                "vulns": vulns,
                "os": os_name,
                "org": org,
                "isp": isp,
                "country_code": country,
                "last_update": data.get("last_update"),
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
