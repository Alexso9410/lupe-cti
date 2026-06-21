from __future__ import annotations

from datetime import datetime, timezone

import httpx

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity

_ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"


def _score_to_severity(score: int) -> Severity:
    if score >= 80:
        return Severity.critical
    if score >= 50:
        return Severity.high
    if score >= 25:
        return Severity.medium
    if score >= 1:
        return Severity.low
    return Severity.info


class AbuseIPDBPlugin(EnrichmentPlugin):
    name = "abuseipdb"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4, IOCType.ipv6}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query AbuseIPDB for IP reputation and abuse confidence score."""
        headers = {
            "Key": self._api_key,
            "Accept": "application/json",
        }
        params = {
            "ipAddress": ioc.value,
            "maxAgeInDays": "90",
            "verbose": "",
        }
        try:
            response = await client.get(
                _ABUSEIPDB_URL, headers=headers, params=params, timeout=10.0
            )
        except httpx.RequestError:
            return None

        if response.status_code == 429:
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="AbuseIPDB rate limit reached — try again later",
                raw_data={"error": "rate_limited"},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        if response.status_code != 200:
            return None

        data: dict = response.json()
        report_data: dict = data.get("data", {})

        score: int = report_data.get("abuseConfidenceScore", 0)
        total_reports: int = report_data.get("totalReports", 0)
        country: str = report_data.get("countryCode", "N/A")
        domain: str = report_data.get("domain", "") or "N/A"
        usage_type: str = report_data.get("usageType", "") or "N/A"
        isp: str = report_data.get("isp", "") or "N/A"

        parts: list[str] = [
            f"Confidence: {score}%",
            f"Reports: {total_reports}",
            f"Country: {country}",
            f"ISP: {isp}",
        ]
        if usage_type != "N/A":
            parts.append(f"Usage: {usage_type}")

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_score_to_severity(score),
            summary=" | ".join(parts),
            raw_data=report_data,
            enriched_at=datetime.now(tz=timezone.utc),
        )
