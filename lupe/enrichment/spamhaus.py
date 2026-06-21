"""Spamhaus plugin — IP and domain reputation via Spamhaus intel API.

Requires API key: LUPE_SPAMHAUS_KEY
API: https://api.spamhaus.org/api/v2/
"""

from __future__ import annotations

import logging

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity
from datetime import datetime

logger = logging.getLogger(__name__)


class SpamhausPlugin(EnrichmentPlugin):
    """Spamhaus — IP/domain reputation from Spamhaus threat intel."""

    name = "spamhaus"
    supported_ioc_types = {IOCType.ipv4, IOCType.ipv6, IOCType.domain}
    requires_api_key = True

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query Spamhaus for IP or domain reputation."""
        if not self._api_key:
            return None

        headers = {"Authorization": f"Bearer {self._api_key}"}

        # Determine query type
        if ioc.type in (IOCType.ipv4, IOCType.ipv6):
            url = f"https://api.spamhaus.org/api/v2/intel/ipv4/{ioc.value}"
        elif ioc.type == IOCType.domain:
            url = f"https://api.spamhaus.org/api/v2/intel/domain/{ioc.value}"
        else:
            return None

        try:
            response = await client.get(url, headers=headers, timeout=15.0)
        except httpx.RequestError:
            logger.debug("Spamhaus request failed for %s", ioc.value)
            return None

        if response.status_code == 401:
            logger.warning("Spamhaus authentication failed — check LUPE_SPAMHAUS_KEY")
            return None

        if response.status_code == 404:
            # Not found = clean
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        # Extract threat info
        threat_score = data.get("score", 0)
        categories = data.get("categories", [])
        description = data.get("description", "")

        if threat_score == 0 and not categories:
            return None

        severity = (
            Severity.critical if threat_score >= 8
            else Severity.high if threat_score >= 5
            else Severity.medium if threat_score >= 2
            else Severity.low
        )

        summary_parts = []
        if categories:
            summary_parts.append(f"Categories: {', '.join(categories)}")
        if description:
            summary_parts.append(description[:200])

        return EnrichmentResult(
            source="spamhaus",
            ioc_value=ioc.value,
            severity=severity,
            summary="; ".join(summary_parts) or f"Score: {threat_score}",
            raw_data=data,
            enriched_at=datetime.now(),
        )
