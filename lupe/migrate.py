"""Migration script: copy legacy Centinela DB to Lupe CTI XDG path.

Usage:
    lupe migrate-from-centinela
    python -m lupe.migrate

This is an opt-in, one-time migration. It does NOT run automatically.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from lupe.config import get_data_dir


_LEGACY_DB_PATH = Path.home() / ".centinela" / "centinela.db"


def migrate_from_centinela(
    legacy_path: Path | None = None,
    target_dir: Path | None = None,
    *,
    dry_run: bool = False,
) -> dict:
    """Copy the legacy Centinela DB to the new Lupe CTI XDG path.

    Args:
        legacy_path: Path to legacy DB. Defaults to ~/.centinela/centinela.db.
        target_dir: Target directory. Defaults to platformdirs data dir.
        dry_run: If True, only report what would happen.

    Returns:
        Dict with migration summary: source, target, tables, row_counts, backup_path.
    """
    source = legacy_path or _LEGACY_DB_PATH
    target_parent = target_dir or get_data_dir()
    target = target_parent / "lupe.db"

    result: dict = {
        "source": str(source),
        "target": str(target),
        "source_exists": source.exists(),
        "migrated": False,
        "backup_path": None,
        "tables": {},
        "error": None,
    }

    if not source.exists():
        result["error"] = f"Legacy DB not found: {source}"
        return result

    if dry_run:
        result["tables"] = _count_rows(source)
        result["dry_run"] = True
        return result

    # Create backup
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = source.with_name(f"centinela.db.bak.{timestamp}")
    shutil.copy2(source, backup_path)
    result["backup_path"] = str(backup_path)

    # Create target directory
    target_parent.mkdir(parents=True, exist_ok=True)

    # Copy DB
    shutil.copy2(source, target)
    result["migrated"] = True

    # Count rows for verification
    result["tables"] = _count_rows(target)

    return result


def _count_rows(db_path: Path) -> dict[str, int]:
    """Count rows in all tables of a SQLite database."""
    counts: dict[str, int] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cur.fetchall()]
        for table in tables:
            cur = conn.execute(f"SELECT count(*) FROM [{table}]")
            counts[table] = cur.fetchone()[0]
        conn.close()
    except sqlite3.Error:
        pass
    return counts


def main() -> None:
    """CLI entry point for migration."""
    print("\nLupe CTI — Migration from Centinela\n")

    if not _LEGACY_DB_PATH.exists():
        print(f"  Legacy DB not found at: {_LEGACY_DB_PATH}")
        print("  Nothing to migrate.")
        sys.exit(1)

    print(f"  Source: {_LEGACY_DB_PATH}")
    result = migrate_from_centinela()

    if result.get("error"):
        print(f"  Error: {result['error']}")
        sys.exit(1)

    print(f"  Target: {result['target']}")
    print(f"  Backup: {result['backup_path']}")
    print()

    if result["tables"]:
        print("  Tables migrated:")
        for table, count in result["tables"].items():
            print(f"    {table}: {count} rows")
    print()
    print("  Migration complete!")
    print()


if __name__ == "__main__":
    main()
