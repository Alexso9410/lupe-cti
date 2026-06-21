"""Blocklist.de plugin — IP reputation from blocklist.de lists.

Free, no API key required.
API: https://lists.blocklist.de/lists/
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

logger = logging.getLogger(__name__)

_LISTS = [
    "bruteforcelogin",
    "bruteforceattacks",
    "ircbot",
    "ssh",
    "mail",
    "apache",
    "imap",
    "ftp",
    "sip",
    "voip",
]


class BlocklistDePlugin(EnrichmentPlugin):
    """Blocklist.de — IP reputation check against multiple blacklists."""

    name = "blocklist-de"
    supported_ioc_types = {IOCType.ipv4, IOCType.ipv6}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Check if IP appears in any blocklist.de lists."""
        url = f"https://api.blocklist.de/api.php?ip={ioc.value}&start=1"

        try:
            response = await client.get(url, timeout=15.0)
        except httpx.RequestError:
            logger.debug("blocklist.de request failed for %s", ioc.value)
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        # Empty response or "attacks" key with 0 = clean
        if not data or (isinstance(data, dict) and data.get("attacks", 0) == 0):
            return None

        # Parse the response
        attacks = 0
        categories = []
        if isinstance(data, dict):
            attacks = data.get("attacks", 0)
            if "blacklists" in data:
                categories = (
                    list(data["blacklists"].keys()) if isinstance(data["blacklists"], dict) else []
                )

        if attacks == 0:
            return None

        severity = (
            Severity.high if attacks > 100 else Severity.medium if attacks > 10 else Severity.low
        )

        return EnrichmentResult(
            source="blocklist.de",
            ioc_value=ioc.value,
            severity=severity,
            summary=f"Listed in {len(categories)} blocklist(s), {attacks} attack(s) reported",
            raw_data=data if isinstance(data, dict) else {"attacks": attacks},
            enriched_at=datetime.now(),
        )
