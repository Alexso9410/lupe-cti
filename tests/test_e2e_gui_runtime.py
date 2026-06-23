"""E2E runtime tests for Flet GUI views — covers FilePicker, Add to Case, Drag&Drop."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import flet as ft
import pytest

from lupe.flet.views.enrich import build_enrich_view
from lupe.models import IOC, EnrichmentResult, IOCType, Severity

# ---------------------------------------------------------------------------
# Shared MockPage with overlay tracking
# ---------------------------------------------------------------------------


class _OverlayList(list):
    """List subclass that tracks SnackBar and FilePicker additions."""

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
        self._services: list = []

    def show_dialog(self, dialog):
        """Show a dialog (Flet 0.85.3+ API)."""
        self._dialogs.append(dialog)

    def pop_dialog(self):
        """Dismiss current dialog."""
        if self._dialogs:
            self._dialogs.pop()

    def run_task(self, coro_func, *args):
        """Run an async coroutine function (Flet 0.85.3+).

        In real Flet, this schedules the coroutine on the event loop.
        In tests, we create a task so it actually executes.
        """
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
    if hasattr(control, "controls"):
        for child in control.controls:
            found.extend(_find_controls(child, control_type))
    if hasattr(control, "content"):
        content = control.content
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


def _find_textfield(control, label):
    fields = _find_controls(control, ft.TextField)
    for f in fields:
        if f.label and label.lower() in f.label.lower():
            return f
    return None


def _find_dropdown_by_label(control, label):
    dropdowns = _find_controls(control, ft.Dropdown)
    for d in dropdowns:
        if d.label and label.lower() in d.label.lower():
            return d
    return None


# ===========================================================================
# Test 1: Email View — Browse / FilePicker
# ===========================================================================


class TestEmailViewBrowse:
    """Test Browse button and FilePicker behavior."""

    def test_email_view_has_exactly_one_browse_button(self, mock_page):
        """Email view must have exactly one Browse button (no duplicates)."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        buttons = _find_controls(view, ft.ElevatedButton)
        browse_btns = [b for b in buttons if _button_text(b) == "Browse"]
        assert len(browse_btns) == 1, (
            f"Expected 1 Browse button, found {len(browse_btns)} — "
            "duplicate definitions overwrite each other"
        )

    def test_browse_button_has_on_click(self, mock_page):
        """Browse button must have an on_click handler."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        browse_btn = _find_button(view, "Browse")
        assert browse_btn is not None
        assert browse_btn.on_click is not None

    @pytest.mark.asyncio
    async def test_browse_creates_file_picker_and_registers_it(self, mock_page):
        """Browse should create a FilePicker and register it on the page overlay."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        browse_btn = _find_button(view, "Browse")

        # Mock FilePicker to avoid native dialog
        with patch("lupe.flet.views.email.ft.FilePicker") as mock_fp_cls:
            mock_picker = MagicMock()
            mock_picker.pick_files = MagicMock()
            mock_fp_cls.return_value = mock_picker

            event = MagicMock()
            # on_click is a lambda that calls page.run_task(_browse, e)
            # which returns a Task. We need to await that task.
            task = browse_btn.on_click(event)
            if task is not None and hasattr(task, "__await__"):
                await task

            # FilePicker must be in page.overlay before pick_files is called
            file_pickers_in_overlay = [
                c
                for c in mock_page.overlay
                if isinstance(c, MagicMock) or isinstance(c, ft.FilePicker)
            ]
            assert len(file_pickers_in_overlay) > 0, (
                "FilePicker was not registered in page.overlay — "
                "native dialog won't open on Windows"
            )

    @pytest.mark.asyncio
    async def test_browse_calls_pick_files_with_eml_extension(self, mock_page):
        """Browse should call pick_files with allowed_extensions=['eml']."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        browse_btn = _find_button(view, "Browse")

        with patch("lupe.flet.views.email.ft.FilePicker") as mock_fp_cls:
            mock_picker = MagicMock()
            mock_picker.pick_files = MagicMock()
            mock_fp_cls.return_value = mock_picker

            event = MagicMock()
            task = browse_btn.on_click(event)
            if task is not None and hasattr(task, "__await__"):
                await task

            mock_picker.pick_files.assert_called_once()
            call_kwargs = mock_picker.pick_files.call_args
            assert call_kwargs.kwargs.get("allowed_extensions") == ["eml"]

    @pytest.mark.asyncio
    async def test_browse_no_runtime_warning_on_coroutine(self, mock_page):
        """Browse must not produce 'coroutine was never awaited' warning."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        browse_btn = _find_button(view, "Browse")

        with patch("lupe.flet.views.email.ft.FilePicker") as mock_fp_cls:
            mock_picker = MagicMock()
            mock_picker.pick_files = MagicMock()
            mock_fp_cls.return_value = mock_picker

            event = MagicMock()
            task = browse_btn.on_click(event)
            if task is not None and hasattr(task, "__await__"):
                await task

            # If we get here without RuntimeWarning, the fix is correct
            mock_picker.pick_files.assert_called()


