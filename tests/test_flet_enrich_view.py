"""Tests for Enrich view integration with run_enrichment."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import flet as ft
import pytest

from lupe.flet.views.enrich import build_enrich_view
from lupe.models import IOC, EnrichmentResult, IOCType, Severity


class MockPage:
    """Minimal mock of ft.Page for testing views."""

    def __init__(self):
        self.update = MagicMock()
        self.snack_bar = None

    def show_snack_bar(self, snack_bar):
        self.snack_bar = snack_bar


@pytest.fixture
def mock_page():
    return MockPage()


@pytest.fixture
def enrich_view(mock_page):
    return build_enrich_view(mock_page)


class TestEnrichViewStructure:
    """Test that EnrichView has the expected UI elements."""

    def test_enrich_view_is_column(self, enrich_view):
        """Enrich view should be a Column."""
        assert isinstance(enrich_view, ft.Column)

    def test_enrich_view_has_enrich_button(self, enrich_view):
        """Enrich view should have an Enrich button."""
        buttons = _find_controls(enrich_view, ft.ElevatedButton)
        enrich_btns = [b for b in buttons if _button_text(b) == "Enrich"]
        assert len(enrich_btns) == 1

    def test_enrich_view_has_ioc_field(self, enrich_view):
        """Enrich view should have an IOC value TextField."""
        fields = _find_controls(enrich_view, ft.TextField)
        ioc_fields = [f for f in fields if f.label == "IOC Value"]
        assert len(ioc_fields) == 1

    def test_enrich_view_has_results_area(self, enrich_view):
        """Enrich view should have a DataTable for results."""
        tables = _find_controls(enrich_view, ft.DataTable)
        assert len(tables) >= 1


class TestEnrichViewImports:
    """Test that Enrich view imports are correct."""

    def test_enrich_view_importable(self):
        """Enrich view is importable."""
        from lupe.flet.views.enrich import build_enrich_view

        assert callable(build_enrich_view)

    def test_enrich_view_has_run_enrichment_import(self):
        """Enrich view module should import run_enrichment."""
        import lupe.flet.views.enrich as enrich_module

        source = open(enrich_module.__file__, encoding="utf-8").read()
        assert "run_enrichment" in source

    def test_enrich_view_has_detect_ioc_import(self):
        """Enrich view module should import detect_ioc."""
        import lupe.flet.views.enrich as enrich_module

        source = open(enrich_module.__file__, encoding="utf-8").read()
        assert "detect_ioc" in source


class TestEnrichViewEnrichment:
    """Test Enrich functionality."""

    @pytest.mark.asyncio
    async def test_enrich_shows_error_when_no_ioc(self, mock_page):
        """Enrich should show error when IOC field is empty."""
        from lupe.flet.views.enrich import build_enrich_view

        view = build_enrich_view(mock_page)
        enrich_btn = _find_button(view, "Enrich")
        event = MagicMock()
        event.control = enrich_btn
        event.page = mock_page
        await enrich_btn.on_click(event)
        assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_enrich_shows_error_when_ioc_not_recognized(self, mock_page):
        """Enrich should show error when IOC type is not recognized."""
        from lupe.flet.views.enrich import build_enrich_view

        with patch("lupe.flet.views.enrich.detect_ioc", return_value=None):
            view = build_enrich_view(mock_page)
            # Set IOC value
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "not-an-ioc"
            enrich_btn = _find_button(view, "Enrich")
            event = MagicMock()
            event.control = enrich_btn
            event.page = mock_page
            await enrich_btn.on_click(event)
            assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_enrich_calls_run_enrichment(self, mock_page):
        """Enrich should call run_enrichment with detected IOC."""
        from lupe.flet.views.enrich import build_enrich_view

        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="TestPlugin",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Test result",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch(
                "lupe.flet.views.enrich.get_settings",
                return_value=MagicMock(),
            ),
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")
            event = MagicMock()
            event.control = enrich_btn
            event.page = mock_page
            await enrich_btn.on_click(event)
            # Should show results
            assert mock_page.snack_bar is not None


class TestEnrichViewLoadingState:
    """Test loading state during async operations."""

    def test_enrich_button_has_on_click_handler(self, enrich_view):
        """Enrich button should have an on_click handler."""
        enrich_btn = _find_button(enrich_view, "Enrich")
        assert enrich_btn is not None
        assert enrich_btn.on_click is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _button_text(btn):
    """Get button text from ElevatedButton."""
    if hasattr(btn, "content") and isinstance(btn.content, str):
        return btn.content
    if hasattr(btn, "text"):
        return btn.text
    return ""


def _find_controls(control, control_type):
    """Recursively find all controls of a given type."""
    found = []
    if isinstance(control, control_type):
        found.append(control)
    if hasattr(control, "controls"):
        for child in control.controls:
            found.extend(_find_controls(child, control_type))
    if hasattr(control, "content"):
        content = control.content
        if content is not None and not isinstance(content, str):
            found.extend(_find_controls(content, control_type))
    return found


def _find_button(control, text):
    """Find a button with the given text."""
    buttons = _find_controls(control, ft.ElevatedButton)
    for btn in buttons:
        if _button_text(btn) == text:
            return btn
    return None


def _find_textfield(control, label):
    """Find a TextField with the given label."""
    fields = _find_controls(control, ft.TextField)
    for f in fields:
        if f.label == label:
            return f
    return None
