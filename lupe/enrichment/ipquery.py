from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity


class IPQueryPlugin(EnrichmentPlugin):
    name = "ipquery"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4, IOCType.ipv6}
    requires_api_key = False

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query IPQuery API for IP reputation, geolocation and network data."""
        try:
            resp = await client.get(f"https://api.ipquery.io/{ioc.value}")
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        risk = data.get("risk", {})
        location = data.get("location", {})
        isp = data.get("isp", {})

        risk_score = risk.get("risk_score", 0)
        is_tor = risk.get("is_tor", False)
        is_vpn = risk.get("is_vpn", False)

        # Determine severity
        if risk_score >= 75 or is_tor:
            severity = Severity.high
        elif risk_score >= 50 or is_vpn:
            severity = Severity.medium
        elif risk_score >= 25:
            severity = Severity.low
        else:
            severity = Severity.info

        country = location.get("country", "unknown")
        city = location.get("city", "unknown")
        asn = isp.get("asn", "unknown")
        is_proxy = risk.get("is_proxy", False)

        summary = (
            f"IPQuery: score={risk_score} | {country}/{city} | "
            f"ASN={asn} | flags: vpn={is_vpn}, tor={is_tor}, proxy={is_proxy}"
        )

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={"risk": risk, "location": location, "isp": isp},
            enriched_at=datetime.now(tz=timezone.utc),
        )