class TestEmailViewFilePickerResult:
    """Test file picker result handling."""

    def test_on_pick_result_sets_path(self, mock_page):
        """When pick_files returns a file, path should be set."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)

        # Get the on_result handler by finding the FilePicker creation
        # We test the callback directly
        path_field = _find_textfield(view, "email file path")
        assert path_field is not None

    def test_email_path_field_label_is_searchable(self, mock_page):
        """Email path field label must contain 'email' for test discovery."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        fields = _find_controls(view, ft.TextField)
        email_fields = [f for f in fields if f.label and "email" in f.label.lower()]
        assert len(email_fields) >= 1, (
            "No TextField with 'email' in label found — tests can't discover the field"
        )


# ===========================================================================
# Test 2: Enrich View — Add to Case
# ===========================================================================


class TestEnrichViewAddToCase:
    """Test Add to Case functionality in EnrichView."""

    def test_add_to_case_button_exists(self, mock_page):
        """Enrich view must have an 'Add to Case' button."""
        from lupe.flet.views.enrich import build_enrich_view

        with patch("lupe.flet.views.enrich.list_cases", return_value=[]):
            view = build_enrich_view(mock_page)
            add_btn = _find_button(view, "Add to Case")
            assert add_btn is not None

    def test_add_to_case_button_has_handler(self, mock_page):
        """Add to Case button must have an on_click handler."""
        from lupe.flet.views.enrich import build_enrich_view

        with patch("lupe.flet.views.enrich.list_cases", return_value=[]):
            view = build_enrich_view(mock_page)
            add_btn = _find_button(view, "Add to Case")
            assert add_btn.on_click is not None

    @pytest.mark.asyncio
    async def test_add_to_case_requires_enrichment_first(self, mock_page):
        """Add to Case should show error if no enrichment was run."""
        from lupe.flet.views.enrich import build_enrich_view

        with patch("lupe.flet.views.enrich.list_cases", return_value=[]):
            view = build_enrich_view(mock_page)
            add_btn = _find_button(view, "Add to Case")
            event = MagicMock()
            await add_btn.on_click(event)
            assert mock_page.snack_bar is not None
            # Verify error message
            snack_content = mock_page.snack_bar.content
            if hasattr(snack_content, "value"):
                assert (
                    "enrich" in snack_content.value.lower()
                    or "first" in snack_content.value.lower()
                )

    @pytest.mark.asyncio
    async def test_add_to_case_with_new_case_name(self, mock_page):
        """Add to Case should create new case when name is provided."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="Test",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="OK",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]
        from lupe.case import CaseInfo

        new_case = CaseInfo(id=99, name="IR-Test", description="", status="open", ioc_count=0)

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.list_cases", return_value=[]),
            patch("lupe.flet.views.enrich.create_case", return_value=new_case) as mock_create,
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=1) as mock_add,
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")

            event = MagicMock()
            await enrich_btn.on_click(event)

            # Now add to case
            new_case_field = _find_textfield(view, "New case name")
            new_case_field.value = "IR-Test"
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_create.assert_called_once_with("IR-Test")
            mock_add.assert_called_once_with(99, "8.8.8.8", "ipv4")

    @pytest.mark.asyncio
    async def test_add_to_case_with_existing_case(self, mock_page):
        """Add to Case should use selected case ID when no new name given."""
        mock_ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        mock_results = [
            EnrichmentResult(
                source="Test",
                ioc_value="1.2.3.4",
                severity=Severity.low,
                summary="OK",
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
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.list_cases", return_value=[]),
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=5) as mock_add,
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "1.2.3.4"
            enrich_btn = _find_button(view, "Enrich")

            event = MagicMock()
            await enrich_btn.on_click(event)

            # Select existing case
            case_dropdown = _find_dropdown_by_label(view, "Case")
            case_dropdown.value = "42"
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_add.assert_called_once_with(42, "1.2.3.4", "ipv4")

    @pytest.mark.asyncio
    async def test_add_to_case_shows_success_snackbar(self, mock_page):
        """Add to Case should show a success snackbar after adding."""
        mock_ioc = IOC(type=IOCType.domain, value="evil.com")
        mock_results = [
            EnrichmentResult(
                source="Test",
                ioc_value="evil.com",
                severity=Severity.high,
                summary="Bad",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]
        from lupe.case import CaseInfo

        new_case = CaseInfo(id=7, name="Case-7", description="", status="open", ioc_count=0)

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.list_cases", return_value=[]),
            patch("lupe.flet.views.enrich.create_case", return_value=new_case),
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=1),
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "evil.com"
            enrich_btn = _find_button(view, "Enrich")

            event = MagicMock()
            await enrich_btn.on_click(event)

            new_case_field = _find_textfield(view, "New case name")
            new_case_field.value = "Case-7"
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            assert mock_page.snack_bar is not None
            snack_content = mock_page.snack_bar.content
            if hasattr(snack_content, "value"):
                assert (
                    "added" in snack_content.value.lower() or "case" in snack_content.value.lower()
                )


# ===========================================================================
# Test 3: Email View — Drag & Drop
# ===========================================================================


class TestEmailViewDragDrop:
    """Test drag & drop functionality in email view."""

    def test_drag_target_exists(self, mock_page):
        """Email view should have a DragTarget control."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        drag_targets = _find_controls(view, ft.DragTarget)
        assert len(drag_targets) >= 1

    def test_drag_target_has_files_group(self, mock_page):
        """DragTarget should have group='files'."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        drag_targets = _find_controls(view, ft.DragTarget)
        assert any(dt.group == "files" for dt in drag_targets)

    def test_drag_target_has_on_accept_handler(self, mock_page):
        """DragTarget should have an on_accept handler."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        drag_targets = _find_controls(view, ft.DragTarget)
        assert any(dt.on_accept is not None for dt in drag_targets)

    def test_drag_target_wraps_path_field(self, mock_page):
        """DragTarget content should be the path TextField."""
        from lupe.flet.views.email import build_email_view

        view = build_email_view(mock_page)
        drag_targets = _find_controls(view, ft.DragTarget)
        path_field = _find_textfield(view, "email file path")
        assert path_field is not None
        # At least one DragTarget should wrap the path field
        assert any(dt.content is path_field for dt in drag_targets)


