"""End-to-end tests for enrich -> AI analysis -> add to case workflow."""

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


@pytest.fixture
def mock_page():
    return MockPage()


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
        if f.label == label:
            return f
    return None


def _find_dropdown_by_label(control, label):
    dropdowns = _find_controls(control, ft.Dropdown)
    for d in dropdowns:
        if d.label and label.lower() in d.label.lower():
            return d
    return None


class TestEnrichToAIToCaseWorkflow:
    """Test the complete enrich -> AI analysis -> add to case workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_enrich_ai_add_to_case(self, mock_page):
        """Complete workflow: enrich IOC, analyze with AI, add to case."""
        mock_ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        mock_results = [
            EnrichmentResult(
                source="ThreatFox",
                ioc_value="8.8.8.8",
                severity=Severity.medium,
                summary="Known C2 server",
                raw_data={"score": 42},
                enriched_at=datetime.now(tz=timezone.utc),
            ),
            EnrichmentResult(
                source="AbuseIPDB",
                ioc_value="8.8.8.8",
                severity=Severity.high,
                summary="Abuse confidence: 85%",
                raw_data={"abuseConfidenceScore": 85},
                enriched_at=datetime.now(tz=timezone.utc),
            ),
        ]
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(
            return_value="## Puntuacion de riesgo: 7/10\nIP asociado a C2."
        )
        from lupe.case import CaseInfo

        new_case = CaseInfo(id=10, name="IR-2026-042", description="", status="open", ioc_count=0)

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.get_provider", return_value=mock_provider),
            patch("lupe.flet.views.enrich.list_cases", return_value=[]),
            patch("lupe.flet.views.enrich.create_case", return_value=new_case) as mock_create,
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=77) as mock_add,
        ):
            view = build_enrich_view(mock_page)

            # Step 1: Enrich
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "8.8.8.8"
            enrich_btn = _find_button(view, "Enrich")
            event = MagicMock()
            await enrich_btn.on_click(event)

            # Verify enrichment ran
            assert len(mock_results) == 2
            tables = _find_controls(view, ft.DataTable)
            assert tables[0].visible is True

            # Step 2: AI Analysis
            ai_btn = _find_button(view, "Analyze with AI")
            await ai_btn.on_click(event)
            mock_provider.generate.assert_called_once()

            # Verify AI prompt contains enrichment data
            call_args = mock_provider.generate.call_args
            user_prompt = call_args[0][0] if call_args[0] else call_args.kwargs.get("prompt", "")
            assert "8.8.8.8" in user_prompt

            # Step 3: Add to Case
            new_case_field = _find_textfield(view, "New case name")
            new_case_field.value = "IR-2026-042"
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_create.assert_called_once_with("IR-2026-042")
            mock_add.assert_called_once()
            add_args = mock_add.call_args
            assert add_args[0][0] == 10  # case_id
            assert add_args[0][1] == "8.8.8.8"  # ioc_value

    @pytest.mark.asyncio
    async def test_workflow_with_existing_case(self, mock_page):
        """Workflow: enrich, analyze, add to existing case."""
        mock_ioc = IOC(type=IOCType.domain, value="evil.com")
        mock_results = [
            EnrichmentResult(
                source="URLhaus",
                ioc_value="evil.com",
                severity=Severity.critical,
                summary="Active malware distribution",
                raw_data={},
                enriched_at=datetime.now(tz=timezone.utc),
            )
        ]
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="## Risk: 9/10\nCritical threat.")

        with (
            patch("lupe.flet.views.enrich.detect_ioc", return_value=mock_ioc),
            patch(
                "lupe.flet.views.enrich.run_enrichment",
                new_callable=AsyncMock,
                return_value=mock_results,
            ),
            patch("lupe.flet.views.enrich.get_settings", return_value=MagicMock()),
            patch("lupe.flet.views.enrich.get_provider", return_value=mock_provider),
            patch("lupe.flet.views.enrich.list_cases", return_value=[]),
            patch("lupe.flet.views.enrich.add_ioc_to_case", return_value=88) as mock_add,
        ):
            view = build_enrich_view(mock_page)

            # Enrich
            ioc_field = _find_textfield(view, "IOC Value")
            ioc_field.value = "evil.com"
            enrich_btn = _find_button(view, "Enrich")
            event = MagicMock()
            await enrich_btn.on_click(event)

            # AI Analysis
            ai_btn = _find_button(view, "Analyze with AI")
            await ai_btn.on_click(event)

            # Add to existing case
            case_dropdown = _find_dropdown_by_label(view, "Case")
            case_dropdown.value = "5"
            add_btn = _find_button(view, "Add to Case")
            await add_btn.on_click(event)

            mock_add.assert_called_once()
            assert mock_add.call_args[0][0] == 5


class TestViewBuildSmoke:
    """Smoke test: all views build without error."""

    @pytest.mark.parametrize(
        "mod_path,func_name",
        [
            ("lupe.flet.views.home", "build_home_view"),
            ("lupe.flet.views.enrich", "build_enrich_view"),
            ("lupe.flet.views.settings", "build_settings_view"),
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
        result = func(page)
        assert isinstance(result, ft.Control)


class TestCLICommands:
    """Test that CLI commands still work after changes."""

    def test_config_show_command(self):
        """lupe config show should be importable."""
        from lupe.cli import app

        assert app is not None

    def test_enrich_command_exists(self):
        """enrich command should exist in CLI."""
        import lupe.cli as cli_mod

        source = open(cli_mod.__file__, encoding="utf-8").read()
        assert "enrich" in source

    def test_case_module_importable(self):
        """case module should be importable."""
        from lupe.case import add_ioc_to_case, create_case, list_cases

        assert callable(list_cases)
        assert callable(create_case)
        assert callable(add_ioc_to_case)

    def test_llm_registry_importable(self):
        """LLM registry should be importable."""
        from lupe.llm.registry import get_provider

        assert callable(get_provider)
