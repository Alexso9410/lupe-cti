"""Tests for case detail view data transformation helpers (PR #3)."""

from __future__ import annotations

import pytest

from lupe.db import Database


@pytest.fixture
def db(tmp_path):
    """Create a Database with temp path."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def populated_db(db):
    """Populate DB with a case, 2 IOCs, enrichments, analyses, and a note."""
    case_id = db.create_case("Incident-2026-001", "Suspicious activity investigation")

    # IOC 1 — IP with enrichment + analysis
    ioc1_id = db.upsert_ioc("ipv4", "8.8.8.8")
    db.link_ioc_to_case(case_id, ioc1_id, "Suspicious IP")
    db.save_enrichment(ioc1_id, "virustotal", "low", "Clean IP", {"clean": True})
    db.save_analysis(ioc1_id, "gemini-2.5-flash", "This IP is benign.")

    # IOC 2 — Domain with enrichment + 2 analyses
    ioc2_id = db.upsert_ioc("domain", "evil.com")
    db.link_ioc_to_case(case_id, ioc2_id)
    db.save_enrichment(ioc2_id, "urlhaus", "high", "Malware distribution", {"threat": "malware"})
    db.save_analysis(ioc2_id, "gemini-2.5-flash", "Malicious domain distributing malware.")
    db.save_analysis(ioc2_id, "gemini-2.5-pro", "Confirmed C2 infrastructure.")

    # Case note
    db.add_case_note(case_id, "Escalated to IR team.")

    return db, case_id


# ---------------------------------------------------------------------------
# Test: format_event_for_display
# ---------------------------------------------------------------------------


class TestFormatEventForDisplay:
    """Test the event formatting helper used by the detail view."""

    def test_format_enrichment_event(self):
        """Enrichment events should return source, severity, summary, timestamp."""
        from lupe.flet.views.case_detail import format_event_for_display

        event = {
            "event_type": "enrichment",
            "timestamp": "2026-07-06 10:00:00",
            "description": "[virustotal] 8.8.8.8: Clean IP",
            "detail": "low",
            "source": "virustotal",
            "summary": "Clean IP",
        }
        result = format_event_for_display(event)
        assert result["type"] == "enrichment"
        assert result["icon"] == "enrichment"
        assert result["source"] == "virustotal"
        assert result["severity"] == "low"
        assert result["summary"] == "Clean IP"
        assert result["timestamp"] == "2026-07-06 10:00:00"

    def test_format_analysis_event(self):
        """Analysis events should return model, summary, timestamp."""
        from lupe.flet.views.case_detail import format_event_for_display

        event = {
            "event_type": "analysis",
            "timestamp": "2026-07-06 10:05:00",
            "description": "AI analysis by gemini-2.5-flash",
            "model": "gemini-2.5-flash",
            "summary": "This IP is benign.",
            "ioc_value": "8.8.8.8",
            "detail": "This IP is benign.",
        }
        result = format_event_for_display(event)
        assert result["type"] == "analysis"
        assert result["icon"] == "analysis"
        assert result["model"] == "gemini-2.5-flash"
        assert result["summary"] == "This IP is benign."
        assert result["timestamp"] == "2026-07-06 10:05:00"

    def test_format_ioc_added_event(self):
        """ioc_added events should be formatted correctly."""
        from lupe.flet.views.case_detail import format_event_for_display

        event = {
            "event_type": "ioc_added",
            "timestamp": "2026-07-06 09:00:00",
            "description": "IOC added: [ipv4] 8.8.8.8",
            "detail": "Suspicious IP",
        }
        result = format_event_for_display(event)
        assert result["type"] == "ioc_added"
        assert result["icon"] == "ioc_added"
        assert "8.8.8.8" in result["summary"]

    def test_format_note_event(self):
        """Note events should be formatted correctly."""
        from lupe.flet.views.case_detail import format_event_for_display

        event = {
            "event_type": "note",
            "timestamp": "2026-07-06 11:00:00",
            "description": "Escalated to IR team.",
            "detail": "",
        }
        result = format_event_for_display(event)
        assert result["type"] == "note"
        assert result["icon"] == "note"
        assert result["summary"] == "Escalated to IR team."


# ---------------------------------------------------------------------------
# Test: build_case_detail_data
# ---------------------------------------------------------------------------


class TestBuildCaseDetailData:
    """Test the data preparation function for the detail view."""

    def test_returns_none_for_missing_case(self, populated_db):
        """Should return None when case doesn't exist."""
        from lupe.flet.views.case_detail import build_case_detail_data

        db, _ = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = build_case_detail_data(9999)
        finally:
            case_module._get_db = original

        assert result is None

    def test_returns_case_header_info(self, populated_db):
        """Should return case name, description, status, created_at."""
        from lupe.flet.views.case_detail import build_case_detail_data

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = build_case_detail_data(case_id)
        finally:
            case_module._get_db = original

        assert result is not None
        assert result["case"]["name"] == "Incident-2026-001"
        assert result["case"]["description"] == "Suspicious activity investigation"
        assert result["stats"]["ioc_count"] == 2

    def test_returns_iocs_with_formatted_events(self, populated_db):
        """Each IOC group should have formatted events."""
        from lupe.flet.views.case_detail import build_case_detail_data

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = build_case_detail_data(case_id)
        finally:
            case_module._get_db = original

        assert result is not None
        assert len(result["iocs"]) == 2

        # Check that events are formatted
        for ioc_group in result["iocs"]:
            assert "ioc" in ioc_group
            assert "events" in ioc_group
            for event in ioc_group["events"]:
                assert "type" in event
                assert "icon" in event
                assert "summary" in event
                assert "timestamp" in event

    def test_analysis_events_have_model(self, populated_db):
        """Analysis events in the detail data should include model name."""
        from lupe.flet.views.case_detail import build_case_detail_data

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = build_case_detail_data(case_id)
        finally:
            case_module._get_db = original

        assert result is not None
        evil_group = next(g for g in result["iocs"] if g["ioc"]["value"] == "evil.com")
        analysis_events = [e for e in evil_group["events"] if e["type"] == "analysis"]
        assert len(analysis_events) == 2
        models = {e["model"] for e in analysis_events}
        assert "gemini-2.5-flash" in models
        assert "gemini-2.5-pro" in models


