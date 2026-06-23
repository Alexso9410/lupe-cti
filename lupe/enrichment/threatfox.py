from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

_THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"


class ThreatFoxPlugin(EnrichmentPlugin):
    name = "threatfox"
    supported_ioc_types: set[IOCType] = {
        IOCType.ipv4,
        IOCType.domain,
        IOCType.hash_md5,
        IOCType.hash_sha256,
        IOCType.url,
    }
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query ThreatFox for known malicious IOCs."""
        payload = {"query": "search_ioc", "search_term": ioc.value}
        try:
            response = await client.post(_THREATFOX_URL, json=payload, timeout=15.0)
        except httpx.RequestError:
            return None

        if response.status_code != 200:
            return None

        data: dict = response.json()

        if data.get("query_status") != "ok":
            return None

        iocs: list[dict] = data.get("data", []) or []
        if not iocs:
            return None

        first = iocs[0]
        malware = first.get("malware_printable", "unknown malware")
        threat_type = first.get("threat_type", "unknown")
        confidence = first.get("confidence_level", 0)
        tags: list[str] = [t.get("tag", "") for t in (first.get("tags") or [])]

        parts: list[str] = [
            f"Malware: {malware}",
            f"Threat type: {threat_type}",
            f"Confidence: {confidence}%",
        ]
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=Severity.critical,
            summary=" | ".join(parts),
            raw_data={"matches": iocs, "total": len(iocs)},
            enriched_at=datetime.now(tz=timezone.utc),
        )
