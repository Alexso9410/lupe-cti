"""TXT export formatter for case history and individual IOCs."""

from __future__ import annotations

from datetime import datetime, timezone

_SEPARATOR = "=" * 72
_SUBSEP = "-" * 72


def export_case_to_txt(history: dict) -> str:
    """Export a full case history to TXT format.

    Args:
        history: CaseHistory dict from build_case_history().

    Returns:
        Formatted TXT string with executive summary and IOC-grouped details.
    """
    lines: list[str] = []
    case = history.get("case", {})
    stats = history.get("stats", {})
    iocs = history.get("iocs", [])
    notes = history.get("case_notes", [])

    # --- Executive Summary ---
    lines.append(_SEPARATOR)
    lines.append("EXECUTIVE SUMMARY")
    lines.append(_SEPARATOR)
    lines.append(f"Case:        {case.get('name', 'N/A')}")
    lines.append(f"Description: {case.get('description', '')}")
    lines.append(f"Status:      {case.get('status', 'unknown')}")
    lines.append(f"Created:     {case.get('created_at', 'N/A')}")
    lines.append(f"IOCs:        {stats.get('ioc_count', 0)}")
    lines.append(f"Enrichments: {stats.get('enrichment_count', 0)}")
    lines.append(f"Analyses:    {stats.get('analysis_count', 0)}")
    lines.append(f"Top Severity:{stats.get('top_severity', 'info')}")
    lines.append(f"Exported:    {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    if not iocs:
        lines.append("No IOCs in case.")
        lines.append("")
        return "\n".join(lines)

    # --- Case Notes ---
    if notes:
        lines.append(_SEPARATOR)
        lines.append("CASE NOTES")
        lines.append(_SEPARATOR)
        for note in notes:
            lines.append(f"[{note.get('created_at', '')}] {note.get('content', '')}")
        lines.append("")

    # --- IOC Details ---
    for ioc_group in iocs:
        ioc = ioc_group.get("ioc", {})
        events = ioc_group.get("events", [])
        lines.append(_SEPARATOR)
        lines.append(f"IOC: [{ioc.get('type', 'unknown')}] {ioc.get('value', 'N/A')}")
        lines.append(_SEPARATOR)
        lines.append("")

        for event in events:
            ev_type = event.get("event_type", "")
            if ev_type == "ioc_added":
                lines.append(f"  [{event.get('timestamp', '')}] IOC ADDED")
                lines.append(f"    Type: {event.get('ioc_type', 'unknown')}")
                lines.append("")
            elif ev_type == "enrichment":
                ts = event.get("timestamp", "")
                src = event.get("source", "")
                lines.append(f"  [{ts}] ENRICHMENT — {src}")
                lines.append(f"    Severity: {event.get('detail', event.get('severity', ''))}")
                lines.append(f"    Summary:  {event.get('summary', event.get('description', ''))}")
                lines.append("")
            elif ev_type == "analysis":
                ts = event.get("timestamp", "")
                mdl = event.get("model", "")
                lines.append(f"  [{ts}] AI ANALYSIS — {mdl}")
                lines.append(f"    {event.get('summary', '')}")
                lines.append("")

    return "\n".join(lines)


def export_ioc_to_txt(ioc_data: dict, case_info: dict | None = None) -> str:
    """Export a single IOC's data to TXT format.

    Args:
        ioc_data: Single IOC group dict with 'ioc' and 'events' keys.
        case_info: Optional case metadata dict.

    Returns:
        Formatted TXT string for this IOC only.
    """
    lines: list[str] = []
    ioc = ioc_data.get("ioc", {})
    events = ioc_data.get("events", [])

    lines.append(_SEPARATOR)
    if case_info:
        lines.append(f"Case: {case_info.get('name', 'N/A')}")
    lines.append(f"IOC: [{ioc.get('type', 'unknown')}] {ioc.get('value', 'N/A')}")
    lines.append(_SEPARATOR)
    lines.append("")

    for event in events:
        ev_type = event.get("event_type", "")
        if ev_type == "ioc_added":
            lines.append(
                f"  [{event.get('timestamp', '')}] IOC ADDED "
                f"— Type: {event.get('ioc_type', 'unknown')}"
            )
            lines.append("")
        elif ev_type == "enrichment":
            lines.append(f"  [{event.get('timestamp', '')}] ENRICHMENT — {event.get('source', '')}")
            lines.append(f"    Severity: {event.get('detail', event.get('severity', ''))}")
            lines.append(f"    Summary:  {event.get('summary', event.get('description', ''))}")
            lines.append("")
        elif ev_type == "analysis":
            lines.append(f"  [{event.get('timestamp', '')}] AI ANALYSIS — {event.get('model', '')}")
            lines.append(f"    {event.get('summary', '')}")
            lines.append("")

    return "\n".join(lines)