# ---------------------------------------------------------------------------
# Test: export integration — view data works with export functions
# ---------------------------------------------------------------------------


class TestDetailViewExportIntegration:
    """Test that detail view data passes correctly to export functions."""

    def test_txt_export_with_detail_data(self, populated_db):
        """export_case_to_txt should work with CaseHistory from build_case_history."""
        from lupe.case import build_case_history
        from lupe.export.txt_export import export_case_to_txt

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        txt = export_case_to_txt(history)
        assert "Incident-2026-001" in txt
        assert "8.8.8.8" in txt
        assert "evil.com" in txt
        assert "AI ANALYSIS" in txt
        assert "gemini-2.5-flash" in txt

    def test_docx_export_with_detail_data(self, populated_db, tmp_path):
        """export_case_to_docx should work with CaseHistory from build_case_history."""
        from lupe.case import build_case_history
        from lupe.export.docx_export import export_case_to_docx

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        out_path = tmp_path / "test_report.docx"
        result_path = export_case_to_docx(history, out_path)
        assert result_path.exists()
        assert result_path.stat().st_size > 0

    def test_ioc_txt_export_with_detail_data(self, populated_db):
        """export_ioc_to_txt should work with a single IOC group from detail data."""
        from lupe.case import build_case_history
        from lupe.export.txt_export import export_ioc_to_txt

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        evil_group = next(g for g in history["iocs"] if g["ioc"]["value"] == "evil.com")
        txt = export_ioc_to_txt(evil_group, history["case"])
        assert "evil.com" in txt
        assert "AI ANALYSIS" in txt


# ---------------------------------------------------------------------------
# Test: export_case_txt_to_file / export_case_docx_to_file
# ---------------------------------------------------------------------------


