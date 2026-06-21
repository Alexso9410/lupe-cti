from __future__ import annotations

from datetime import datetime, timezone

import httpx

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity

_URLSCAN_SEARCH = "https://urlscan.io/api/v1/search/"


def _verdict_to_severity(verdict: str, score: int) -> Severity:
    verdict_lower = verdict.lower()
    if verdict_lower == "malicious":
        return Severity.critical
    if verdict_lower == "suspicious" or score >= 50:
        return Severity.high
    return Severity.info


def _build_query(ioc: IOC) -> str:
    if ioc.type == IOCType.ipv4:
        return f"page.ip:{ioc.value}"
    if ioc.type == IOCType.domain:
        return f"page.domain:{ioc.value}"
    # url type — search by domain extracted or use the full URL
    return f"page.url:{ioc.value}"


class URLScanPlugin(EnrichmentPlugin):
    name = "urlscan"
    supported_ioc_types: set[IOCType] = {
        IOCType.domain,
        IOCType.url,
        IOCType.ipv4,
    }
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Search urlscan.io for scan history, verdicts, and targeted brands."""
        query = _build_query(ioc)
        headers = {"API-Key": self._api_key}
        params = {"q": query, "size": "10"}

        try:
            response = await client.get(
                _URLSCAN_SEARCH, headers=headers, params=params, timeout=15.0
            )
        except httpx.RequestError:
            return None

        if response.status_code == 429:
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="urlscan.io rate limit reached — try again later",
                raw_data={"error": "rate_limited"},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        if response.status_code != 200:
            return None

        data: dict = response.json()
        total: int = data.get("total", 0)
        results: list[dict] = data.get("results", [])

        if not results:
            return None

        # Aggregate verdicts from results
        worst_verdict = "benign"
        worst_score = 0
        brands: set[str] = set()

        for entry in results:
            page: dict = entry.get("page", {})
            verdicts: dict = entry.get("verdicts", {})
            overall: dict = verdicts.get("overall", {})

            verdict_str: str = overall.get("verdict", "") or ""
            score: int = overall.get("score", 0) or 0

            if verdict_str.lower() == "malicious":
                worst_verdict = "malicious"
                worst_score = max(worst_score, score)
            elif verdict_str.lower() == "suspicious" and worst_verdict != "malicious":
                worst_verdict = "suspicious"
                worst_score = max(worst_score, score)

            for brand in overall.get("brands", []):
                if isinstance(brand, str):
                    brands.add(brand)
                elif isinstance(brand, dict) and brand.get("name"):
                    brands.add(brand["name"])

        parts: list[str] = [
            f"Scans: {total}",
            f"Verdict: {worst_verdict}",
            f"Score: {worst_score}",
        ]
        if brands:
            parts.append(f"Brands: {', '.join(sorted(brands)[:3])}")

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=_verdict_to_severity(worst_verdict, worst_score),
            summary=" | ".join(parts),
            raw_data={"total": total, "verdict": worst_verdict, "score": worst_score, "brands": list(brands)},
            enriched_at=datetime.now(tz=timezone.utc),
        )
