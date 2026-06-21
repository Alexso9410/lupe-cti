from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity

_HIBP_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"


def _breaches_to_severity(count: int) -> Severity:
    if count > 5:
        return Severity.critical
    if count > 2:
        return Severity.high
    if count > 0:
        return Severity.medium
    return Severity.info


class HaveIBeenPwnedPlugin(EnrichmentPlugin):
    name = "hibp"
    supported_ioc_types: set[IOCType] = {IOCType.email}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query Have I Been Pwned for email address breach exposure."""
        url = _HIBP_URL.format(email=ioc.value)
        headers = {
            "hibp-api-key": self._api_key,
            "User-Agent": "centinela-ioc-enrichment/2.0",
        }
        params = {"truncateResponse": "false"}

        try:
            response = await client.get(
                url, headers=headers, params=params, timeout=15.0
            )
        except httpx.RequestError:
            return None

        if response.status_code == 404:
            # 404 means the email was NOT found in any breach — good news
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="No breaches found for this email",
                raw_data={"breaches": []},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        if response.status_code == 429:
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="HIBP rate limit reached — try again later",
                raw_data={"error": "rate_limited"},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        if response.status_code != 200:
            return None

        breaches: list[dict] = response.json()
        count = len(breaches)

        # Collect data classes across all breaches
        all_data_classes: set[str] = set()
        for breach in breaches:
            for dc in breach.get("DataClasses", []):
                all_data_classes.add(dc)

        # Find the most recent breach date
        dates = [b.get("BreachDate", "") for b in breaches if b.get("BreachDate")]
        latest = max(dates) if dates else "unknown"

        breach_names = [b.get("Name", "") for b in breaches if b.get("Name")]

        # Summarise most impactful data classes
        notable = {"Passwords", "Email addresses", "Usernames", "Credit cards"}
        impactful = sorted(all_data_classes & notable) or sorted(all_data_classes)[:3]

        parts: list[str] = [
            f"Breaches: {count}",
            f"Includes: {', '.join(impactful[:3])}",
            f"Latest: {latest}",
        ]

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_breaches_to_severity(count),
            summary=" | ".join(parts),
            raw_data={
                "breach_count": count,
                "breach_names": breach_names,
                "data_classes": list(all_data_classes),
                "latest_breach": latest,
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