class TestExportCaseToFile:
    """Test the file-export helpers used by the Flet view buttons."""

    def test_export_txt_to_file_creates_file(self, populated_db, tmp_path, monkeypatch):
        """export_case_txt_to_file should write a .txt file."""
        from lupe.flet.views.case_detail import export_case_txt_to_file

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        monkeypatch.setattr(
            "lupe.flet.views.case_detail._resolve_export_path",
            lambda name, ext, default="case": tmp_path / f"{name}{ext}",
        )
        try:
            result = export_case_txt_to_file(case_id)
        finally:
            case_module._get_db = original

        assert result is not None
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Incident-2026-001" in content
        assert "8.8.8.8" in content

    def test_export_docx_to_file_creates_file(self, populated_db, tmp_path, monkeypatch):
        """export_case_docx_to_file should write a .docx file."""
        from lupe.flet.views.case_detail import export_case_docx_to_file

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        monkeypatch.setattr(
            "lupe.flet.views.case_detail._resolve_export_path",
            lambda name, ext, default="case": tmp_path / f"{name}{ext}",
        )
        try:
            result = export_case_docx_to_file(case_id)
        finally:
            case_module._get_db = original

        assert result is not None
        assert result.exists()
        assert result.stat().st_size > 0

    def test_export_txt_returns_none_for_missing_case(self, populated_db):
        """export_case_txt_to_file should return None for nonexistent case."""
        from lupe.flet.views.case_detail import export_case_txt_to_file

        db, _ = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = export_case_txt_to_file(9999)
        finally:
            case_module._get_db = original

        assert result is None

    def test_export_ioc_txt_to_file(self, populated_db, tmp_path, monkeypatch):
        """export_ioc_txt_to_file should write a file for a single IOC."""
        from lupe.flet.views.case_detail import export_ioc_txt_to_file

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        monkeypatch.setattr(
            "lupe.flet.views.case_detail._resolve_export_path",
            lambda name, ext, default="case": tmp_path / f"{name}{ext}",
        )
        try:
            result = export_ioc_txt_to_file(case_id, "evil.com")
        finally:
            case_module._get_db = original

        assert result is not None
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "evil.com" in content

    def test_export_ioc_txt_returns_none_for_missing_ioc(self, populated_db):
        """export_ioc_txt_to_file should return None when IOC not in case."""
        from lupe.flet.views.case_detail import export_ioc_txt_to_file

        db, case_id = populated_db
        import lupe.case as case_module

        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            result = export_ioc_txt_to_file(case_id, "nonexistent.com")
        finally:
            case_module._get_db = original

        assert result is None


# ---------------------------------------------------------------------------
# Test: Flet view structure (component-level, not E2E)
# ---------------------------------------------------------------------------


