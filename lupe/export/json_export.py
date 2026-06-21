from __future__ import annotations

from datetime import datetime, timezone

from lupe.models import IOC, EnrichmentResult, Severity

_SEVERITY_RANK: dict[Severity, int] = {
    Severity.info: 0,
    Severity.low: 1,
    Severity.medium: 2,
    Severity.high: 3,
    Severity.critical: 4,
}


def _highest_severity(enrichments: list[EnrichmentResult]) -> Severity:
    """Return the highest severity across all enrichment results."""
    if not enrichments:
        return Severity.info
    return max(enrichments, key=lambda e: _SEVERITY_RANK[e.severity]).severity


def export_ioc_to_json(
    ioc: IOC,
    enrichments: list[EnrichmentResult],
    analysis: str | None = None,
    case_name: str | None = None,
) -> dict:
    """Generate a JSON-serializable dict for an IOC enrichment result.

    Args:
        ioc: The IOC being documented.
        enrichments: List of enrichment results from plugins.
        analysis: Optional AI-generated analysis text.
        case_name: Optional case identifier (e.g. "OP-2026-14").

    Returns:
        A dict that is safe to pass to ``json.dumps``.
    """
    severity = _highest_severity(enrichments)

    serialized_enrichments = [
        {
            "source": e.source,
            "severity": e.severity.value,
            "summary": e.summary,
            "raw_data": e.raw_data,
            "enriched_at": e.enriched_at.isoformat(),
        }
        for e in enrichments
    ]

    payload: dict = {
        "ioc": {
            "type": ioc.type.value,
            "value": ioc.value,
        },
        "severity": severity.value,
        "enrichments": serialized_enrichments,
        "analysis": analysis,
        "case": case_name,
        "exported_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    return payload
