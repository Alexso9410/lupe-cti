"""Tests for Enrich view integration with run_enrichment, AI Analysis, and Add to case."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import flet as ft
import pytest

from lupe.flet.views.enrich import build_enrich_view
from lupe.models import IOC, EnrichmentResult, IOCType, Severity


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
# AI Analysis Tests (PR-27)
# ---------------------------------------------------------------------------


class TestAIAnalysisPanel:
    """Test AI Analysis panel in EnrichView."""

    def test_enrich_view_has_ai_provider_dropdown(self, enrich_view):
        """Enrich view should have an AI provider Dropdown."""
        dropdowns = _find_controls(enrich_view, ft.Dropdown)
        ai_dropdowns = [d for d in dropdowns if d.label and "provider" in d.label.lower()]
        assert len(ai_dropdowns) >= 1

    def test_enrich_view_has_analyze_with_ai_button(self, enrich_view):
        """Enrich view should have an 'Analyze with AI' button."""
        buttons = _find_controls(enrich_view, ft.ElevatedButton)
        ai_btns = [b for b in buttons if _button_text(b) == "Analyze with AI"]
        assert len(ai_btns) == 1

    def test_enrich_view_has_ai_markdown_output(self, enrich_view):
        """Enrich view should have a Markdown widget for AI output."""
        mds = _find_controls(enrich_view, ft.Markdown)
        assert len(mds) >= 1

    def test_ai_analysis_panel_hidden_before_enrichment(self, enrich_view):
        """AI Analysis panel should be hidden before enrichment runs."""
        # Find the AI Analysis header text
        texts = _find_controls(enrich_view, ft.Text)
        ai_header = [t for t in texts if t.value == "AI Analysis"]
        assert len(ai_header) == 1
        # The parent Container should be hidden
        # We check the Container wrapping the AI panel
        containers = _find_controls(enrich_view, ft.Container)
        ai_containers = [
            c
            for c in containers
            if hasattr(c, "content")
            and c.content is not None
            and not isinstance(c.content, str)
            and any(
                isinstance(ctrl, ft.Text) and ctrl.value == "AI Analysis"
                for ctrl in _find_controls(c, ft.Text)
            )
        ]
        assert len(ai_containers) == 1
        assert ai_containers[0].visible is False

    def test_ai_analyze_button_has_on_click_handler(self, enrich_view):
        """Analyze with AI button should have an on_click handler."""
        ai_btn = _find_button(enrich_view, "Analyze with AI")
        assert ai_btn is not None
        assert ai_btn.on_click is not None


class TestAIAnalysisPromptGeneration:
    """Test that the AI prompt includes required sections."""

    def test_system_prompt_includes_risk_score_section(self):
        """AI system prompt should include risk score section."""
        from lupe.flet.views.enrich import _build_ai_system_prompt

        prompt = _build_ai_system_prompt()
        assert "Puntuación de riesgo" in prompt

    def test_system_prompt_includes_mitre_attack_section(self):
        """AI system prompt should include MITRE ATT&CK section."""
        from lupe.flet.views.enrich import _build_ai_system_prompt

        prompt = _build_ai_system_prompt()
        assert "MITRE ATT&CK" in prompt

    def test_system_prompt_includes_evaluation_section(self):
        """AI system prompt should include evaluation section."""
        from lupe.flet.views.enrich import _build_ai_system_prompt

        prompt = _build_ai_system_prompt()
        assert "Evaluación" in prompt

    def test_system_prompt_includes_recommended_actions(self):
        """AI system prompt should include recommended actions section."""
        from lupe.flet.views.enrich import _build_ai_system_prompt

        prompt = _build_ai_system_prompt()
        assert "Acciones recomendadas" in prompt

    def test_user_prompt_contains_ioc_value(self):
        """AI user prompt should contain the IOC value."""
        from lupe.flet.views.enrich import _build_ai_prompt

        prompt = _build_ai_prompt("evil.com", "domain", "data")
        assert "evil.com" in prompt

    def test_user_prompt_contains_enrichment_results(self):
        """AI user prompt should contain the enrichment results table."""
        from lupe.flet.views.enrich import _build_ai_prompt

        results = "TestPlugin | Malicious | high"
        prompt = _build_ai_prompt("8.8.8.8", "ipv4", results)
        assert "TestPlugin" in prompt


class TestAIAnalysisExecution:
    """Test AI analysis click handler."""

    @pytest.mark.asyncio
    async def test_analyze_with_ai_calls_provider_generate(self, mock_page):
        """Analyze with AI should call provider.generate()."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="TestPlugin",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Clean",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="## Risk: 2/10\nLow risk IP.")

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.get_provider", return_value=mock_provider),
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")

            # Enrich first
            event = MagicMock()
            await enrich_btn.on_click(event)

            # Now find and click AI button
            ai_btn = _find_button(view, "Analyze with AI")
            await ai_btn.on_click(event)

            mock_provider.generate.assert_called_once()
            call_kwargs = mock_provider.generate.call_args
            assert "system" in call_kwargs.kwargs or len(call_kwargs.args) > 1

    @pytest.mark.asyncio
    async def test_analyze_with_ai_shows_error_when_no_enrichment(self, mock_page):
        """Analyze with AI should show error when no enrichment results exist."""
        view = build_enrich_view(mock_page)
        ai_btn = _find_button(view, "Analyze with AI")
        event = MagicMock()
        await ai_btn.on_click(event)
        assert mock_page.snack_bar is not None


