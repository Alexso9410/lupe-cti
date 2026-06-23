from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

_OTX_BASE = "https://otx.alienvault.com/api/v1/indicators"

_IOC_TYPE_PATH: dict[IOCType, str] = {
    IOCType.ipv4: "IPv4",
    IOCType.domain: "domain",
    IOCType.hash_md5: "file",
    IOCType.hash_sha1: "file",
    IOCType.hash_sha256: "file",
}


def _pulses_to_severity(pulse_count: int) -> Severity:
    if pulse_count > 10:
        return Severity.critical
    if pulse_count > 5:
        return Severity.high
    if pulse_count > 0:
        return Severity.medium
    return Severity.info


class OTXPlugin(EnrichmentPlugin):
    name = "otx"
    supported_ioc_types: set[IOCType] = {
        IOCType.ipv4,
        IOCType.domain,
        IOCType.hash_md5,
        IOCType.hash_sha1,
        IOCType.hash_sha256,
    }
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query AlienVault OTX for threat pulse intelligence."""
        path = _IOC_TYPE_PATH.get(ioc.type)
        if path is None:
            return None

        url = f"{_OTX_BASE}/{path}/{ioc.value}/general"
        headers = {"X-OTX-API-KEY": self._api_key}

        try:
            response = await client.get(url, headers=headers, timeout=15.0)
        except httpx.RequestError:
            return None

        if response.status_code != 200:
            return None

        data: dict = response.json()

        pulse_info: dict = data.get("pulse_info", {})
        pulse_count: int = pulse_info.get("count", 0)
        tags: list[str] = pulse_info.get("tags", []) or []
        country: str = data.get("country_code", "") or ""
        validation: list[dict] = data.get("validation", []) or []
        validation_names = [v.get("name", "") for v in validation if v.get("name")]

        parts: list[str] = [f"Pulses: {pulse_count}"]
        if tags:
            parts.append(f"Tags: {', '.join(tags[:5])}")
        if country:
            parts.append(f"Country: {country}")
        if validation_names:
            parts.append(f"Validated by: {', '.join(validation_names[:3])}")

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_pulses_to_severity(pulse_count),
            summary=" | ".join(parts),
            raw_data={
                "pulse_count": pulse_count,
                "tags": tags,
                "country": country,
                "validation": validation,
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
