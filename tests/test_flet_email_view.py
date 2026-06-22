"""Tests for Email view with file picker and analyzer integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import flet as ft
import pytest

from lupe.flet.views.email import build_email_view


class _OverlayList(list):
    """List subclass that tracks SnackBar additions."""

    def __init__(self, page_ref):
        super().__init__()
        self._page = page_ref

    def append(self, item):
        super().append(item)
        if isinstance(item, ft.SnackBar):
            self._page.snack_bar = item


class MockPage:
    """Minimal mock of ft.Page for testing views."""

    def __init__(self):
        self.update = MagicMock()
        self.snack_bar = None
        self.overlay: list = _OverlayList(self)

    def show_snack_bar(self, snack_bar):
        self.snack_bar = snack_bar


@pytest.fixture
def mock_page():
    return MockPage()


@pytest.fixture
def email_view(mock_page):
    return build_email_view(mock_page)


class TestEmailViewStructure:
    """Test that EmailView has the expected UI elements."""

    def test_email_view_is_column(self, email_view):
        """Email view should be a Column."""
        assert isinstance(email_view, ft.Column)

    def test_email_view_has_browse_button(self, email_view):
        """Email view should have a Browse button."""
        buttons = _find_controls(email_view, ft.ElevatedButton)
        browse_btns = [b for b in buttons if _button_text(b) == "Browse"]
        assert len(browse_btns) == 1

    def test_email_view_has_analyze_button(self, email_view):
        """Email view should have an Analyze Email button."""
        buttons = _find_controls(email_view, ft.ElevatedButton)
        analyze_btns = [b for b in buttons if _button_text(b) == "Analyze Email"]
        assert len(analyze_btns) == 1

    def test_email_view_has_file_path_field(self, email_view):
        """Email view should have a file path TextField."""
        fields = _find_controls(email_view, ft.TextField)
        path_fields = [f for f in fields if f.label == "Email file path"]
        assert len(path_fields) == 1

    def test_email_view_has_markdown_output(self, email_view):
        """Email view should have a Markdown output area."""
        md_controls = _find_controls(email_view, ft.Markdown)
        assert len(md_controls) >= 1


class TestEmailViewImports:
    """Test that Email view imports are correct."""

    def test_email_view_importable(self):
        """Email view is importable."""
        from lupe.flet.views.email import build_email_view

        assert callable(build_email_view)

    def test_email_view_has_parse_eml_import(self):
        """Email view module should import parse_eml."""
        import lupe.flet.views.email as email_module

        source = open(email_module.__file__, encoding="utf-8").read()
        assert "parse_eml" in source

    def test_email_view_has_analyze_email_import(self):
        """Email view module should import analyze_email."""
        import lupe.flet.views.email as email_module

        source = open(email_module.__file__, encoding="utf-8").read()
        assert "analyze_email" in source


class TestEmailViewAnalyze:
    """Test Analyze Email functionality."""

    @pytest.mark.asyncio
    async def test_analyze_shows_error_when_no_file_selected(self, mock_page):
        """Analyze should show error when no file is selected."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        analyze_btn = _find_button(view, "Analyze Email")
        event = MagicMock()
        event.control = analyze_btn
        event.page = mock_page
        await analyze_btn.on_click(event)
        assert mock_page.snack_bar is not None

    def test_analyze_button_has_on_click_handler(self, email_view):
        """Analyze button should have an on_click handler."""
        analyze_btn = _find_button(email_view, "Analyze Email")
        assert analyze_btn is not None
        assert analyze_btn.on_click is not None

    def test_browse_button_has_on_click_handler(self, email_view):
        """Browse button should have an on_click handler."""
        browse_btn = _find_button(email_view, "Browse")
        assert browse_btn is not None
        assert browse_btn.on_click is not None


class TestEmailViewNavigation:
    """Test that Email view is registered in app navigation."""

    def test_email_view_in_nav_items(self):
        """Email should be in the app's navigation items."""
        from lupe.flet.app import _NAV_ITEMS

        nav_names = [name for name, _, _ in _NAV_ITEMS]
        assert "email" in nav_names

    def test_email_view_imported_in_app(self):
        """Email view builder should be imported in app.py."""
        import lupe.flet.app as app_module

        source = open(app_module.__file__).read()
        assert "build_email_view" in source


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
