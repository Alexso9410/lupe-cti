"""Tests for lupe.case module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lupe.case import CaseInfo, add_ioc_to_case, create_case, list_cases


@pytest.fixture
def mock_db():
    """Create a mock Database instance."""
    db = MagicMock()
    db.list_cases.return_value = [
        {
            "id": 1,
            "name": "Test Case",
            "description": "A test case",
            "status": "open",
            "ioc_count": 2,
        }
    ]
    db.create_case.return_value = 42
    db.upsert_ioc.return_value = 99
    db.link_ioc_to_case.return_value = None
    return db


class TestCaseInfo:
    """Test CaseInfo dataclass."""

    def test_case_info_fields(self):
        """CaseInfo should store all provided fields."""
        info = CaseInfo(id=1, name="Test", description="desc", status="open", ioc_count=3)
        assert info.id == 1
        assert info.name == "Test"
        assert info.description == "desc"
        assert info.status == "open"
        assert info.ioc_count == 3


class TestListCases:
    """Test list_cases function."""

    def test_list_cases_returns_case_info_objects(self, mock_db):
        """list_cases should return CaseInfo objects."""
        with patch("lupe.case._get_db", return_value=mock_db):
            result = list_cases()
        assert len(result) == 1
        assert isinstance(result[0], CaseInfo)
        assert result[0].name == "Test Case"
        assert result[0].ioc_count == 2

    def test_list_cases_passes_status_filter(self, mock_db):
        """list_cases should pass status filter to Database."""
        with patch("lupe.case._get_db", return_value=mock_db):
            list_cases(status="open")
        mock_db.list_cases.assert_called_once_with(status="open")

    def test_list_cases_returns_empty_when_no_cases(self, mock_db):
        """list_cases should return empty list when no cases exist."""
        mock_db.list_cases.return_value = []
        with patch("lupe.case._get_db", return_value=mock_db):
            result = list_cases()
        assert result == []


class TestCreateCase:
    """Test create_case function."""

    def test_create_case_returns_case_info(self, mock_db):
        """create_case should return a CaseInfo."""
        with patch("lupe.case._get_db", return_value=mock_db):
            result = create_case("New Case", "description here")
        assert isinstance(result, CaseInfo)
        assert result.id == 42
        assert result.name == "New Case"
        assert result.status == "open"

    def test_create_case_calls_db_create(self, mock_db):
        """create_case should call Database.create_case with correct args."""
        with patch("lupe.case._get_db", return_value=mock_db):
            create_case("Incident-2026-001", "Phishing campaign")
        mock_db.create_case.assert_called_once_with("Incident-2026-001", "Phishing campaign")

    def test_create_case_default_empty_description(self, mock_db):
        """create_case should default to empty description."""
        with patch("lupe.case._get_db", return_value=mock_db):
            create_case("Quick Case")
        mock_db.create_case.assert_called_once_with("Quick Case", "")


class TestAddIOCToCase:
    """Test add_ioc_to_case function."""

    def test_add_ioc_upserts_and_links(self, mock_db):
        """add_ioc_to_case should upsert IOC then link to case."""
        with patch("lupe.case._get_db", return_value=mock_db):
            result = add_ioc_to_case(1, "8.8.8.8", "ipv4", "Suspicious IP")
        assert result == 99
        mock_db.upsert_ioc.assert_called_once_with("ipv4", "8.8.8.8")
        mock_db.link_ioc_to_case.assert_called_once_with(1, 99, "Suspicious IP")

    def test_add_ioc_default_empty_notes(self, mock_db):
        """add_ioc_to_case should default to empty notes."""
        with patch("lupe.case._get_db", return_value=mock_db):
            add_ioc_to_case(1, "evil.com", "domain")
        mock_db.link_ioc_to_case.assert_called_once_with(1, 99, "")
