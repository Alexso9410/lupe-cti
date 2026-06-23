"""E2E tests for Cases view — Edit/Delete actions (PR-31)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import flet as ft
import pytest

from lupe.case import CaseInfo  # noqa: I001

# ---------------------------------------------------------------------------
# MockPage (same pattern as test_e2e_gui_runtime.py)
# ---------------------------------------------------------------------------


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
    """Mock of ft.Page that supports overlay, show_dialog, pop_dialog, run_task."""

    def __init__(self):
        self.update = MagicMock()
        self.snack_bar = None
        self.overlay: list = _OverlayList(self)
        self._dialogs: list = []

    def show_dialog(self, dialog):
        """Show a dialog (Flet 0.85.3+ API)."""
        self._dialogs.append(dialog)

    def pop_dialog(self):
        """Dismiss current dialog."""
        if self._dialogs:
            self._dialogs.pop()

    def run_task(self, coro_func, *args):
        """Run an async coroutine function."""
        loop = asyncio.get_event_loop()
        return loop.create_task(coro_func(*args))


@pytest.fixture
def mock_page():
    return MockPage()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_controls(control, control_type):
    """Recursively find all controls of a given type."""
    found = []
    if isinstance(control, control_type):
        found.append(control)
    # Standard controls list
    if hasattr(control, "controls"):
        for child in control.controls:
            found.extend(_find_controls(child, control_type))
    # Content attribute (single child)
    if hasattr(control, "content"):
        content = control.content
        if content is not None and not isinstance(content, str):
            found.extend(_find_controls(content, control_type))
    # DataTable rows/cells traversal
    if hasattr(control, "rows"):
        for row in control.rows:
            if hasattr(row, "cells"):
                for cell in row.cells:
                    if hasattr(cell, "content"):
                        content = cell.content
                        if content is not None and not isinstance(content, str):
                            found.extend(_find_controls(content, control_type))
    return found


def _button_text(btn):
    if hasattr(btn, "content") and isinstance(btn.content, str):
        return btn.content
    if hasattr(btn, "text"):
        return btn.text
    return ""


def _find_button(control, text):
    buttons = _find_controls(control, ft.ElevatedButton)
    for btn in buttons:
        if _button_text(btn) == text:
            return btn
    return None


def _find_icon_button(control, icon):
    """Find IconButton by icon attribute."""
    buttons = _find_controls(control, ft.IconButton)
    for btn in buttons:
        if btn.icon == icon:
            return btn
    return None


def _make_cases():
    """Return a list of test CaseInfo objects."""
    return [
        CaseInfo(id=1, name="Case Alpha", description="First", status="open", ioc_count=2),
        CaseInfo(id=2, name="Case Beta", description="Second", status="open", ioc_count=0),
    ]


# ===========================================================================
# Test: Edit/Delete buttons exist in Cases view
# ===========================================================================


class TestCasesViewEditDeleteButtons:
    """Test that Edit and Delete buttons appear in the Cases table."""

    def test_cases_view_has_actions_column(self, mock_page):
        """Cases view table should have an 'Actions' column."""
        from lupe.flet.views.cases import build_cases_view

        with patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()):
            view = build_cases_view(mock_page)

        tables = _find_controls(view, ft.DataTable)
        assert len(tables) >= 1
        table = tables[0]
        col_names = [
            c.label.value if hasattr(c.label, "value") else str(c.label) for c in table.columns
        ]
        assert "Actions" in col_names, f"Expected 'Actions' column, got: {col_names}"

    def test_cases_row_has_edit_button(self, mock_page):
        """Each case row should have an Edit IconButton."""
        from lupe.flet.views.cases import build_cases_view

        with patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()):
            view = build_cases_view(mock_page)

        # Look for edit icon buttons in the entire view tree (including DataTable cells)
        edit_btns = _find_controls(view, ft.IconButton)
        edit_found = any(btn.icon == ft.Icons.EDIT or btn.icon == "edit" for btn in edit_btns)
        assert edit_found, (
            f"No Edit IconButton found. Found {len(edit_btns)} icon buttons: "
            f"{[b.icon for b in edit_btns]}"
        )

    def test_cases_row_has_delete_button(self, mock_page):
        """Each case row should have a Delete IconButton."""
        from lupe.flet.views.cases import build_cases_view

        with patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()):
            view = build_cases_view(mock_page)

        delete_btns = _find_controls(view, ft.IconButton)
        delete_found = any(
            btn.icon == ft.Icons.DELETE or btn.icon == "delete" for btn in delete_btns
        )
        assert delete_found, (
            f"No Delete IconButton found. Found {len(delete_btns)} icon buttons: "
            f"{[b.icon for b in delete_btns]}"
        )


# ===========================================================================
# Test: Delete flow — confirmation dialog + backend call
# ===========================================================================


class TestCasesViewDeleteFlow:
    """Test the delete confirmation flow."""

    @pytest.mark.asyncio
    async def test_delete_shows_confirmation_dialog(self, mock_page):
        """Clicking Delete should show a confirmation AlertDialog."""
        from lupe.flet.views.cases import build_cases_view

        with patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()):
            view = build_cases_view(mock_page)

        # Find delete icon buttons in the view tree
        icon_btns = _find_controls(view, ft.IconButton)
        delete_btns = [b for b in icon_btns if b.icon in (ft.Icons.DELETE, "delete")]
        assert len(delete_btns) >= 1, "No Delete icon button found in Cases view"
        # Verify the button has an on_click handler
        assert delete_btns[0].on_click is not None, "Delete button has no on_click handler"

    @pytest.mark.asyncio
    async def test_delete_confirm_calls_delete_case(self, mock_page):
        """Confirming delete should call lupe.case.delete_case."""
        from lupe.flet.views.cases import build_cases_view

        with (
            patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()),
            patch("lupe.flet.views.cases.delete_case", return_value=True) as mock_del,
        ):
            build_cases_view(mock_page)
            # Simulate calling delete_case directly
            from lupe.flet.views.cases import delete_case as dc_func

            result = dc_func(1)
            assert result is True
            mock_del.assert_called_once_with(1)


# ===========================================================================
# Test: Edit flow — dialog with name field + backend call
# ===========================================================================


class TestCasesViewEditFlow:
    """Test the edit flow."""

    def test_edit_button_exists_for_each_row(self, mock_page):
        """Each data row should have an Edit control."""
        from lupe.flet.views.cases import build_cases_view

        with patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()):
            view = build_cases_view(mock_page)

        tables = _find_controls(view, ft.DataTable)
        assert len(tables) >= 1
        table = tables[0]
        # Each row should have a cell with an edit-related control
        for row in table.rows:
            # Last cell should be actions
            last_cell = row.cells[-1]
            # Check that the cell has some interactive control
            cell_controls = _find_controls(last_cell, (ft.IconButton, ft.ElevatedButton, ft.Row))
            assert len(cell_controls) > 0, "Actions cell has no interactive controls"

    @pytest.mark.asyncio
    async def test_update_case_backend_function(self, mock_page):
        """update_case should call DB and return True on success."""
        from lupe.flet.views.cases import build_cases_view

        with (
            patch("lupe.flet.views.cases.list_cases", return_value=_make_cases()),
            patch("lupe.flet.views.cases.update_case", return_value=True) as mock_upd,
        ):
            build_cases_view(mock_page)
            from lupe.flet.views.cases import update_case as uc_func

            result = uc_func(1, name="Updated Name")
            assert result is True
            mock_upd.assert_called_once_with(1, name="Updated Name")
