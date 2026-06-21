"""Tests for TUI Settings screen validation and persistence."""

from __future__ import annotations

import sys

import pytest


class TestSettingsValidation:
    """Tests for API key format validation logic."""

    def test_validate_openai_key_valid(self):
        """OpenAI key starting with sk- passes validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("openai", "sk-test1234567890abcdef") is True

    def test_validate_openai_key_invalid(self):
        """OpenAI key not starting with sk- fails validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("openai", "invalid-key") is False

    def test_validate_anthropic_key_valid(self):
        """Anthropic key starting with sk-ant- passes validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("anthropic", "sk-ant-test1234567890abcdef") is True

    def test_validate_anthropic_key_invalid(self):
        """Anthropic key not starting with sk-ant- fails validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("anthropic", "sk-test123") is False

    def test_validate_openrouter_key_valid(self):
        """OpenRouter key starting with sk-or- passes validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("openrouter", "sk-or-test1234567890abcdef") is True

    def test_validate_openrouter_key_invalid(self):
        """OpenRouter key not starting with sk-or- fails validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("openrouter", "bad-key") is False

    def test_validate_generic_key_nonempty(self):
        """Generic non-empty key passes validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("virustotal", "any-nonempty-key-123") is True

    def test_validate_generic_key_empty(self):
        """Empty key fails validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("virustotal", "") is False

    def test_validate_url_valid(self):
        """Valid URL passes validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("ollama_url", "http://localhost:11434") is True

    def test_validate_url_invalid(self):
        """Invalid URL fails validation."""
        from lupe.tui.screens.settings import validate_key_format

        assert validate_key_format("ollama_url", "not-a-url") is False


class TestSettingsPersistence:
    """Tests for saving and loading settings to/from TOML file."""

    def test_save_creates_config_file(self, tmp_path, monkeypatch):
        """save_settings creates a TOML file at the expected path."""
        from lupe.tui.screens.settings import save_settings

        monkeypatch.setattr(
            "lupe.tui.screens.settings._get_config_path", lambda: tmp_path / "lupe.toml"
        )
        settings = {
            "llm_provider": "openai",
            "openai_key": "sk-test123",
        }
        save_settings(settings)

        config_path = tmp_path / "lupe.toml"
        assert config_path.exists()

    def test_save_creates_parent_dirs(self, tmp_path, monkeypatch):
        """save_settings creates parent directories if they don't exist."""
        from lupe.tui.screens.settings import save_settings

        config_path = tmp_path / "nested" / "dir" / "lupe.toml"
        monkeypatch.setattr("lupe.tui.screens.settings._get_config_path", lambda: config_path)
        save_settings({"test": "value"})

        assert config_path.exists()

    def test_save_file_permissions_unix(self, tmp_path, monkeypatch):
        """On Unix, config file gets 600 permissions."""
        from lupe.tui.screens.settings import save_settings

        if sys.platform == "win32":
            pytest.skip("chmod 600 not applicable on Windows")

        monkeypatch.setattr(
            "lupe.tui.screens.settings._get_config_path", lambda: tmp_path / "lupe.toml"
        )
        save_settings({"test": "value"})

        mode = (tmp_path / "lupe.toml").stat().st_mode & 0o777
        assert mode == 0o600

    def test_save_no_crash_on_windows(self, tmp_path, monkeypatch):
        """On Windows, save doesn't crash (chmod gracefully skipped)."""
        from lupe.tui.screens.settings import save_settings

        monkeypatch.setattr(
            "lupe.tui.screens.settings._get_config_path", lambda: tmp_path / "lupe.toml"
        )
        # Should not raise on any platform
        save_settings({"test": "value"})
        assert (tmp_path / "lupe.toml").exists()

    def test_load_populates_settings(self, tmp_path, monkeypatch):
        """load_settings reads values from TOML file."""

        from lupe.tui.screens.settings import load_settings

        config_path = tmp_path / "lupe.toml"
        config_path.write_text(
            'llm_provider = "openai"\nopenai_key = "sk-test123"\n',
            encoding="utf-8",
        )
        monkeypatch.setattr("lupe.tui.screens.settings._get_config_path", lambda: config_path)

        loaded = load_settings()
        assert loaded["llm_provider"] == "openai"
        assert loaded["openai_key"] == "sk-test123"

    def test_load_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        """load_settings returns empty dict when config file doesn't exist."""
        from lupe.tui.screens.settings import load_settings

        monkeypatch.setattr(
            "lupe.tui.screens.settings._get_config_path", lambda: tmp_path / "nonexistent.toml"
        )

        loaded = load_settings()
        assert loaded == {}

    def test_roundtrip_save_load(self, tmp_path, monkeypatch):
        """Settings survive a save→load roundtrip."""
        from lupe.tui.screens.settings import load_settings, save_settings

        monkeypatch.setattr(
            "lupe.tui.screens.settings._get_config_path", lambda: tmp_path / "lupe.toml"
        )
        original = {
            "llm_provider": "anthropic",
            "anthropic_key": "sk-ant-test123",
            "ollama_url": "http://localhost:11434",
        }
        save_settings(original)
        loaded = load_settings()

        assert loaded["llm_provider"] == original["llm_provider"]
        assert loaded["anthropic_key"] == original["anthropic_key"]


class TestSignupUrls:
    """Tests for provider signup URL lookup."""

    def test_signup_urls_defined(self):
        """SIGNUP_URLS dict exists and has expected entries."""
        from lupe.tui.screens.settings import SIGNUP_URLS

        assert "openai" in SIGNUP_URLS
        assert "anthropic" in SIGNUP_URLS
        assert "virustotal" in SIGNUP_URLS
        assert "shodan" in SIGNUP_URLS
        assert "abuseipdb" in SIGNUP_URLS

    def test_signup_urls_are_valid(self):
        """All signup URLs start with https://."""
        from lupe.tui.screens.settings import SIGNUP_URLS

        for name, url in SIGNUP_URLS.items():
            assert url.startswith("https://"), f"{name} URL should start with https://"
