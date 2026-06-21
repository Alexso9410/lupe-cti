"""Tests for DB migration from Centinela to Lupe CTI (PR-5)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from lupe.migrate import _count_rows, migrate_from_centinela


def _create_fake_legacy_db(db_path: Path) -> None:
    """Create a fake Centinela DB with schema and sample data."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS iocs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            value TEXT NOT NULL,
            first_seen TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(type, value)
        );
        CREATE TABLE IF NOT EXISTS enrichments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL REFERENCES iocs(id),
            source TEXT NOT NULL,
            raw_data TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            summary TEXT NOT NULL DEFAULT '',
            enriched_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(ioc_id, source)
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL REFERENCES iocs(id),
            model TEXT NOT NULL,
            summary TEXT NOT NULL,
            analyzed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO iocs (type, value) VALUES ('ipv4', '8.8.8.8');
        INSERT INTO iocs (type, value) VALUES ('domain', 'evil.com');
        INSERT INTO enrichments (ioc_id, source, raw_data, severity, summary)
            VALUES (1, 'ipinfo', '{}', 'info', 'Google DNS');
    """)
    conn.close()


class TestMigration:
    """Tests for migrate_from_centinela function."""

    def test_migrate_command_exists(self) -> None:
        from lupe.migrate import migrate_from_centinela

        assert callable(migrate_from_centinela)

    def test_legacy_not_found_returns_error(self, tmp_path: Path) -> None:
        result = migrate_from_centinela(
            legacy_path=tmp_path / "nonexistent.db",
            target_dir=tmp_path / "target",
        )
        assert result["source_exists"] is False
        assert result["migrated"] is False
        assert "not found" in result["error"].lower()

    def test_backup_created(self, tmp_path: Path) -> None:
        legacy = tmp_path / "centinela.db"
        _create_fake_legacy_db(legacy)

        result = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
        )

        assert result["migrated"] is True
        assert result["backup_path"] is not None
        backup = Path(result["backup_path"])
        assert backup.exists()
        assert "centinela.db.bak" in backup.name

    def test_data_integrity_after_migration(self, tmp_path: Path) -> None:
        legacy = tmp_path / "centinela.db"
        _create_fake_legacy_db(legacy)

        result = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
        )

        assert result["migrated"] is True
        target = Path(result["target"])
        assert target.exists()

        # Verify row counts
        assert result["tables"]["iocs"] == 2
        assert result["tables"]["enrichments"] == 1

    def test_target_db_is_valid_sqlite(self, tmp_path: Path) -> None:
        legacy = tmp_path / "centinela.db"
        _create_fake_legacy_db(legacy)

        result = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
        )

        target = Path(result["target"])
        conn = sqlite3.connect(str(target))
        cur = conn.execute("SELECT value FROM iocs WHERE type='ipv4'")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "8.8.8.8"
        conn.close()

    def test_dry_run_does_not_copy(self, tmp_path: Path) -> None:
        legacy = tmp_path / "centinela.db"
        _create_fake_legacy_db(legacy)

        result = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
            dry_run=True,
        )

        assert result.get("dry_run") is True
        assert result["migrated"] is False
        assert not (tmp_path / "target" / "lupe.db").exists()

    def test_idempotent_migration(self, tmp_path: Path) -> None:
        """Migrating twice should not corrupt data."""
        legacy = tmp_path / "centinela.db"
        _create_fake_legacy_db(legacy)

        # First migration
        result1 = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
        )
        assert result1["migrated"] is True

        # Second migration (overwrites)
        result2 = migrate_from_centinela(
            legacy_path=legacy,
            target_dir=tmp_path / "target",
        )
        assert result2["migrated"] is True
        assert result2["tables"]["iocs"] == 2


class TestCountRows:
    """Tests for _count_rows helper."""

    def test_count_rows_returns_dict(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        _create_fake_legacy_db(db_path)
        counts = _count_rows(db_path)
        assert isinstance(counts, dict)
        assert "iocs" in counts
        assert counts["iocs"] == 2

    def test_count_rows_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        counts = _count_rows(tmp_path / "nonexistent.db")
        assert counts == {}
