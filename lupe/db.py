from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_SCHEMA = """
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

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS case_iocs (
    case_id INTEGER NOT NULL REFERENCES cases(id),
    ioc_id INTEGER NOT NULL REFERENCES iocs(id),
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    notes TEXT DEFAULT '',
    PRIMARY KEY (case_id, ioc_id)
);

CREATE TABLE IF NOT EXISTS case_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER REFERENCES cases(id),
    file_path TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    from_addr TEXT NOT NULL,
    subject TEXT NOT NULL,
    analyzed_at TEXT NOT NULL DEFAULT (datetime('now')),
    spf TEXT NOT NULL DEFAULT 'none',
    dkim TEXT NOT NULL DEFAULT 'none',
    dmarc TEXT NOT NULL DEFAULT 'none',
    phishing_score REAL NOT NULL DEFAULT 0.0,
    ai_classification TEXT,
    ai_confidence REAL,
    ioc_count INTEGER NOT NULL DEFAULT 0,
    attachment_count INTEGER NOT NULL DEFAULT 0,
    full_result_json TEXT NOT NULL,
    pdf_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_iocs_value ON iocs(value);
CREATE INDEX IF NOT EXISTS idx_enrichments_ioc ON enrichments(ioc_id);
CREATE INDEX IF NOT EXISTS idx_case_iocs_case ON case_iocs(case_id);
CREATE INDEX IF NOT EXISTS idx_email_analyses_case ON email_analyses(case_id);
CREATE INDEX IF NOT EXISTS idx_email_analyses_score ON email_analyses(phishing_score DESC);
"""


