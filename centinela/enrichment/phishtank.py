from __future__ import annotations

from datetime import datetime, timezone

import httpx

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity


class PhishTankPlugin(EnrichmentPlugin):
    name = "phishtank"
    supported_ioc_types: set[IOCType] = {IOCType.url}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        data = {
            "url": ioc.value,
            "format": "json",
            "app_key": self._api_key,
        }

        try:
            resp = await client.post(
                "https://checkurl.phishtank.com/checkurl/",
                data=data,
            )
            resp.raise_for_status()
            result_json = resp.json()
            results = result_json.get("results", {})
        except Exception:
            return None

        if not results.get("in_database", False):
            return None

        verified = results.get("verified", False)
        valid = results.get("valid", False)
        detail_page = results.get("phish_detail_page", "sin detalle")

        # Only consider it a threat if valid (still actively phishing)
        if not valid:
            return None

        if verified:
            severity = Severity.critical
        else:
            severity = Severity.high

        status = "VERIFICADO" if verified else "reportado"
        summary = f"PhishTank: PHISHING {status} | {detail_page}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={"phish_detail_page": detail_page, "verified": verified, "valid": valid},
            enriched_at=datetime.now(tz=timezone.utc),
        )
