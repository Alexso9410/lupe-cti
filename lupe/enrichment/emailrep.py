from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity


class EmailRepPlugin(EnrichmentPlugin):
    name = "emailrep"
    supported_ioc_types: set[IOCType] = {IOCType.email}
    requires_api_key = False  # works with low rate limit without key

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        try:
            headers = {}
            if self._api_key:
                headers["Key"] = self._api_key
            resp = await client.get(f"https://emailrep.io/{ioc.value}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        details = data.get("details", {})
        reputation = data.get("reputation", "unknown")
        suspicious = data.get("suspicious", False)
        credentials_leaked = details.get("credentials_leaked", False)
        data_breach = details.get("data_breach", False)
        spam_lists = details.get("spam_lists", False)
        disposable = details.get("disposable", False)
        profiles = details.get("profiles", [])

        # Determine severity
        if suspicious and credentials_leaked:
            severity = Severity.high
        elif suspicious:
            severity = Severity.medium
        elif data_breach or spam_lists:
            severity = Severity.low
        else:
            severity = Severity.info

        profiles_str = ", ".join(profiles[:5]) if profiles else "ninguno"
        summary = (
            f"EmailRep: rep={reputation} | suspicious={suspicious} "
            f"| breach={data_breach} | leaked={credentials_leaked} "
            f"| disposable={disposable} | perfiles: {profiles_str}"
        )

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={
                "reputation": reputation,
                "suspicious": suspicious,
                "details": details,
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