class TestCaseDetailViewStructure:
    """Test that the Flet detail view builds correctly with mock data."""

    def test_detail_view_returns_column(self):
        """build_case_detail_view should return a Flet Column."""
        import flet as ft

        from lupe.flet.views.case_detail import build_case_detail_view

        detail_data = {
            "case": {
                "name": "Test",
                "description": "Desc",
                "status": "open",
                "created_at": "2026-07-06",
            },
            "iocs": [],
            "case_notes": [],
            "stats": {
                "ioc_count": 0,
                "enrichment_count": 0,
                "analysis_count": 0,
                "top_severity": "info",
            },
        }
        view = build_case_detail_view(detail_data, on_back=lambda: None)
        assert isinstance(view, ft.Column)

    def test_detail_view_with_iocs_has_timeline(self):
        """Detail view with IOCs should contain IOC value text."""
        import flet as ft

        from lupe.flet.views.case_detail import build_case_detail_view

        detail_data = {
            "case": {
                "name": "Test",
                "description": "Desc",
                "status": "open",
                "created_at": "2026-07-06",
            },
            "iocs": [
                {
                    "ioc": {"id": 1, "type": "ipv4", "value": "8.8.8.8"},
                    "events": [
                        {
                            "type": "enrichment",
                            "icon": "enrichment",
                            "source": "virustotal",
                            "severity": "low",
                            "summary": "Clean IP",
                            "timestamp": "2026-07-06 10:00",
                            "model": "",
                            "detail": "low",
                        },
                        {
                            "type": "analysis",
                            "icon": "analysis",
                            "source": "gemini-2.5-flash",
                            "severity": "",
                            "summary": "Benign IP",
                            "timestamp": "2026-07-06 10:05",
                            "model": "gemini-2.5-flash",
                            "detail": "",
                        },
                    ],
                },
            ],
            "case_notes": [],
            "stats": {
                "ioc_count": 1,
                "enrichment_count": 1,
                "analysis_count": 1,
                "top_severity": "low",
            },
        }
        view = build_case_detail_view(detail_data, on_back=lambda: None)

        # Recursively find all Text controls
        def find_texts(ctrl):
            found = []
            if isinstance(ctrl, ft.Text):
                found.append(ctrl)
            if hasattr(ctrl, "controls"):
                for c in ctrl.controls:
                    found.extend(find_texts(c))
            if (
                hasattr(ctrl, "content")
                and ctrl.content is not None
                and not isinstance(ctrl.content, str)
            ):
                found.extend(find_texts(ctrl.content))
            return found

        texts = find_texts(view)
        text_values = [t.value for t in texts if hasattr(t, "value")]
        assert any("8.8.8.8" in v for v in text_values), (
            f"IOC value not found in texts: {text_values}"
        )

    def test_detail_view_has_export_buttons(self):
        """Detail view should have Export TXT and Export DOCX buttons."""
        import flet as ft

        from lupe.flet.views.case_detail import build_case_detail_view

        detail_data = {
            "case": {
                "name": "Test",
                "description": "Desc",
                "status": "open",
                "created_at": "2026-07-06",
            },
            "iocs": [],
            "case_notes": [],
            "stats": {
                "ioc_count": 0,
                "enrichment_count": 0,
                "analysis_count": 0,
                "top_severity": "info",
            },
        }
        view = build_case_detail_view(detail_data, on_back=lambda: None)

        def find_buttons(ctrl):
            found = []
            if isinstance(ctrl, (ft.Button, ft.ElevatedButton)):
                found.append(ctrl)
            if hasattr(ctrl, "controls"):
                for c in ctrl.controls:
                    found.extend(find_buttons(c))
            if (
                hasattr(ctrl, "content")
                and ctrl.content is not None
                and not isinstance(ctrl.content, str)
            ):
                found.extend(find_buttons(ctrl.content))
            return found

        def _btn_text(btn):
            if hasattr(btn, "content") and isinstance(btn.content, str):
                return btn.content
            if hasattr(btn, "text"):
                return btn.text
            return ""

        buttons = find_buttons(view)
        button_texts = [_btn_text(b) for b in buttons]
        assert any("Export TXT" in t for t in button_texts), (
            f"Export TXT button not found: {button_texts}"
        )
        assert any("Export DOCX" in t for t in button_texts), (
            f"Export DOCX button not found: {button_texts}"
        )

    def test_detail_view_has_back_button(self):
        """Detail view should have a Back button."""
        import flet as ft

        from lupe.flet.views.case_detail import build_case_detail_view

        detail_data = {
            "case": {
                "name": "Test",
                "description": "Desc",
                "status": "open",
                "created_at": "2026-07-06",
            },
            "iocs": [],
            "case_notes": [],
            "stats": {
                "ioc_count": 0,
                "enrichment_count": 0,
                "analysis_count": 0,
                "top_severity": "info",
            },
        }
        view = build_case_detail_view(detail_data, on_back=lambda: None)

        def find_buttons(ctrl):
            found = []
            if isinstance(ctrl, (ft.ElevatedButton, ft.TextButton, ft.IconButton)):
                found.append(ctrl)
            if hasattr(ctrl, "controls"):
                for c in ctrl.controls:
                    found.extend(find_buttons(c))
            if (
                hasattr(ctrl, "content")
                and ctrl.content is not None
                and not isinstance(ctrl.content, str)
            ):
                found.extend(find_buttons(ctrl.content))
            return found

        buttons = find_buttons(view)
        has_back = any(
            (hasattr(b, "text") and "Back" in str(b.text))
            or (hasattr(b, "icon") and b.icon in (ft.Icons.ARROW_BACK, "arrow_back"))
            for b in buttons
        )
        assert has_back, "Back button not found in detail view"
