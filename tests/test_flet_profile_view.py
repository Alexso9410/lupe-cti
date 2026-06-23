"""Tests for Profile Flet view (PR-32)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import flet as ft
import pytest


class _OverlayList(list):
    def __init__(self, page_ref):
        super().__init__()
        self._page = page_ref

    def append(self, item):
        super().append(item)
        if isinstance(item, ft.SnackBar):
            self._page.snack_bar = item


class MockPage:
    def __init__(self):
        self.update = MagicMock()
        self.snack_bar = None
        self.overlay: list = _OverlayList(self)
        self._dialogs: list = []

    def show_dialog(self, dialog):
        self._dialogs.append(dialog)

    def pop_dialog(self):
        if self._dialogs:
            self._dialogs.pop()

    def run_task(self, coro_func, *args):
        loop = asyncio.get_event_loop()
        return loop.create_task(coro_func(*args))


@pytest.fixture
def mock_page():
    return MockPage()


def _find_controls(control, control_type):
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
    buttons = _find_controls(control, ft.ElevatedButton)
    for btn in buttons:
        if hasattr(btn, "content") and btn.content == text:
            return btn
        if hasattr(btn, "text") and btn.text == text:
            return btn
    return None


def _find_textfield(control, label):
    fields = _find_controls(control, ft.TextField)
    for f in fields:
        if f.label and label.lower() in f.label.lower():
            return f
    return None


def _find_dropdown(control):
    dropdowns = _find_controls(control, ft.Dropdown)
    return dropdowns[0] if dropdowns else None


class TestProfileViewImport:
    """Test that profile view module exists and is importable."""

    def test_profile_view_importable(self):
        """lupe.flet.views.profile module is importable."""
        from lupe.flet.views.profile import ProfileView

        assert ProfileView is not None

    def test_build_profile_view_callable(self):
        """build_profile_view function is callable."""
        from lupe.flet.views.profile import build_profile_view

        assert callable(build_profile_view)


class TestProfileViewUI:
    """Test Profile view UI components."""

    def test_profile_view_builds(self, mock_page):
        """Profile view should build without error."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default", "analyst1"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        assert isinstance(view, ft.Control)

    def test_has_profile_dropdown(self, mock_page):
        """Profile view should have a dropdown for selecting profiles."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        dropdown = _find_dropdown(view)
        assert dropdown is not None, "No Dropdown found in profile view"

    def test_has_create_field(self, mock_page):
        """Profile view should have a TextField for creating new profiles."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        field = _find_textfield(view, "profile")
        assert field is not None, "No profile name TextField found"

    def test_has_switch_button(self, mock_page):
        """Profile view should have a Switch button."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        btn = _find_button(view, "Switch")
        assert btn is not None, "No Switch button found"

    def test_has_create_button(self, mock_page):
        """Profile view should have a Create button."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        btn = _find_button(view, "Create")
        assert btn is not None, "No Create button found"

    def test_has_delete_button(self, mock_page):
        """Profile view should have a Delete button."""
        from lupe.flet.views.profile import build_profile_view

        with (
            patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
            patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
        ):
            view = build_profile_view(mock_page)
        btn = _find_button(view, "Delete")
        assert btn is not None, "No Delete button found"
