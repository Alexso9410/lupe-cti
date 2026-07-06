from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

logger = logging.getLogger(__name__)

_GREYNOISE_URL = "https://api.greynoise.io/v3/community/"


def _classify_severity(noise: bool, riot: bool, classification: str) -> Severity:
    if riot:
        return Severity.info  # Servicio benigno conocido (Google, Cloudflare)
    if classification == "malicious":
        return Severity.high
    if classification == "benign":
        return Severity.info
    if noise and classification == "unknown":
        return Severity.medium  # Scanner masivo pero no clasificado
    return Severity.info


class GreyNoisePlugin(EnrichmentPlugin):
    name = "greynoise"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Query GreyNoise for IP reputation and mass scanning activity."""
        headers = {"key": self._api_key}
        try:
            response = await client.get(
                f"{_GREYNOISE_URL}{ioc.value}",
                headers=headers,
                timeout=15.0,
            )
        except httpx.RequestError as exc:
            logger.debug("GreyNoise request error for %s: %s", ioc.value, exc)
            return None

        if response.status_code == 404:
            # IP no conocida por GreyNoise → no es un error
            logger.debug("GreyNoise no data for %s (404)", ioc.value)
            return None

        if response.status_code == 429:
            # Rate limit → retornar None
            logger.debug("GreyNoise rate limited for %s (429)", ioc.value)
            return None

        if response.status_code != 200:
            logger.debug("GreyNoise non-200 status %s for %s", response.status_code, ioc.value)
            return None

        data: dict = response.json()

        noise = data.get("noise", False)
        riot = data.get("riot", False)
        classification = data.get("classification", "unknown")
        name = data.get("name")
        last_seen = data.get("last_seen")

        severity = _classify_severity(noise, riot, classification)

        summary = (
            f"GreyNoise: classification={classification}, "
            f"noise={noise}, riot={riot}, "
            f"name={name}, last_seen={last_seen}"
        )

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )
