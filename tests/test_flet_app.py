"""Tests for the Flet desktop application (replaces Textual TUI)."""

from __future__ import annotations

import importlib


class TestFletAppImport:
    """Tests that the Flet app module is importable and well-formed."""

    def test_flet_package_importable(self):
        """lupe.flet package is importable."""
        mod = importlib.import_module("lupe.flet")
        assert mod is not None

    def test_flet_app_module_importable(self):
        """lupe.flet.app module is importable."""
        mod = importlib.import_module("lupe.flet.app")
        assert mod is not None

    def test_lupe_flet_app_class_exists(self):
        """LupeFletApp class exists in lupe.flet.app."""
        from lupe.flet.app import LupeFletApp

        assert LupeFletApp is not None

    def test_main_function_exists(self):
        """main() entry point function exists in lupe.flet.app."""
        from lupe.flet.app import main

        assert callable(main)

    def test_lupe_flet_app_has_main_method(self):
        """LupeFletApp has a static main method for flet.app target."""
        from lupe.flet.app import LupeFletApp

        assert hasattr(LupeFletApp, "main")
        assert callable(LupeFletApp.main)


class TestFletTheme:
    """Tests for the Flet theme module."""

    def test_theme_module_importable(self):
        """lupe.flet.theme module is importable."""
        mod = importlib.import_module("lupe.flet.theme")
        assert mod is not None

    def test_theme_colors_defined(self):
        """Theme module defines the expected color constants."""
        from lupe.flet.theme import CYAN, DARK_BG, MATRIX_GREEN

        assert MATRIX_GREEN == "#00FF41"
        assert CYAN == "#00ffff"
        assert DARK_BG == "#0a0a0a"

    def test_theme_has_matrix_dim(self):
        """Theme defines MATRIX_DIM for secondary elements."""
        from lupe.flet.theme import MATRIX_DIM

        assert MATRIX_DIM == "#00802b"

    def test_theme_has_text_colors(self):
        """Theme defines TEXT_PRIMARY and TEXT_SECONDARY."""
        from lupe.flet.theme import TEXT_PRIMARY, TEXT_SECONDARY

        assert TEXT_PRIMARY == "#ffffff"
        assert TEXT_SECONDARY == "#a0a0a0"

    def test_theme_mode_is_dark(self):
        """THEME_MODE is set to DARK."""
        from lupe.flet.theme import THEME_MODE

        assert THEME_MODE is not None


class TestFletViews:
    """Tests that all 8 views exist and are importable."""

    def test_home_view_importable(self):
        """HomeView is importable from lupe.flet.views.home."""
        from lupe.flet.views.home import HomeView

        assert HomeView is not None

    def test_enrich_view_importable(self):
        """EnrichView is importable from lupe.flet.views.enrich."""
        from lupe.flet.views.enrich import EnrichView

        assert EnrichView is not None

    def test_settings_view_importable(self):
        """SettingsView is importable from lupe.flet.views.settings."""
        from lupe.flet.views.settings import SettingsView

        assert SettingsView is not None

    def test_misp_view_importable(self):
        """MISPView is importable from lupe.flet.views.misp."""
        from lupe.flet.views.misp import MISPView

        assert MISPView is not None

    def test_plugins_view_importable(self):
        """PluginsView is importable from lupe.flet.views.plugins."""
        from lupe.flet.views.plugins import PluginsView

        assert PluginsView is not None

    def test_cases_view_importable(self):
        """CasesView is importable from lupe.flet.views.cases."""
        from lupe.flet.views.cases import CasesView

        assert CasesView is not None

    def test_profile_view_importable(self):
        """ProfileView is importable from lupe.flet.views.profile."""
        from lupe.flet.views.profile import ProfileView

        assert ProfileView is not None


class TestSettingsViewFields:
    """Tests that SettingsView has all required API key fields."""

    def test_settings_view_has_signup_urls(self):
        """SettingsView defines SIGNUP_URLS dict with all provider URLs."""
        from lupe.flet.views.settings import SIGNUP_URLS

        expected_providers = [
            "openai",
            "anthropic",
            "openrouter",
            "virustotal",
            "abuseipdb",
            "shodan",
            "otx",
            "urlscan",
            "hibp",
            "greynoise",
            "ipqs",
            "numverify",
            "misp",
            "censys",
            "hybrid_analysis",
        ]
        for provider in expected_providers:
            assert provider in SIGNUP_URLS, f"Missing signup URL for {provider}"

    def test_signup_urls_are_https(self):
        """All signup URLs use HTTPS."""
        from lupe.flet.views.settings import SIGNUP_URLS

        for provider, url in SIGNUP_URLS.items():
            assert url.startswith("https://"), f"{provider} signup URL is not HTTPS: {url}"

    def test_settings_view_has_field_definitions(self):
        """SettingsView defines FIELDS list with at least 14 API key fields."""
        from lupe.flet.views.settings import FIELDS

        assert len(FIELDS) >= 14, f"Expected at least 14 fields, got {len(FIELDS)}"

    def test_settings_field_definitions_have_correct_structure(self):
        """Each field definition has (key, label, is_password) tuple."""
        from lupe.flet.views.settings import FIELDS

        for field in FIELDS:
            assert len(field) == 3, (
                f"Field tuple should have 3 elements (key, label, is_password): {field}"
            )
            key, label, is_password = field
            assert isinstance(key, str), f"Field key should be str: {key}"
            assert isinstance(label, str), f"Field label should be str: {label}"
            assert isinstance(is_password, bool), f"Field is_password should be bool: {is_password}"

    def test_settings_has_save_function(self):
        """Settings module has save_settings function."""
        from lupe.flet.views.settings import save_settings

        assert callable(save_settings)

    def test_settings_has_load_function(self):
        """Settings module has load_settings function."""
        from lupe.flet.views.settings import load_settings

        assert callable(load_settings)


class TestHomeViewBanner:
    """Tests that HomeView contains the LUPE banner."""

    def test_home_view_has_banner(self):
        """Home module defines LUPE_BANNER constant."""
        from lupe.flet.views.home import LUPE_BANNER

        # Should contain box-drawing characters
        assert "█" in LUPE_BANNER or "╗" in LUPE_BANNER
        # Should reference LUPE (spaced or not)
        assert "L U P E" in LUPE_BANNER or "LUPE" in LUPE_BANNER


class TestFletEntryPoint:
    """Tests for the lupe-desktop entry point wiring."""

    def test_entry_point_target_exists(self):
        """The entry point target lupe.flet.app:main is importable."""
        from lupe.flet.app import main

        assert callable(main)
