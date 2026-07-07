"""Tests for build_case_history() — timeline with analysis events grouped by IOC."""

from __future__ import annotations

import pytest

from lupe.db import Database


@pytest.fixture
def db(tmp_path):
    """Create a Database with in-memory-like temp path."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def populated_db(db):
    """Populate DB with a case, 2 IOCs, enrichments, analyses, and a note."""
    case_id = db.create_case("Test Case", "A test investigation")

    # IOC 1
    ioc1_id = db.upsert_ioc("ipv4", "8.8.8.8")
    db.link_ioc_to_case(case_id, ioc1_id, "Suspicious IP")
    db.save_enrichment(ioc1_id, "virustotal", "low", "Clean IP", {"clean": True})
    db.save_analysis(ioc1_id, "gemini-2.5-flash", "This IP is benign.")

    # IOC 2
    ioc2_id = db.upsert_ioc("domain", "evil.com")
    db.link_ioc_to_case(case_id, ioc2_id)
    db.save_enrichment(ioc2_id, "urlhaus", "high", "Malware distribution", {"threat": "malware"})
    db.save_analysis(ioc2_id, "gemini-2.5-flash", "Malicious domain distributing malware.")
    db.save_analysis(ioc2_id, "gemini-2.5-pro", "Confirmed C2 infrastructure.")

    # Case note
    db.add_case_note(case_id, "Escalated to IR team.")

    return db, case_id


class TestTimelineAnalysisEvents:
    """Test that get_case_timeline returns analysis event_type."""

    def test_timeline_includes_analysis_events(self, populated_db):
        """Timeline should include event_type='analysis' from analyses table."""
        db, case_id = populated_db
        timeline = db.get_case_timeline(case_id)
        analysis_events = [e for e in timeline if e["event_type"] == "analysis"]
        assert len(analysis_events) == 3  # 1 for IOC1 + 2 for IOC2

    def test_analysis_event_has_model_and_summary(self, populated_db):
        """Each analysis event should include model and summary."""
        db, case_id = populated_db
        timeline = db.get_case_timeline(case_id)
        analysis_events = [e for e in timeline if e["event_type"] == "analysis"]
        for event in analysis_events:
            assert "model" in event
            assert "summary" in event
            assert len(event["model"]) > 0
            assert len(event["summary"]) > 0

    def test_analysis_event_has_ioc_value(self, populated_db):
        """Analysis events should reference the IOC value."""
        db, case_id = populated_db
        timeline = db.get_case_timeline(case_id)
        analysis_events = [e for e in timeline if e["event_type"] == "analysis"]
        ioc_values = {e["ioc_value"] for e in analysis_events}
        assert "8.8.8.8" in ioc_values
        assert "evil.com" in ioc_values

    def test_backward_compat_existing_events(self, populated_db):
        """Existing event types (ioc_added, enrichment, note) still present."""
        db, case_id = populated_db
        timeline = db.get_case_timeline(case_id)
        types = {e["event_type"] for e in timeline}
        assert "ioc_added" in types
        assert "enrichment" in types
        assert "note" in types
        assert "analysis" in types

    def test_timeline_chronological_order(self, populated_db):
        """All events should be sorted by timestamp ascending."""
        db, case_id = populated_db
        timeline = db.get_case_timeline(case_id)
        timestamps = [e["timestamp"] for e in timeline]
        assert timestamps == sorted(timestamps)


class TestCaseHistoryGrouping:
    """Test that build_case_history groups events by IOC."""

    def test_case_history_structure(self, populated_db):
        """build_case_history should return a dict with case, iocs, case_notes, stats."""
        from lupe.case import build_case_history

        db, case_id = populated_db
        # Patch _get_db to return our test db
        import lupe.case as case_module
        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        assert "case" in history
        assert "iocs" in history
        assert "case_notes" in history
        assert "stats" in history

    def test_case_history_iocs_grouped(self, populated_db):
        """Each IOC should have its own entry with events list."""
        from lupe.case import build_case_history

        db, case_id = populated_db
        import lupe.case as case_module
        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        assert len(history["iocs"]) == 2
        for ioc_group in history["iocs"]:
            assert "ioc" in ioc_group
            assert "events" in ioc_group
            assert len(ioc_group["events"]) > 0

    def test_case_history_analysis_in_ioc_events(self, populated_db):
        """Analysis events should appear in the IOC's events list."""
        from lupe.case import build_case_history

        db, case_id = populated_db
        import lupe.case as case_module
        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        # Find the evil.com IOC group
        evil_ioc = next(g for g in history["iocs"] if g["ioc"]["value"] == "evil.com")
        analysis_events = [e for e in evil_ioc["events"] if e["event_type"] == "analysis"]
        assert len(analysis_events) == 2

    def test_case_history_stats(self, populated_db):
        """Stats should include counts."""
        from lupe.case import build_case_history

        db, case_id = populated_db
        import lupe.case as case_module
        original = case_module._get_db
        case_module._get_db = lambda: db
        try:
            history = build_case_history(case_id)
        finally:
            case_module._get_db = original

        stats = history["stats"]
        assert stats["ioc_count"] == 2
        assert stats["enrichment_count"] == 2
        assert stats["analysis_count"] == 3