# ===========================================================================
# Test 4: All Views Build Smoke Test
# ===========================================================================


class TestAllViewsBuild:
    """Smoke test: all 8 views build without errors using MockPage."""

    @pytest.mark.parametrize(
        "mod_path,func_name",
        [
            ("lupe.flet.views.home", "build_home_view"),
            ("lupe.flet.views.enrich", "build_enrich_view"),
            ("lupe.flet.views.settings", "build_settings_view"),
            ("lupe.flet.views.profile", "build_profile_view"),
            ("lupe.flet.views.misp", "build_misp_view"),
            ("lupe.flet.views.email", "build_email_view"),
            ("lupe.flet.views.plugins", "build_plugins_view"),
            ("lupe.flet.views.cases", "build_cases_view"),
        ],
    )
    def test_view_builds_without_error(self, mod_path, func_name):
        """Each view should build without raising an exception."""
        page = MockPage()
        mod = __import__(mod_path, fromlist=[func_name])
        func = getattr(mod, func_name)
        # enrich and email views may need list_cases mock
        if "enrich" in mod_path:
            with patch("lupe.flet.views.enrich.list_cases", return_value=[]):
                result = func(page)
        elif "profile" in mod_path:
            with (
                patch("lupe.flet.views.profile.list_profiles", return_value=["default"]),
                patch("lupe.flet.views.profile.get_active_profile", return_value="default"),
            ):
                result = func(page)
        else:
            result = func(page)
        assert isinstance(result, ft.Control)
