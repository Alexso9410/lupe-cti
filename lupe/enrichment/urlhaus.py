from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

_URLHAUS_URL = "https://urlhaus-api.abuse.ch/v1/"


class URLhausPlugin(EnrichmentPlugin):
    name = "urlhaus"
    supported_ioc_types: set[IOCType] = {
        IOCType.url,
        IOCType.domain,
        IOCType.ipv4,
        IOCType.hash_sha256,
    }
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query URLhaus for malware distribution URLs and hosts."""
        try:
            if ioc.type == IOCType.url:
                response = await client.post(
                    f"{_URLHAUS_URL}url/",
                    json={"url": ioc.value},
                    timeout=15.0,
                )
            elif ioc.type in {IOCType.domain, IOCType.ipv4}:
                response = await client.post(
                    f"{_URLHAUS_URL}host/",
                    json={"host": ioc.value},
                    timeout=15.0,
                )
            elif ioc.type == IOCType.hash_sha256:
                response = await client.post(
                    f"{_URLHAUS_URL}payload/",
                    json={"sha256_hash": ioc.value},
                    timeout=15.0,
                )
            else:
                return None
        except httpx.RequestError:
            return None

        if response.status_code != 200:
            return None

        data: dict = response.json()
        query_status = data.get("query_status")

        if query_status == "no_results":
            return None

        if ioc.type == IOCType.url:
            if query_status not in {"is_url", "ok"}:
                return None

            threat = data.get("threat", "unknown")
            url_status = data.get("url_status", "unknown")
            tags: list[str] = data.get("tags", []) or []

            severity = Severity.critical if url_status == "online" else Severity.medium

            summary = f"URLhaus: {threat} — status: {url_status}, tags: {tags}"

            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=severity,
                summary=summary,
                raw_data=data,
                enriched_at=datetime.now(tz=timezone.utc),
            )

        elif ioc.type in {IOCType.domain, IOCType.ipv4}:
            if query_status not in {"is_host", "ok"}:
                return None

            urls_count = data.get("urls_count", 0)
            tags = data.get("tags", []) or []

            severity = Severity.high if urls_count > 0 else Severity.info

            summary = f"URLhaus: {urls_count} URLs maliciosas asociadas, tags: {tags}"

            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=severity,
                summary=summary,
                raw_data=data,
                enriched_at=datetime.now(tz=timezone.utc),
            )

        elif ioc.type == IOCType.hash_sha256:
            if query_status != "ok":
                return None

            tags = data.get("tags", []) or []
            file_type = data.get("file_type", "unknown")

            summary = f"URLhaus payload: tags={tags}, tipo={file_type}"

            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.critical,
                summary=summary,
                raw_data=data,
                enriched_at=datetime.now(tz=timezone.utc),
            )

        return None
