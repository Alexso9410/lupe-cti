"""Censys plugin — IP, domain, and certificate search.

Freemium, requires two keys: LUPE_CENSYS_ID + LUPE_CENSYS_SECRET
API: https://search.censys.io/api/v2/
Uses HTTP Basic auth (id:secret).
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

logger = logging.getLogger(__name__)


class CensysPlugin(EnrichmentPlugin):
    """Censys — host and certificate intelligence."""

    name = "censys"
    supported_ioc_types = {IOCType.ipv4, IOCType.ipv6, IOCType.domain}
    requires_api_key = True

    def __init__(self, censys_id: str = "", censys_secret: str = "") -> None:
        self._censys_id = censys_id
        self._censys_secret = censys_secret

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query Censys for host or certificate data."""
        if not self._censys_id or not self._censys_secret:
            return None

        auth = (self._censys_id, self._censys_secret)

        if ioc.type in (IOCType.ipv4, IOCType.ipv6):
            url = f"https://search.censys.io/api/v2/hosts/{ioc.value}"
        elif ioc.type == IOCType.domain:
            url = f"https://search.censys.io/api/v2/hosts/search?q={ioc.value}"
        else:
            return None

        try:
            response = await client.get(url, auth=auth, timeout=15.0)
        except httpx.RequestError:
            logger.debug("Censys request failed for %s", ioc.value)
            return None

        if response.status_code == 401:
            logger.warning("Censys auth failed — check LUPE_CENSYS_ID and LUPE_CENSYS_SECRET")
            return None

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        result = data.get("result", data)

        # For IP lookups
        if ioc.type in (IOCType.ipv4, IOCType.ipv6):
            services = result.get("services", [])
            operating_system = result.get("operating_system", {})
            autonomous_system = result.get("autonomous_system", {})
            last_updated = result.get("last_updated_at", "")

            service_names = [s.get("service_name", "") for s in services]
            open_ports = [s.get("port", 0) for s in services]

            return EnrichmentResult(
                source="censys",
                ioc_value=ioc.value,
                severity=Severity.info,
                summary=(
                    f"{len(services)} service(s), "
                    f"OS: {operating_system.get('product', 'unknown')}, "
                    f"AS: {autonomous_system.get('asn', 'unknown')}"
                ),
                raw_data={
                    "services": service_names[:20],
                    "open_ports": open_ports[:20],
                    "os": operating_system,
                    "autonomous_system": autonomous_system,
                    "last_updated": last_updated,
                },
                enriched_at=datetime.now(),
            )

        # For domain searches
        hits = result.get("hits", [])
        total = result.get("total", 0)

        return EnrichmentResult(
            source="censys",
            ioc_value=ioc.value,
            severity=Severity.info,
            summary=f"{total} host(s) found matching domain",
            raw_data={"total": total, "hits": hits[:10]},
            enriched_at=datetime.now(),
        )
