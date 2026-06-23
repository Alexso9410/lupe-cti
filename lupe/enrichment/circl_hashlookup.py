from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity


class CIRCLHashlookupPlugin(EnrichmentPlugin):
    name = "circl_hashlookup"
    supported_ioc_types: set[IOCType] = {IOCType.hash_md5, IOCType.hash_sha1, IOCType.hash_sha256}
    requires_api_key = False

    _PATH = {
        IOCType.hash_md5: "md5",
        IOCType.hash_sha1: "sha1",
        IOCType.hash_sha256: "sha256",
    }

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        path = self._path_for_type(ioc.type)
        if not path:
            return None

        try:
            resp = await client.get(f"https://hashlookup.circl.lu/lookup/{path}/{ioc.value}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        _unset = object()
        known_malicious = data.get("KnownMalicious", _unset)
        filename = data.get("FileName", "unknown")
        file_size = data.get("FileSize", "unknown")

        if known_malicious is _unset:
            malicious = None
        elif isinstance(known_malicious, str):
            malicious = known_malicious.lower() == "true"
        else:
            malicious = known_malicious is True

        if malicious is True:
            severity = Severity.critical
        elif malicious is False:
            severity = Severity.info
        else:
            severity = Severity.medium

        if malicious is True:
            status = "MALICIOSO"
        elif malicious is False:
            status = "benigno"
        else:
            status = "desconocido"
        summary = f"CIRCL Hashlookup: {status} | archivo={filename} | size={file_size}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )

    def _path_for_type(self, ioc_type: IOCType) -> str | None:
        return self._PATH.get(ioc_type)
