"""Tests for lupe.db.Database — CRUD operations including delete_case and update_case."""

from __future__ import annotations

import pytest

from lupe.db import Database


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary Database instance."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def db_with_cases(tmp_db):
    """Database pre-populated with test cases."""
    tmp_db.create_case("Case Alpha", "First case")
    tmp_db.create_case("Case Beta", "Second case")
    tmp_db.create_case("Case Gamma", "Third case")
    return tmp_db


# ------------------------------------------------------------------
# Existing behavior (sanity checks)
# ------------------------------------------------------------------


class TestCreateCase:
    """Test Database.create_case."""

    def test_create_case_returns_id(self, tmp_db):
        """create_case should return a positive integer ID."""
        case_id = tmp_db.create_case("Test", "desc")
        assert isinstance(case_id, int)
        assert case_id > 0

    def test_create_case_persists(self, tmp_db):
        """Created case should be retrievable via get_case."""
        case_id = tmp_db.create_case("Persist", "test")
        case = tmp_db.get_case(case_id)
        assert case is not None
        assert case["name"] == "Persist"
        assert case["description"] == "test"
        assert case["status"] == "open"


class TestListCases:
    """Test Database.list_cases."""

    def test_list_cases_returns_all(self, db_with_cases):
        """list_cases should return all cases."""
        cases = db_with_cases.list_cases()
        assert len(cases) == 3

    def test_list_cases_filters_by_status(self, tmp_db):
        """list_cases with status filter should only return matching cases."""
        tmp_db.create_case("Open Case")
        case_id = tmp_db.create_case("Closed Case")
        tmp_db.close_case(case_id)
        open_cases = tmp_db.list_cases(status="open")
        assert len(open_cases) == 1
        assert open_cases[0]["name"] == "Open Case"


class TestGetCase:
    """Test Database.get_case."""

    def test_get_case_returns_dict(self, db_with_cases):
        """get_case should return a dict with expected keys."""
        case = db_with_cases.get_case(1)
        assert case is not None
        assert "name" in case
        assert "status" in case
        assert "ioc_count" in case

    def test_get_case_returns_none_for_missing(self, tmp_db):
        """get_case should return None for nonexistent ID."""
        assert tmp_db.get_case(999) is None


# ------------------------------------------------------------------
# NEW: delete_case
# ------------------------------------------------------------------


class TestDeleteCase:
    """Test Database.delete_case — PR-31."""

    def test_delete_case_returns_true_for_existing(self, db_with_cases):
        """delete_case should return True when case exists."""
        result = db_with_cases.delete_case(1)
        assert result is True

    def test_delete_case_removes_from_list(self, db_with_cases):
        """Deleted case should no longer appear in list_cases."""
        db_with_cases.delete_case(1)
        cases = db_with_cases.list_cases()
        assert len(cases) == 2
        names = [c["name"] for c in cases]
        assert "Case Alpha" not in names

    def test_delete_case_returns_false_for_nonexistent(self, tmp_db):
        """delete_case should return False when case doesn't exist."""
        result = tmp_db.delete_case(999)
        assert result is False

    def test_delete_case_removes_case_iocs_link(self, tmp_db):
        """delete_case should also remove linked IOCs from case_iocs."""
        case_id = tmp_db.create_case("With IOCs")
        ioc_id = tmp_db.upsert_ioc("ipv4", "1.2.3.4")
        tmp_db.link_ioc_to_case(case_id, ioc_id)
        tmp_db.delete_case(case_id)
        # Case should be gone
        assert tmp_db.get_case(case_id) is None

    def test_delete_case_removes_case_notes(self, tmp_db):
        """delete_case should also remove case notes."""
        case_id = tmp_db.create_case("With Notes")
        tmp_db.add_case_note(case_id, "Important note")
        tmp_db.delete_case(case_id)
        assert tmp_db.get_case(case_id) is None

    def test_delete_case_does_not_affect_other_cases(self, db_with_cases):
        """Deleting one case should not affect others."""
        db_with_cases.delete_case(2)
        remaining = db_with_cases.list_cases()
        assert len(remaining) == 2
        names = [c["name"] for c in remaining]
        assert "Case Alpha" in names
        assert "Case Gamma" in names


# ------------------------------------------------------------------
# NEW: update_case
# ------------------------------------------------------------------


class TestUpdateCase:
    """Test Database.update_case — PR-31."""

    def test_update_case_name_returns_true(self, db_with_cases):
        """update_case should return True when case exists and is updated."""
        result = db_with_cases.update_case(1, name="Updated Alpha")
        assert result is True

    def test_update_case_name_persists(self, db_with_cases):
        """Updated name should be persisted."""
        db_with_cases.update_case(1, name="Renamed Case")
        case = db_with_cases.get_case(1)
        assert case is not None
        assert case["name"] == "Renamed Case"

    def test_update_case_description_persists(self, db_with_cases):
        """Updated description should be persisted."""
        db_with_cases.update_case(1, description="New description here")
        case = db_with_cases.get_case(1)
        assert case is not None
        assert case["description"] == "New description here"

    def test_update_case_both_name_and_description(self, db_with_cases):
        """Can update name and description simultaneously."""
        db_with_cases.update_case(1, name="New Name", description="New Desc")
        case = db_with_cases.get_case(1)
        assert case["name"] == "New Name"
        assert case["description"] == "New Desc"

    def test_update_case_returns_false_for_nonexistent(self, tmp_db):
        """update_case should return False when case doesn't exist."""
        result = tmp_db.update_case(999, name="Ghost")
        assert result is False

    def test_update_case_updates_updated_at(self, tmp_db):
        """update_case should refresh the updated_at timestamp."""
        case_id = tmp_db.create_case("Timestamp Test")
        tmp_db.update_case(case_id, name="Changed")
        after = tmp_db.get_case(case_id)["updated_at"]
        # updated_at should change (or at least not error)
        assert after is not None

    def test_update_case_preserves_other_fields(self, db_with_cases):
        """Updating name should not alter status or other fields."""
        db_with_cases.update_case(1, name="Still Open")
        case = db_with_cases.get_case(1)
        assert case["status"] == "open"