# ---------------------------------------------------------------------------
# Add to Case Tests (PR-27)
# ---------------------------------------------------------------------------


class TestAddToCasePanel:
    """Test Add to Case panel in EnrichView."""

    def test_enrich_view_has_case_dropdown(self, enrich_view):
        """Enrich view should have a case selection Dropdown."""
        dropdowns = _find_controls(enrich_view, ft.Dropdown)
        case_dropdowns = [d for d in dropdowns if d.label and "case" in d.label.lower()]
        assert len(case_dropdowns) >= 1

    def test_enrich_view_has_new_case_field(self, enrich_view):
        """Enrich view should have a 'New case name' TextField."""
        fields = _find_controls(enrich_view, ft.TextField)
        new_case_fields = [f for f in fields if f.label and "new case" in f.label.lower()]
        assert len(new_case_fields) == 1

    def test_enrich_view_has_add_to_case_button(self, enrich_view):
        """Enrich view should have an 'Add to Case' button."""
        buttons = _find_controls(enrich_view, ft.ElevatedButton)
        add_btns = [b for b in buttons if _button_text(b) == "Add to Case"]
        assert len(add_btns) == 1

    def test_add_to_case_panel_hidden_before_enrichment(self, enrich_view):
        """Add to Case panel should be hidden before enrichment runs."""
        containers = _find_controls(enrich_view, ft.Container)
        case_containers = [
            c
            for c in containers
            if hasattr(c, "content")
            and c.content is not None
            and not isinstance(c.content, str)
            and any(
                isinstance(ctrl, ft.Text) and ctrl.value == "Investigation"
                for ctrl in _find_controls(c, ft.Text)
            )
        ]
        assert len(case_containers) == 1
        assert case_containers[0].visible is False

    def test_add_to_case_button_has_on_click_handler(self, enrich_view):
        """Add to Case button should have an on_click handler."""
        add_btn = _find_button(enrich_view, "Add to Case")
        assert add_btn is not None
        assert add_btn.on_click is not None


class TestAddToCaseExecution:
    """Test Add to Case click handler."""

    @pytest.mark.asyncio
    async def test_add_to_case_with_existing_case(self, mock_page):
        """Add to Case should link IOC to selected case."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="TestPlugin",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Clean",
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
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=1) as mock_add,
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")

            # Enrich first
            event = MagicMock()
            await enrich_btn.on_click(event)

            # Set case ID on dropdown
            case_dropdown = _find_dropdown_by_label(view, "Case")
            case_dropdown.value = "1"

            # Click Add to Case
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_add.assert_called_once()
            assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_add_to_case_creates_new_case(self, mock_page):
        """Add to Case should create a new case when name is provided."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="TestPlugin",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Clean",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]
        from lupe.case import CaseInfo

        new_case = CaseInfo(id=55, name="New Incident", description="", status="open", ioc_count=0)

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

            # Enrich first
            event = MagicMock()
            await enrich_btn.on_click(event)

            # Set new case name
            new_case_field = _find_textfield(view, "New case name")
            new_case_field.value = "New Incident"

            # Click Add to Case
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_create.assert_called_once_with("New Incident")
            mock_add.assert_called_once()
            # Should be called with case_id=55
            call_args = mock_add.call_args
            assert call_args[0][0] == 55

    @pytest.mark.asyncio
    async def test_add_to_case_shows_error_when_no_enrichment(self, mock_page):
        """Add to Case should show error when no enrichment results exist."""
        with patch("lupe.flet.views.enrich.list_cases", return_value=[]):
            view = build_enrich_view(mock_page)
            add_btn = _find_button(view, "Add to Case")
            event = MagicMock()
            await add_btn.on_click(event)
            assert mock_page.snack_bar is not None

    @pytest.mark.asyncio
    async def test_add_to_case_shows_error_when_no_case_selected(self, mock_page):
        """Add to Case should show error when no case is selected or named."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="TestPlugin",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Clean",
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
        ):
            view = build_enrich_view(mock_page)
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")
            event = MagicMock()
            await enrich_btn.on_click(event)

            # Try to add to case without selecting one
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)
            assert mock_page.snack_bar is not None


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


def _find_dropdown_by_label(control, label):
    """Find a Dropdown with the given label."""
    dropdowns = _find_controls(control, ft.Dropdown)
    for d in dropdowns:
        if d.label and label.lower() in d.label.lower():
            return d
    return None
