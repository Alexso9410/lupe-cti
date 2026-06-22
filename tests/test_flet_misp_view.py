"""Tests for MISP view integration with MISPClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import flet as ft
import pytest

from lupe.flet.views.misp import build_misp_view


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

    async def run_task(self, coro):
        """Execute coroutine and return result."""
        return await coro


@pytest.fixture
def mock_page():
    return MockPage()


@pytest.fixture
def misp_view(mock_page):
    return build_misp_view(mock_page)


class TestMISPViewStructure:
    """Test that MISPView has the expected UI elements."""

    def test_misp_view_is_column(self, misp_view):
        """MISP view should be a Column."""
        assert isinstance(misp_view, ft.Column)

    def test_misp_view_has_pull_button(self, misp_view):
        """MISP view should have a Pull Indicators button."""
        buttons = _find_controls(misp_view, ft.ElevatedButton)
        pull_btns = [b for b in buttons if _button_text(b) == "Pull Indicators"]
        assert len(pull_btns) == 1

    def test_misp_view_has_push_button(self, misp_view):
        """MISP view should have a Push IOC button."""
        buttons = _find_controls(misp_view, ft.ElevatedButton)
        push_btns = [b for b in buttons if _button_text(b) == "Push IOC"]
        assert len(push_btns) == 1

    def test_misp_view_has_tag_filter_field(self, misp_view):
        """MISP view should have a Tag filter TextField."""
        fields = _find_controls(misp_view, ft.TextField)
        tag_fields = [f for f in fields if f.label == "Tag filter"]
        assert len(tag_fields) == 1

    def test_misp_view_has_days_field(self, misp_view):
        """MISP view should have a Days to look back TextField."""
        fields = _find_controls(misp_view, ft.TextField)
        days_fields = [f for f in fields if f.label == "Days to look back"]
        assert len(days_fields) == 1

    def test_misp_view_has_ioc_value_field(self, misp_view):
        """MISP view should have an IOC value TextField."""
        fields = _find_controls(misp_view, ft.TextField)
        ioc_fields = [f for f in fields if f.label == "IOC value to push"]
        assert len(ioc_fields) == 1


class TestMISPViewImports:
    """Test that MISP view imports are correct."""

    def test_misp_view_importable(self):
        """MISP view is importable."""
        from lupe.flet.views.misp import build_misp_view

        assert callable(build_misp_view)

    def test_misp_view_has_mispclient_import(self):
        """MISP view module should import MISPClient."""
        import lupe.flet.views.misp as misp_module

        source = open(misp_module.__file__, encoding="utf-8").read()
        assert "MISPClient" in source

    def test_misp_view_has_load_settings_import(self):
        """MISP view module should import load_settings."""
        import lupe.flet.views.misp as misp_module

        source = open(misp_module.__file__, encoding="utf-8").read()
        assert "load_settings" in source


class TestMISPViewPullIndicators:
    """Test Pull Indicators functionality."""

    @pytest.mark.asyncio
    async def test_pull_shows_error_when_misp_not_configured(self, mock_page):
        """Pull should show SnackBar error when MISP settings are missing."""
        from lupe.flet.views.misp import build_misp_view

        with patch("lupe.flet.views.misp.load_settings", return_value={}):
            view = build_misp_view(mock_page)
            pull_btn = _find_button(view, "Pull Indicators")
            # Simulate click
            event = MagicMock()
            event.control = pull_btn
            event.page = mock_page
            await pull_btn.on_click(event)
            # Should show error snackbar
            assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_pull_calls_get_indicators(self, mock_page):
        """Pull Indicators should call MISPClient.get_indicators()."""
        from lupe.flet.views.misp import build_misp_view

        mock_client = AsyncMock()
        mock_client.get_indicators.return_value = [
            {
                "uuid": "abc-123",
                "type": "ip-dst",
                "value": "8.8.8.8",
                "timestamp": "1234567890",
                "category": "Network activity",
                "comment": "test",
            }
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("lupe.flet.views.misp.MISPClient", return_value=mock_client):
            with patch(
                "lupe.flet.views.misp.load_settings",
                return_value={"misp_url": "https://misp.test", "misp_key": "test-key"},
            ):
                view = build_misp_view(mock_page)
                pull_btn = _find_button(view, "Pull Indicators")
                event = MagicMock()
                event.control = pull_btn
                event.page = mock_page
                await pull_btn.on_click(event)
                mock_client.get_indicators.assert_called_once()


class TestMISPViewPushIOC:
    """Test Push IOC functionality."""

    @pytest.mark.asyncio
    async def test_push_shows_error_when_misp_not_configured(self, mock_page):
        """Push should show SnackBar error when MISP settings are missing."""
        from lupe.flet.views.misp import build_misp_view

        with patch("lupe.flet.views.misp.load_settings", return_value={}):
            view = build_misp_view(mock_page)
            push_btn = _find_button(view, "Push IOC")
            event = MagicMock()
            event.control = push_btn
            event.page = mock_page
            await push_btn.on_click(event)
            assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_push_calls_add_indicator(self, mock_page):
        """Push IOC should call MISPClient.add_indicator()."""
        from lupe.flet.views.misp import build_misp_view

        mock_client = AsyncMock()
        mock_client.add_indicator.return_value = "uuid-456"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("lupe.flet.views.misp.MISPClient", return_value=mock_client):
            with patch(
                "lupe.flet.views.misp.load_settings",
                return_value={"misp_url": "https://misp.test", "misp_key": "test-key"},
            ):
                view = build_misp_view(mock_page)
                # Set IOC value
                ioc_field = _find_textfield(view, "IOC value to push")
                ioc_field.value = "8.8.8.8"
                push_btn = _find_button(view, "Push IOC")
                event = MagicMock()
                event.control = push_btn
                event.page = mock_page
                await push_btn.on_click(event)
                mock_client.add_indicator.assert_called_once()


class TestMISPViewLoadingState:
    """Test loading state during async operations."""

    def test_pull_button_has_on_click_handler(self, misp_view):
        """Pull button should have an on_click handler."""
        pull_btn = _find_button(misp_view, "Pull Indicators")
        assert pull_btn is not None
        assert pull_btn.on_click is not None

    def test_push_button_has_on_click_handler(self, misp_view):
        """Push button should have an on_click handler."""
        push_btn = _find_button(misp_view, "Push IOC")
        assert push_btn is not None
        assert push_btn.on_click is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _button_text(btn):
    """Get button text from ElevatedButton."""
    # Flet ElevatedButton stores text in content
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
