"""Case management module — wraps Database methods for IOC case management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

from lupe.config import get_settings
from lupe.db import Database


class CaseHistory(TypedDict):
    """Structured case history grouped by IOC."""

    case: dict[str, Any]
    iocs: list[dict[str, Any]]
    case_notes: list[dict[str, Any]]
    stats: dict[str, Any]


@dataclass
class CaseInfo:
    """Lightweight case representation."""

    id: int
    name: str
    description: str
    status: str
    ioc_count: int
    created_at: datetime | None = None


@dataclass
class CaseIOC:
    """IOC linked to a case."""

    id: int
    type: str
    value: str
    notes: str


def _get_db() -> Database:
    """Get a Database instance from settings."""
    settings = get_settings()
    return Database(settings.db_path)


def _coerce_dt(value: object) -> datetime | None:
    """Best-effort coerce DB value to datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def list_cases(status: str | None = None) -> list[CaseInfo]:
    """List all cases, optionally filtered by status.

    Args:
        status: If provided, only return cases with this status.

    Returns:
        List of CaseInfo objects.
    """
    db = _get_db()
    rows = db.list_cases(status=status)
    return [
        CaseInfo(
            id=r["id"],
            name=r["name"],
            description=r.get("description", ""),
            status=r["status"],
            ioc_count=r.get("ioc_count", 0),
            created_at=_coerce_dt(r.get("created_at")),
        )
        for r in rows
    ]


def create_case(name: str, description: str = "") -> CaseInfo:
    """Create a new investigation case.

    Args:
        name: Short display name for the case.
        description: Optional longer description.

    Returns:
        CaseInfo of the newly created case.
    """
    db = _get_db()
    case_id = db.create_case(name, description)
    # Read the row back to get the actual created_at from the DB
    try:
        rows = db.list_cases()
        for r in rows:
            if r["id"] == case_id:
                return CaseInfo(
                    id=case_id,
                    name=name,
                    description=description,
                    status=r.get("status", "open"),
                    ioc_count=r.get("ioc_count", 0),
                    created_at=_coerce_dt(r.get("created_at")),
                )
    except Exception:
        pass
    return CaseInfo(
        id=case_id,
        name=name,
        description=description,
        status="open",
        ioc_count=0,
        created_at=datetime.now(),
    )


def add_ioc_to_case(
    case_id: int,
    ioc_value: str,
    ioc_type: str,
    notes: str = "",
) -> int:
    """Add an IOC to an investigation case.

    Args:
        case_id: The case to add the IOC to.
        ioc_value: The raw IOC value.
        ioc_type: The IOC type string (e.g. 'ipv4', 'domain').
        notes: Optional analyst notes.

    Returns:
        The IOC database ID.
    """
    db = _get_db()
    ioc_id = db.upsert_ioc(ioc_type, ioc_value)
    db.link_ioc_to_case(case_id, ioc_id, notes)
    return ioc_id


def delete_case(case_id: int) -> bool:
    """Delete an investigation case by ID.

    Args:
        case_id: The case to delete.

    Returns:
        True if the case was deleted, False if not found.
    """
    db = _get_db()
    return db.delete_case(case_id)


def update_case(
    case_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
) -> bool:
    """Update a case's name and/or description.

    Args:
        case_id: The case to update.
        name: New name (keyword-only, optional).
        description: New description (keyword-only, optional).

    Returns:
        True if the case was updated, False if not found.
    """
    db = _get_db()
    return db.update_case(case_id, name=name, description=description)


def build_case_history(case_id: int) -> CaseHistory:
    """Build a complete case history with events grouped by IOC.

    Args:
        case_id: The case to build history for.

    Returns:
        CaseHistory dict with case metadata, grouped IOCs, notes, and stats.
    """
    db = _get_db()

    case = db.get_case(case_id)
    if case is None:
        return CaseHistory(case={}, iocs=[], case_notes=[], stats={})

    # Get raw timeline and group by IOC
    timeline = db.get_case_timeline(case_id)
    case_notes = db.get_case_notes(case_id)

    # Group events by IOC value
    ioc_groups: dict[str, dict[str, Any]] = {}
    for event in timeline:
        if event["event_type"] == "note":
            continue
        ioc_value = event.get("ioc_value", "")
        if not ioc_value:
            continue

        if ioc_value not in ioc_groups:
            # Find the IOC record
            ioc_record = db.find_ioc(ioc_value)
            ioc_groups[ioc_value] = {
                "ioc": {
                    "id": ioc_record["id"] if ioc_record else 0,
                    "type": ioc_record["type"] if ioc_record else "unknown",
                    "value": ioc_value,
                    "added_at": event.get("timestamp", ""),
                },
                "events": [],
            }
        ioc_groups[ioc_value]["events"].append(event)

    # Sort events within each IOC group
    for group in ioc_groups.values():
        group["events"].sort(key=lambda e: e.get("timestamp", ""))

    # Build stats
    enrichment_count = sum(
        1 for e in timeline if e["event_type"] == "enrichment"
    )
    analysis_count = sum(
        1 for e in timeline if e["event_type"] == "analysis"
    )

    # Determine top severity
    _order = ["critical", "high", "medium", "low", "info"]
    top_severity = "info"
    for event in timeline:
        if event["event_type"] == "enrichment":
            sev = event.get("detail", "info")
            if sev in _order and _order.index(sev) < _order.index(top_severity):
                top_severity = sev

    return CaseHistory(
        case=case,
        iocs=list(ioc_groups.values()),
        case_notes=case_notes,
        stats={
            "ioc_count": len(ioc_groups),
            "enrichment_count": enrichment_count,
            "analysis_count": analysis_count,
            "top_severity": top_severity,
        },
    )
