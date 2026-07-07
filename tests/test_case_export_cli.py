"""Tests for CLI `case export` subcommand."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lupe.cli import app

runner = CliRunner()


@pytest.fixture
def mock_db_for_export():
    """Create a mock Database with case data for export testing."""
    db = MagicMock()
    db.get_case.return_value = {
        "id": 1,
        "name": "Test Case",
        "description": "A test",
        "status": "open",
        "created_at": "2026-07-06",
        "updated_at": "2026-07-06",
        "ioc_count": 1,
    }
    db.get_case_iocs.return_value = [
        {
            "id": 1,
            "type": "ipv4",
            "value": "8.8.8.8",
            "added_at": "2026-07-06",
            "link_notes": "",
            "enrichments": [
                {
                    "id": 1,
                    "ioc_id": 1,
                    "source": "virustotal",
                    "severity": "info",
                    "summary": "Clean",
                    "raw_data": {"clean": True},
                    "enriched_at": "2026-07-06",
                }
            ],
        }
    ]
    db.get_case_timeline.return_value = [
        {
            "event_type": "ioc_added",
            "timestamp": "2026-07-06 10:00:00",
            "description": "IOC added: [ipv4] 8.8.8.8",
            "detail": "",
        },
        {
            "event_type": "enrichment",
            "timestamp": "2026-07-06 10:01:00",
            "description": "[virustotal] 8.8.8.8: Clean",
            "detail": "info",
            "ioc_value": "8.8.8.8",
            "source": "virustotal",
            "severity": "info",
            "summary": "Clean",
        },
        {
            "event_type": "analysis",
            "timestamp": "2026-07-06 10:02:00",
            "description": "AI analysis by gemini-2.5-flash",
            "model": "gemini-2.5-flash",
            "summary": "Benign IP.",
            "ioc_value": "8.8.8.8",
        },
    ]
    db.get_case_notes.return_value = []
    db.find_ioc.return_value = {"id": 1, "type": "ipv4", "value": "8.8.8.8"}
    return db


class TestCaseExportCommand:
    """Test `lupe case export` CLI command."""

    def test_export_txt_creates_file(self, mock_db_for_export, tmp_path):
        """case export --format txt should create a .txt file."""
        output = tmp_path / "report.txt"
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            result = runner.invoke(
                app, ["case", "export", "1", "--format", "txt", "--output", str(output)]
            )
        assert result.exit_code == 0
        assert output.exists()

    def test_export_docx_creates_file(self, mock_db_for_export, tmp_path):
        """case export --format docx should create a .docx file."""
        output = tmp_path / "report.docx"
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            result = runner.invoke(
                app, ["case", "export", "1", "--format", "docx", "--output", str(output)]
            )
        assert result.exit_code == 0
        assert output.exists()

    def test_export_default_txt(self, mock_db_for_export, tmp_path):
        """case export without --format should default to txt."""
        output = tmp_path / "report.txt"
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            result = runner.invoke(app, ["case", "export", "1", "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_export_auto_filename(self, mock_db_for_export, tmp_path, monkeypatch):
        """case export without --output should auto-generate filename."""
        monkeypatch.chdir(tmp_path)
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            result = runner.invoke(app, ["case", "export", "1", "--format", "txt"])
        assert result.exit_code == 0

    def test_export_nonexistent_case(self, mock_db_for_export):
        """case export for nonexistent case should exit with error."""
        mock_db_for_export.get_case.return_value = None
        with patch("lupe.cli._get_db", return_value=mock_db_for_export):
            result = runner.invoke(app, ["case", "export", "999"])
        assert result.exit_code == 1

    def test_export_prints_path(self, mock_db_for_export, tmp_path):
        """case export should print the output file path."""
        output = tmp_path / "report.txt"
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            result = runner.invoke(
                app, ["case", "export", "1", "--format", "txt", "--output", str(output)]
            )
        # Rich may wrap the path; check the filename is present
        assert "report.txt" in result.output

    def test_export_ioc_flag(self, mock_db_for_export, tmp_path):
        """case export --ioc <value> should export only that IOC."""
        output = tmp_path / "ioc_report.txt"
        with (
            patch("lupe.cli._get_db", return_value=mock_db_for_export),
            patch("lupe.case._get_db", return_value=mock_db_for_export),
        ):
            args = [
                "case", "export", "1", "--format", "txt",
                "--ioc", "8.8.8.8", "--output", str(output),
            ]
            result = runner.invoke(app, args)
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "8.8.8.8" in content
