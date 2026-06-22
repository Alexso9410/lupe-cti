"""Case management module — wraps Database methods for IOC case management."""

from __future__ import annotations

from dataclasses import dataclass

from lupe.db import Database
from lupe.config import get_settings


@dataclass
class CaseInfo:
    """Lightweight case representation."""

    id: int
    name: str
    description: str
    status: str
    ioc_count: int


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
    return CaseInfo(id=case_id, name=name, description=description, status="open", ioc_count=0)


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
