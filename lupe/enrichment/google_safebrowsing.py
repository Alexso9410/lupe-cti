from __future__ import annotations

from datetime import datetime, timezone

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity


class GoogleSafeBrowsingPlugin(EnrichmentPlugin):
    """Check URLs and domains against Google Safe Browsing threat lists."""

    name = "google_safebrowsing"
    supported_ioc_types: set[IOCType] = {IOCType.url, IOCType.domain}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        url_to_check = ioc.value
        if ioc.type == IOCType.domain:
            url_to_check = f"https://{ioc.value}"

        payload = {
            "client": {"clientId": "lupe-cti", "clientVersion": "1.0.0"},
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url_to_check}],
            },
        }

        try:
            resp = await client.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={self._api_key}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        if not data or "matches" not in data:
            return None

        matches = data["matches"]
        if not matches:
            return None

        first_match = matches[0]
        threat_type = first_match.get("threatType", "UNKNOWN")
        platform = first_match.get("platformType", "UNKNOWN")

        if threat_type in ("MALWARE", "SOCIAL_ENGINEERING"):
            severity = Severity.critical
        elif threat_type == "UNWANTED_SOFTWARE":
            severity = Severity.high
        else:
            severity = Severity.medium

        summary = (
            f"Google SafeBrowsing: AMENAZA DETECTADA | tipo={threat_type} | plataforma={platform}"
        )

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={"matches": matches},
            enriched_at=datetime.now(tz=timezone.utc),
        )
