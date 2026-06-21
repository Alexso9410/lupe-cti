"""crt.sh plugin — Certificate Transparency logs for domains.

Free, no API key required.
API: https://crt.sh/?q=<domain>&output=json
"""

from __future__ import annotations

import logging

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity
from datetime import datetime

logger = logging.getLogger(__name__)


class CrtShPlugin(EnrichmentPlugin):
    """crt.sh — Certificate Transparency log search for domain subdomains."""

    name = "crt.sh"
    supported_ioc_types = {IOCType.domain}
    requires_api_key = False

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Search crt.sh for certificates issued to the domain."""
        if not self.supports(ioc.type):
            return None

        url = f"https://crt.sh/?q={ioc.value}&output=json"

        try:
            response = await client.get(url, timeout=30.0)
        except httpx.RequestError:
            logger.debug("crt.sh request failed for %s", ioc.value)
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        if not data or not isinstance(data, list):
            return None

        # Extract unique subdomains from certificate entries
        subdomains: set[str] = set()
        issuers: set[str] = set()
        for entry in data:
            name = entry.get("name_value", "")
            for line in name.split("\n"):
                line = line.strip().lower()
                if line and "*" not in line:
                    subdomains.add(line)
            issuer = entry.get("issuer_name", "")
            if issuer:
                issuers.add(issuer)

        cert_count = len(data)
        subdomain_count = len(subdomains)

        if cert_count == 0:
            return None

        severity = (
            Severity.info  # CT logs are informational
        )

        return EnrichmentResult(
            source="crt.sh",
            ioc_value=ioc.value,
            severity=severity,
            summary=f"{cert_count} certificate(s) found, {subdomain_count} unique subdomain(s)",
            raw_data={
                "certificate_count": cert_count,
                "subdomains": sorted(subdomains)[:50],  # Cap for display
                "issuers": sorted(issuers)[:10],
            },
            enriched_at=datetime.now(),
        )
