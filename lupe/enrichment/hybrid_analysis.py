"""Hybrid Analysis plugin — hash and URL sandbox analysis.

Freemium, requires API key: LUPE_HYBRID_ANALYSIS_KEY
API: https://www.hybrid-analysis.com/api/v2/
"""

from __future__ import annotations

import logging

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity
from datetime import datetime

logger = logging.getLogger(__name__)


class HybridAnalysisPlugin(EnrichmentPlugin):
    """Hybrid Analysis — sandbox analysis for hashes and URLs."""

    name = "hybrid_analysis"
    supported_ioc_types = {IOCType.hash_sha256, IOCType.hash_md5, IOCType.hash_sha1, IOCType.url}
    requires_api_key = True

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query Hybrid Analysis for hash or URL analysis."""
        if not self._api_key:
            return None

        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        if ioc.type in (IOCType.hash_sha256, IOCType.hash_md5, IOCType.hash_sha1):
            url = "https://www.hybrid-analysis.com/api/v2/search/hash"
            data = {"hash": ioc.value}
        elif ioc.type == IOCType.url:
            url = "https://www.hybrid-analysis.com/api/v2/search/hash"
            data = {"domain": ioc.value}
        else:
            return None

        try:
            response = await client.post(
                url, headers=headers, data=data, timeout=30.0
            )
        except httpx.RequestError:
            logger.debug("Hybrid Analysis request failed for %s", ioc.value)
            return None

        if response.status_code == 429:
            logger.warning("Hybrid Analysis quota exceeded")
            return None

        if response.status_code == 401:
            logger.warning("Hybrid Analysis auth failed — check LUPE_HYBRID_ANALYSIS_KEY")
            return None

        if response.status_code != 200:
            return None

        try:
            result_data = response.json()
        except ValueError:
            return None

        if not result_data:
            return None

        # result_data is typically a list of submissions
        if isinstance(result_data, list):
            if not result_data:
                return None
            result_data = result_data[0]

        verdict = result_data.get("verdict", "unknown")
        threat_score = result_data.get("threat_score", 0)
        type_ = result_data.get("type_description", "")
        env = result_data.get("environment_description", "")

        severity_map = {
            "malicious": Severity.critical,
            "suspicious": Severity.high,
            "no specific threat": Severity.low,
            "unknown": Severity.info,
        }
        severity = severity_map.get(verdict.lower() if isinstance(verdict, str) else "", Severity.medium)

        return EnrichmentResult(
            source="hybrid_analysis",
            ioc_value=ioc.value,
            severity=severity,
            summary=f"Verdict: {verdict}, Score: {threat_score}, Type: {type_}",
            raw_data=result_data if isinstance(result_data, dict) else {"result": result_data},
            enriched_at=datetime.now(),
        )
