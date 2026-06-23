"""Tests for lupe.profile module — multi-user profile management (PR-32)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from lupe.profile import (
    ACTIVE_PROFILE_FILE,
    create_profile,
    delete_profile,
    get_active_profile,
    get_profile_db_path,
    list_profiles,
    migrate_legacy_db,
    set_active_profile,
)


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Provide a temporary config directory."""
    return tmp_path / "config"


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary data directory."""
    return tmp_path / "data"


class TestGetActiveProfile:
    """Test get_active_profile function."""

    def test_returns_default_when_no_file(self, tmp_config_dir):
        """Should return 'default' when active_profile.txt doesn't exist."""
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            result = get_active_profile()
        assert result == "default"

    def test_returns_stored_profile(self, tmp_config_dir):
        """Should return the profile name stored in active_profile.txt."""
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        (tmp_config_dir / ACTIVE_PROFILE_FILE).write_text("analyst1")
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            result = get_active_profile()
        assert result == "analyst1"

    def test_strips_whitespace(self, tmp_config_dir):
        """Should strip whitespace from stored profile name."""
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        (tmp_config_dir / ACTIVE_PROFILE_FILE).write_text("  analyst2  \n")
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            result = get_active_profile()
        assert result == "analyst2"


class TestSetActiveProfile:
    """Test set_active_profile function."""

    def test_writes_profile_to_file(self, tmp_config_dir):
        """Should write the profile name to active_profile.txt."""
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            set_active_profile("analyst3")
        content = (tmp_config_dir / ACTIVE_PROFILE_FILE).read_text()
        assert content == "analyst3"

    def test_creates_config_dir_if_missing(self, tmp_config_dir):
        """Should create config dir if it doesn't exist."""
        assert not tmp_config_dir.exists()
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            set_active_profile("newuser")
        assert (tmp_config_dir / ACTIVE_PROFILE_FILE).exists()

    def test_overwrites_existing(self, tmp_config_dir):
        """Should overwrite existing profile name."""
        tmp_config_dir.mkdir(parents=True, exist_ok=True)
        (tmp_config_dir / ACTIVE_PROFILE_FILE).write_text("old")
        with patch("lupe.profile.get_config_dir", return_value=tmp_config_dir):
            set_active_profile("new")
        content = (tmp_config_dir / ACTIVE_PROFILE_FILE).read_text()
        assert content == "new"


class TestListProfiles:
    """Test list_profiles function."""

    def test_returns_empty_when_no_profiles_dir(self, tmp_data_dir):
        """Should return empty list when profiles dir doesn't exist."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = list_profiles()
        assert result == []

    def test_returns_existing_profiles(self, tmp_data_dir):
        """Should return list of profile directory names."""
        profiles_dir = tmp_data_dir / "profiles"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "default").mkdir()
        (profiles_dir / "analyst1").mkdir()
        (profiles_dir / "analyst2").mkdir()
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = list_profiles()
        assert sorted(result) == ["analyst1", "analyst2", "default"]

    def test_ignores_files_in_profiles_dir(self, tmp_data_dir):
        """Should ignore non-directory entries."""
        profiles_dir = tmp_data_dir / "profiles"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "default").mkdir()
        (profiles_dir / "notes.txt").write_text("not a profile")
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = list_profiles()
        assert result == ["default"]


class TestCreateProfile:
    """Test create_profile function."""

    def test_creates_profile_directory(self, tmp_data_dir):
        """Should create the profile directory under profiles/."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            create_profile("analyst1")
        assert (tmp_data_dir / "profiles" / "analyst1").exists()

    def test_creates_db_in_profile(self, tmp_data_dir):
        """Should create a DB file in the profile directory."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            create_profile("analyst1")
        db_path = tmp_data_dir / "profiles" / "analyst1" / "lupe.db"
        assert db_path.exists()

    def test_raises_on_duplicate(self, tmp_data_dir):
        """Should raise ValueError if profile already exists."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            create_profile("analyst1")
            with pytest.raises(ValueError, match="already exists"):
                create_profile("analyst1")

    def test_rejects_invalid_name(self, tmp_data_dir):
        """Should reject profile names with path separators."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            with pytest.raises(ValueError, match="[Ii]nvalid"):
                create_profile("../escape")

    def test_rejects_empty_name(self, tmp_data_dir):
        """Should reject empty profile names."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            with pytest.raises(ValueError, match="empty"):
                create_profile("")


class TestDeleteProfile:
    """Test delete_profile function."""

    def test_deletes_profile_directory(self, tmp_data_dir):
        """Should remove the profile directory."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            create_profile("temp")
            delete_profile("temp")
        assert not (tmp_data_dir / "profiles" / "temp").exists()

    def test_raises_on_nonexistent(self, tmp_data_dir):
        """Should raise ValueError if profile doesn't exist."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            with pytest.raises(ValueError, match="not found"):
                delete_profile("ghost")

    def test_rejects_deleting_default(self, tmp_data_dir):
        """Should refuse to delete the 'default' profile."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            create_profile("default")
            with pytest.raises(ValueError, match="default"):
                delete_profile("default")


class TestGetProfileDbPath:
    """Test get_profile_db_path function."""

    def test_returns_path_for_profile(self, tmp_data_dir):
        """Should return the DB path for a given profile."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = get_profile_db_path("analyst1")
        assert result.endswith(str(Path("analyst1/lupe.db")))
        assert "profiles" in result

    def test_default_profile_path(self, tmp_data_dir):
        """Should return correct path for default profile."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = get_profile_db_path("default")
        assert "default" in result
        assert result.endswith("lupe.db")


class TestMigrateLegacyDb:
    """Test migrate_legacy_db function."""

    def test_migrates_existing_db(self, tmp_data_dir):
        """Should move legacy DB to profiles/default/."""
        legacy_db = tmp_data_dir / "lupe.db"
        legacy_db.parent.mkdir(parents=True, exist_ok=True)
        legacy_db.write_text("legacy data")

        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = migrate_legacy_db()

        assert result is True
        default_db = tmp_data_dir / "profiles" / "default" / "lupe.db"
        assert default_db.exists()
        assert default_db.read_text() == "legacy data"
        assert not legacy_db.exists()

    def test_no_migration_when_no_legacy(self, tmp_data_dir):
        """Should return False when no legacy DB exists."""
        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = migrate_legacy_db()
        assert result is False

    def test_no_migration_when_default_already_exists(self, tmp_data_dir):
        """Should not overwrite existing default profile DB."""
        legacy_db = tmp_data_dir / "lupe.db"
        legacy_db.parent.mkdir(parents=True, exist_ok=True)
        legacy_db.write_text("legacy")

        default_db = tmp_data_dir / "profiles" / "default" / "lupe.db"
        default_db.parent.mkdir(parents=True, exist_ok=True)
        default_db.write_text("existing")

        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result = migrate_legacy_db()

        assert result is False
        assert default_db.read_text() == "existing"

    def test_idempotent(self, tmp_data_dir):
        """Should be safe to call multiple times."""
        legacy_db = tmp_data_dir / "lupe.db"
        legacy_db.parent.mkdir(parents=True, exist_ok=True)
        legacy_db.write_text("data")

        with patch("lupe.profile.get_data_dir", return_value=tmp_data_dir):
            result1 = migrate_legacy_db()
            result2 = migrate_legacy_db()

        assert result1 is True
        assert result2 is False
