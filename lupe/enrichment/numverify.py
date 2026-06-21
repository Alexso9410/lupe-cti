from __future__ import annotations

import httpx
from datetime import datetime, timezone

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity

_NUMVERIFY_URL = "http://apilayer.net/api/validate"  # HTTP — free tier no redirige a HTTPS


def _numverify_to_severity(valid: bool, line_type: str) -> Severity:
    if not valid:
        return Severity.low
    if line_type in ("voip",):
        return Severity.medium
    return Severity.info


class NumVerifyPlugin(EnrichmentPlugin):
    name = "numverify"
    supported_ioc_types: set[IOCType] = {IOCType.phone}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        params = {
            "access_key": self._api_key,
            "number": ioc.value,
            "format": "1",
        }
        try:
            response = await client.get(_NUMVERIFY_URL, params=params, timeout=15.0)
        except httpx.RequestError:
            return None
        if response.status_code != 200:
            return None
        data: dict = response.json()
        if data.get("success") is False or "error" in data:
            return None

        valid = data.get("valid", False)
        intl_fmt = data.get("international_format", ioc.value)
        country_name = data.get("country_name", "N/A")
        carrier = data.get("carrier", "N/A")
        line_type = data.get("line_type", "unknown")

        severity = _numverify_to_severity(valid, line_type)
        summary = (
            f"NumVerify: {intl_fmt} | {country_name} | {carrier} | "
            f"{line_type} | válido={valid}"
        )
        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )
