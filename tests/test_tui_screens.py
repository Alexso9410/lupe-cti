"""Tests for the Textual TUI application and screens."""

from __future__ import annotations

import pytest


class TestTuiApp:
    """Tests for the main LupeTuiApp."""

    def test_textual_importable(self):
        """Textual is importable."""
        import textual

        assert textual.__version__

    def test_app_class_exists(self):
        """LupeTuiApp class exists and is a Textual App."""
        from lupe.tui.app import LupeTuiApp
        from textual.app import App

        assert issubclass(LupeTuiApp, App)

    def test_app_title(self):
        """LupeTuiApp has the correct title."""
        from lupe.tui.app import LupeTuiApp

        app = LupeTuiApp()
        assert app.title == "Lupe CTI"

    def test_app_has_bindings(self):
        """LupeTuiApp has key bindings for navigation."""
        from lupe.tui.app import LupeTuiApp

        app = LupeTuiApp()
        # BINDINGS are tuples of (key, action, description)
        binding_keys = [b[0] for b in app.BINDINGS]
        assert "q" in binding_keys
        assert "1" in binding_keys
        assert "2" in binding_keys

    def test_run_function_exists(self):
        """Module-level run() function exists for the entry point."""
        from lupe.tui.app import run

        assert callable(run)


class TestTuiTheme:
    """Tests for TUI theme constants."""

    def test_theme_colors_defined(self):
        """Theme module defines the expected color constants."""
        from lupe.tui.theme import MATRIX_GREEN, CYAN, DARK_BG, ERROR_RED

        assert MATRIX_GREEN == "#00FF41"
        assert CYAN == "#00FFFF"
        assert DARK_BG == "#1a1a1a"
        assert ERROR_RED == "#ff5555"

    def test_lupe_theme_dataclass(self):
        """LupeTheme dataclass exists with expected fields."""
        from lupe.tui.theme import LupeTheme

        theme = LupeTheme()
        assert theme.background is not None
        assert theme.primary is not None
        assert theme.success is not None


class TestTuiScreens:
    """Tests for individual TUI screens."""

    def test_home_screen_class_exists(self):
        """HomeScreen class exists."""
        from lupe.tui.screens.home import HomeScreen
        from textual.screen import Screen

        assert issubclass(HomeScreen, Screen)

    def test_enrich_screen_class_exists(self):
        """EnrichScreen class exists."""
        from lupe.tui.screens.enrich import EnrichScreen
        from textual.screen import Screen

        assert issubclass(EnrichScreen, Screen)

    def test_settings_screen_class_exists(self):
        """SettingsScreen class exists."""
        from lupe.tui.screens.settings import SettingsScreen
        from textual.screen import Screen

        assert issubclass(SettingsScreen, Screen)

    def test_misp_screen_class_exists(self):
        """MISPScreen class exists."""
        from lupe.tui.screens.misp import MISPScreen
        from textual.screen import Screen

        assert issubclass(MISPScreen, Screen)

    def test_plugins_screen_class_exists(self):
        """PluginsScreen class exists."""
        from lupe.tui.screens.plugins import PluginsScreen
        from textual.screen import Screen

        assert issubclass(PluginsScreen, Screen)

    def test_cases_screen_class_exists(self):
        """CasesScreen class exists."""
        from lupe.tui.screens.cases import CasesScreen
        from textual.screen import Screen

        assert issubclass(CasesScreen, Screen)

    def test_screens_package_init(self):
        """Screens package __init__.py imports all screens."""
        from lupe.tui.screens import (
            HomeScreen,
            EnrichScreen,
            SettingsScreen,
            MISPScreen,
            PluginsScreen,
            CasesScreen,
        )

        assert HomeScreen is not None
        assert EnrichScreen is not None


class TestTuiEntryPoint:
    """Tests for the lupe-desktop entry point."""

    def test_entry_point_module_exists(self):
        """lupe.tui.app module is importable."""
        import lupe.tui.app

        assert lupe.tui.app is not None