class Database:
    """SQLite persistence layer for Lupe CTI IOC data and cases.

    Args:
        db_path: Path to the SQLite database file. Tildes are expanded.
    """

    def __init__(self, db_path: str) -> None:
        resolved = Path(db_path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(resolved), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        """Create all tables and indexes if they do not already exist."""
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # IOC CRUD
    # ------------------------------------------------------------------

    def upsert_ioc(self, ioc_type: str, value: str) -> int:
        """Insert an IOC or update last_seen if it already exists.

        Args:
            ioc_type: IOC type string (e.g. 'ipv4', 'domain').
            value: Raw IOC value.

        Returns:
            The row id of the upserted IOC.
        """
        cur = self._conn.execute(
            """
            INSERT INTO iocs (type, value)
            VALUES (?, ?)
            ON CONFLICT(type, value) DO UPDATE SET last_seen = datetime('now')
            RETURNING id
            """,
            (ioc_type, value),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row["id"])

    def get_ioc(self, ioc_id: int) -> dict | None:
        """Fetch an IOC by its primary key.

        Args:
            ioc_id: Primary key of the IOC row.

        Returns:
            Dict with IOC fields or None if not found.
        """
        cur = self._conn.execute("SELECT * FROM iocs WHERE id = ?", (ioc_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def find_ioc(self, value: str) -> dict | None:
        """Fetch an IOC by its value string.

        Args:
            value: The raw IOC value to search for.

        Returns:
            Dict with IOC fields or None if not found.
        """
        cur = self._conn.execute("SELECT * FROM iocs WHERE value = ?", (value,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Enrichment CRUD
    # ------------------------------------------------------------------

    def save_enrichment(
        self,
        ioc_id: int,
        source: str,
        severity: str,
        summary: str,
        raw_data: dict,
    ) -> int:
        """Persist an enrichment result, updating it if the source already exists.

        Args:
            ioc_id: Foreign key referencing iocs.id.
            source: Plugin/source name (e.g. 'virustotal').
            severity: Severity label string.
            summary: Human-readable finding summary.
            raw_data: Full raw response as a dict; stored as JSON.

        Returns:
            The row id of the saved enrichment.
        """
        raw_json = json.dumps(raw_data)
        cur = self._conn.execute(
            """
            INSERT INTO enrichments (ioc_id, source, severity, summary, raw_data)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ioc_id, source) DO UPDATE SET
                severity = excluded.severity,
                summary = excluded.summary,
                raw_data = excluded.raw_data,
                enriched_at = datetime('now')
            RETURNING id
            """,
            (ioc_id, source, severity, summary, raw_json),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row["id"])

    def get_enrichments(self, ioc_id: int) -> list[dict]:
        """Return all enrichment records for a given IOC.

        Args:
            ioc_id: Foreign key referencing iocs.id.

        Returns:
            List of enrichment dicts with raw_data already decoded to dict.
        """
        cur = self._conn.execute(
            "SELECT * FROM enrichments WHERE ioc_id = ? ORDER BY enriched_at",
            (ioc_id,),
        )
        rows = cur.fetchall()
        results: list[dict] = []
        for row in rows:
            entry = dict(row)
            entry["raw_data"] = json.loads(entry["raw_data"])
            results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Analysis CRUD
    # ------------------------------------------------------------------

    def save_analysis(self, ioc_id: int, model: str, summary: str) -> int:
        """Persist an AI analysis result.

        Args:
            ioc_id: Foreign key referencing iocs.id.
            model: Ollama model name used.
            summary: Full AI analysis text.

        Returns:
            The row id of the new analysis record.
        """
        cur = self._conn.execute(
            "INSERT INTO analyses (ioc_id, model, summary) VALUES (?, ?, ?) RETURNING id",
            (ioc_id, model, summary),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row["id"])

    # ------------------------------------------------------------------
    # Case CRUD
    # ------------------------------------------------------------------

    def create_case(self, name: str, description: str = "") -> int:
        """Create a new investigation case.

        Args:
            name: Short display name for the case.
            description: Optional longer description.

        Returns:
            The row id of the new case.
        """
        cur = self._conn.execute(
            "INSERT INTO cases (name, description) VALUES (?, ?) RETURNING id",
            (name, description),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row["id"])

    def list_cases(self, status: str | None = None) -> list[dict]:
        """List all cases, optionally filtered by status.

        Args:
            status: If provided, only return cases with this status.

        Returns:
            List of case dicts, each including an 'ioc_count' field.
        """
        if status is not None:
            cur = self._conn.execute(
                """
                SELECT c.*,
                       COUNT(ci.ioc_id) AS ioc_count
                FROM cases c
                LEFT JOIN case_iocs ci ON ci.case_id = c.id
                WHERE c.status = ?
                GROUP BY c.id
                ORDER BY c.created_at DESC
                """,
                (status,),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT c.*,
                       COUNT(ci.ioc_id) AS ioc_count
                FROM cases c
                LEFT JOIN case_iocs ci ON ci.case_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at DESC
                """
            )
        return [dict(row) for row in cur.fetchall()]

    def get_case(self, case_id: int) -> dict | None:
        """Fetch a case by its primary key.

        Args:
            case_id: Primary key of the case row.

        Returns:
            Case dict or None if not found.
        """
        cur = self._conn.execute(
            """
            SELECT c.*,
                   COUNT(ci.ioc_id) AS ioc_count
            FROM cases c
            LEFT JOIN case_iocs ci ON ci.case_id = c.id
            WHERE c.id = ?
            GROUP BY c.id
            """,
            (case_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def close_case(self, case_id: int) -> None:
        """Mark a case as closed.

        Args:
            case_id: Primary key of the case to close.
        """
        self._conn.execute(
            "UPDATE cases SET status = 'closed', updated_at = datetime('now') WHERE id = ?",
            (case_id,),
        )
        self._conn.commit()

    def delete_case(self, case_id: int) -> bool:
        """Delete a case and its associated data (links, notes).

        Args:
            case_id: Primary key of the case to delete.

        Returns:
            True if the case was deleted, False if not found.
        """
        cur = self._conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if cur.fetchone() is None:
            return False
        # Delete dependent rows first (FK integrity)
        self._conn.execute("DELETE FROM case_notes WHERE case_id = ?", (case_id,))
        self._conn.execute("DELETE FROM case_iocs WHERE case_id = ?", (case_id,))
        self._conn.execute("DELETE FROM email_analyses WHERE case_id = ?", (case_id,))
        self._conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        self._conn.commit()
        return True

    def update_case(
        self,
        case_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> bool:
        """Update a case's name and/or description.

        Args:
            case_id: Primary key of the case to update.
            name: New name (if provided).
            description: New description (if provided).

        Returns:
            True if the case was updated, False if not found.
        """
        cur = self._conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if cur.fetchone() is None:
            return False
        if name is not None:
            self._conn.execute(
                "UPDATE cases SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (name, case_id),
            )
        if description is not None:
            self._conn.execute(
                "UPDATE cases SET description = ?, updated_at = datetime('now') WHERE id = ?",
                (description, case_id),
            )
        self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Case-IOC links
    # ------------------------------------------------------------------

    def link_ioc_to_case(self, case_id: int, ioc_id: int, notes: str = "") -> None:
        """Associate an IOC with a case, ignoring duplicates.

        Args:
            case_id: Foreign key referencing cases.id.
            ioc_id: Foreign key referencing iocs.id.
            notes: Optional analyst notes for this specific link.
        """
        self._conn.execute(
            """
            INSERT OR IGNORE INTO case_iocs (case_id, ioc_id, notes)
            VALUES (?, ?, ?)
            """,
            (case_id, ioc_id, notes),
        )
        self._conn.execute(
            "UPDATE cases SET updated_at = datetime('now') WHERE id = ?",
            (case_id,),
        )
        self._conn.commit()

    def get_case_iocs(self, case_id: int) -> list[dict]:
        """Return all IOCs linked to a case along with their enrichments.

        Args:
            case_id: Foreign key referencing cases.id.

        Returns:
            List of dicts each containing IOC fields plus an 'enrichments' list.
        """
        cur = self._conn.execute(
            """
            SELECT i.*, ci.added_at, ci.notes AS link_notes
            FROM iocs i
            JOIN case_iocs ci ON ci.ioc_id = i.id
            WHERE ci.case_id = ?
            ORDER BY ci.added_at
            """,
            (case_id,),
        )
        iocs: list[dict] = []
        for row in cur.fetchall():
            entry = dict(row)
            entry["enrichments"] = self.get_enrichments(entry["id"])
            iocs.append(entry)
        return iocs

    # ------------------------------------------------------------------
    # Case notes
    # ------------------------------------------------------------------

    def add_case_note(self, case_id: int, content: str) -> int:
        """Append a free-text note to a case.

        Args:
            case_id: Foreign key referencing cases.id.
            content: Note text.

        Returns:
            The row id of the new note.
        """
        cur = self._conn.execute(
            "INSERT INTO case_notes (case_id, content) VALUES (?, ?) RETURNING id",
            (case_id, content),
        )
        row = cur.fetchone()
        self._conn.execute(
            "UPDATE cases SET updated_at = datetime('now') WHERE id = ?",
            (case_id,),
        )
        self._conn.commit()
        return int(row["id"])

    def get_case_notes(self, case_id: int) -> list[dict]:
        """Return all notes for a case ordered by creation time.

        Args:
            case_id: Foreign key referencing cases.id.

        Returns:
            List of note dicts.
        """
        cur = self._conn.execute(
            "SELECT * FROM case_notes WHERE case_id = ? ORDER BY created_at",
            (case_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def get_case_timeline(self, case_id: int) -> list[dict]:
        """Return all events for a case sorted by timestamp.

        Events include IOC additions, individual enrichments, and notes.

        Args:
            case_id: Foreign key referencing cases.id.

        Returns:
            List of event dicts with at least 'event_type', 'timestamp', and
            'description' keys, sorted oldest-first.
        """
        events: list[dict] = []

        # IOC additions
        cur = self._conn.execute(
            """
            SELECT i.type, i.value, ci.added_at, ci.notes AS link_notes
            FROM iocs i
            JOIN case_iocs ci ON ci.ioc_id = i.id
            WHERE ci.case_id = ?
            """,
            (case_id,),
        )
        for row in cur.fetchall():
            events.append(
                {
                    "event_type": "ioc_added",
                    "timestamp": row["added_at"],
                    "description": f"IOC added: [{row['type']}] {row['value']}",
                    "detail": row["link_notes"] or "",
                }
            )

        # Enrichments for IOCs linked to this case
        cur = self._conn.execute(
            """
            SELECT e.source, e.severity, e.summary, e.enriched_at, i.value AS ioc_value
            FROM enrichments e
            JOIN iocs i ON i.id = e.ioc_id
            JOIN case_iocs ci ON ci.ioc_id = e.ioc_id
            WHERE ci.case_id = ?
            """,
            (case_id,),
        )
        for row in cur.fetchall():
            events.append(
                {
                    "event_type": "enrichment",
                    "timestamp": row["enriched_at"],
                    "description": f"[{row['source']}] {row['ioc_value']}: {row['summary']}",
                    "detail": row["severity"],
                }
            )

        # Analyses for IOCs linked to this case
        cur = self._conn.execute(
            """
            SELECT a.model, a.summary, a.analyzed_at, i.value AS ioc_value
            FROM analyses a
            JOIN iocs i ON i.id = a.ioc_id
            JOIN case_iocs ci ON ci.ioc_id = a.ioc_id
            WHERE ci.case_id = ?
            """,
            (case_id,),
        )
        for row in cur.fetchall():
            events.append(
                {
                    "event_type": "analysis",
                    "timestamp": row["analyzed_at"],
                    "description": f"AI analysis by {row['model']}",
                    "model": row["model"],
                    "summary": row["summary"],
                    "ioc_value": row["ioc_value"],
                    "detail": row["summary"],
                }
            )

        # Case notes
        for note in self.get_case_notes(case_id):
            events.append(
                {
                    "event_type": "note",
                    "timestamp": note["created_at"],
                    "description": note["content"],
                    "detail": "",
                }
            )

        events.sort(key=lambda e: e["timestamp"])
        return events

    # ------------------------------------------------------------------
    # Email analysis CRUD
    # ------------------------------------------------------------------

    def save_email_analysis(
        self,
        result: dict,
        case_id: int | None,
        pdf_path: str | None,
    ) -> int:
        """Persist email analysis result.

        Args:
            result: Full analysis result dict produced by the email analyser.
            case_id: Optional foreign key referencing cases.id.
            pdf_path: Optional path to the generated PDF report.

        Returns:
            The row id of the new email_analyses record.
        """
        headers = result.get("headers", {})
        auth = result.get("auth", {})
        score = result.get("phishing_score", {})
        cur = self._conn.execute(
            """
            INSERT INTO email_analyses (
                case_id, file_path, file_sha256, from_addr, subject,
                analyzed_at, spf, dkim, dmarc, phishing_score,
                ai_classification, ai_confidence, ioc_count,
                attachment_count, full_result_json, pdf_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                case_id,
                result.get("file_path", ""),
                result.get("file_sha256", ""),
                headers.get("from_addr", ""),
                headers.get("subject", ""),
                result.get("analyzed_at", ""),
                auth.get("spf", "none"),
                auth.get("dkim", "none"),
                auth.get("dmarc", "none"),
                score.get("total", 0.0),
                result.get("ai_classification"),
                result.get("ai_confidence"),
                len(result.get("iocs_found", [])),
                len(result.get("attachments", [])),
                json.dumps(result, default=str),
                pdf_path,
            ),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row["id"])

    def get_email_analyses(self, case_id: int) -> list[dict]:
        """Return all email analyses linked to a case.

        Args:
            case_id: Foreign key referencing cases.id.

        Returns:
            List of analysis dicts with full_result_json already decoded,
            ordered newest-first.
        """
        cur = self._conn.execute(
            "SELECT * FROM email_analyses WHERE case_id = ? ORDER BY analyzed_at DESC",
            (case_id,),
        )
        results: list[dict] = []
        for row in cur.fetchall():
            entry = dict(row)
            try:
                entry["full_result_json"] = json.loads(entry["full_result_json"])
            except (json.JSONDecodeError, KeyError):
                pass
            results.append(entry)
        return results

    def get_email_analysis(self, analysis_id: int) -> dict | None:
        """Return a single email analysis by id.

        Args:
            analysis_id: Primary key of the email_analyses row.

        Returns:
            Analysis dict with full_result_json decoded, or None if not found.
        """
        cur = self._conn.execute(
            "SELECT * FROM email_analyses WHERE id = ?",
            (analysis_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        entry = dict(row)
        try:
            entry["full_result_json"] = json.loads(entry["full_result_json"])
        except (json.JSONDecodeError, KeyError):
            pass
        return entry

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
