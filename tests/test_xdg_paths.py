"""Tests for XDG paths and platformdirs integration (PR-4)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


class TestXdgPaths:
    """Tests for platformdirs-based path resolution."""

    def test_platformdirs_importable(self) -> None:
        import platformdirs

        assert hasattr(platformdirs, "user_data_dir")

    def test_get_data_dir_returns_absolute_path(self) -> None:
        from lupe.config import get_data_dir

        result = get_data_dir()
        assert result.is_absolute()
        assert "lupe" in str(result).lower()

    def test_get_config_dir_returns_absolute_path(self) -> None:
        from lupe.config import get_config_dir

        result = get_config_dir()
        assert result.is_absolute()
        assert "lupe" in str(result).lower()

    def test_get_cache_dir_returns_absolute_path(self) -> None:
        from lupe.config import get_cache_dir

        result = get_cache_dir()
        assert result.is_absolute()
        assert "lupe" in str(result).lower()

    def test_settings_db_path_uses_data_dir(self) -> None:
        from lupe.config import get_data_dir, get_settings

        settings = get_settings()
        expected = str(get_data_dir() / "lupe.db")
        assert settings.db_path == expected

    def test_settings_db_path_expands_tilde(self) -> None:
        from lupe.config import Settings

        s = Settings(db_path="~/custom/lupe.db")
        assert "~" not in s.db_path
        assert s.db_path.endswith(str(Path("custom/lupe.db")))

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod is Unix-only")
    def test_ensure_dirs_creates_with_permissions(self) -> None:
        import os

        from lupe.config import ensure_dirs, get_config_dir

        ensure_dirs()
        config_dir = get_config_dir()
        assert config_dir.exists()
        mode = os.stat(config_dir).st_mode & 0o777
        assert mode == 0o700

    def test_ensure_dirs_creates_all_dirs(self) -> None:
        from lupe.config import ensure_dirs, get_cache_dir, get_config_dir, get_data_dir

        ensure_dirs()
        assert get_data_dir().exists()
        assert get_config_dir().exists()
        assert get_cache_dir().exists()


class TestXdgPathsDb:
    """Tests for Database using XDG paths."""

    def test_db_uses_xdg_data_dir(self, tmp_path: Path) -> None:
        from lupe.db import Database

        db_path = str(tmp_path / "test.db")
        db = Database(db_path)
        assert db._conn is not None
        db.close()

    def test_db_creates_parent_dirs(self, tmp_path: Path) -> None:
        from lupe.db import Database

        nested = tmp_path / "deep" / "nested" / "lupe.db"
        db = Database(str(nested))
        assert nested.exists()
        db.close()
