from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

_VT_BASE = "https://www.virustotal.com/api/v3"


def _malicious_to_severity(malicious: int) -> Severity:
    if malicious > 10:
        return Severity.critical
    if malicious > 5:
        return Severity.high
    if malicious > 0:
        return Severity.medium
    return Severity.info


class VirusTotalPlugin(EnrichmentPlugin):
    name = "virustotal"
    supported_ioc_types: set[IOCType] = {
        IOCType.ipv4,
        IOCType.ipv6,
        IOCType.domain,
        IOCType.hash_md5,
        IOCType.hash_sha1,
        IOCType.hash_sha256,
        IOCType.url,
    }
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"x-apikey": self._api_key}

    async def _get_analysis(self, client: httpx.AsyncClient, url: str) -> dict | None:
        try:
            response = await client.get(url, headers=self._headers(), timeout=15.0)
        except httpx.RequestError:
            return None
        if response.status_code != 200:
            return None
        result: dict = response.json()
        return result

    async def _submit_url(self, ioc: IOC, client: httpx.AsyncClient) -> dict | None:
        """Submit a URL for scanning, then retrieve its analysis."""
        try:
            submit = await client.post(
                f"{_VT_BASE}/urls",
                headers=self._headers(),
                data={"url": ioc.value},
                timeout=15.0,
            )
        except httpx.RequestError:
            return None

        if submit.status_code not in (200, 201):
            return None

        submit_data: dict = submit.json()
        analysis_id: str | None = submit_data.get("data", {}).get("id")
        if not analysis_id:
            return None

        # VT free tier: 4 req/min — brief pause before polling
        await asyncio.sleep(0.5)

        analysis_url = f"{_VT_BASE}/analyses/{analysis_id}"
        return await self._get_analysis(client, analysis_url)

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query VirusTotal for malicious detections and reputation."""
        data: dict | None = None

        if ioc.type in (IOCType.ipv4, IOCType.ipv6):
            data = await self._get_analysis(client, f"{_VT_BASE}/ip_addresses/{ioc.value}")
        elif ioc.type == IOCType.domain:
            data = await self._get_analysis(client, f"{_VT_BASE}/domains/{ioc.value}")
        elif ioc.type in (IOCType.hash_md5, IOCType.hash_sha1, IOCType.hash_sha256):
            data = await self._get_analysis(client, f"{_VT_BASE}/files/{ioc.value}")
        elif ioc.type == IOCType.url:
            data = await self._submit_url(ioc, client)

        if data is None:
            return None

        # For direct lookups the stats are under data.attributes.last_analysis_stats
        # For analysis results they are under data.attributes.stats
        attributes: dict = data.get("data", {}).get("attributes", {})
        stats: dict = attributes.get("last_analysis_stats") or attributes.get("stats") or {}

        malicious: int = stats.get("malicious", 0)
        undetected: int = stats.get("undetected", 0)
        total: int = malicious + undetected + stats.get("harmless", 0) + stats.get("suspicious", 0)
        reputation: int = attributes.get("reputation", 0)

        summary = f"{malicious}/{total} detections | Reputation: {reputation}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_malicious_to_severity(malicious),
            summary=summary,
            raw_data={"stats": stats, "reputation": reputation},
            enriched_at=datetime.now(tz=timezone.utc),
        )
