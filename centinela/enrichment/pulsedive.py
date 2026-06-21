from __future__ import annotations
from datetime import datetime, timezone
import httpx
from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity


class PulsedivePlugin(EnrichmentPlugin):
    name = "pulsedive"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4, IOCType.domain, IOCType.url}
    requires_api_key = True  # free community tier

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        encoded_value = httpx.URL("https://pulsedive.com/api/indicator.php").copy_with(
            params={"indicator": ioc.value, "pretty": "1", "key": self._api_key}
        )

        try:
            resp = await client.get(str(encoded_value))
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        risk = data.get("risk", "none")
        threats = data.get("threats", [])
        feeds = data.get("feeds", [])

        # If risk=none and no threats -> clean
        if risk == "none" and not threats:
            return None

        # Map risk to severity
        risk_map = {
            "none": Severity.info,
            "low": Severity.low,
            "medium": Severity.medium,
            "high": Severity.high,
            "critical": Severity.critical,
        }
        severity = risk_map.get(risk.lower(), Severity.info)

        threat_names = [t.get("name", "") for t in threats if t.get("name")]
        feed_names = [f.get("name", "") for f in feeds if f.get("name")]

        threats_str = ", ".join(threat_names[:5]) if threat_names else "sin nombre"
        feeds_str = ", ".join(feed_names) if feed_names else "sin feeds"
        summary = f"Pulsedive: riesgo={risk} | amenazas: {threats_str} | feeds: {feeds_str}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={"iid": data.get("iid"), "risk": risk, "indicator": data.get("indicator"), "threats": threats, "feeds": feeds},
            enriched_at=datetime.now(tz=timezone.utc),
        )
