"""Tests for lupe.updater module — auto-update via GitHub releases (PR-33)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lupe.updater import (
    download_wheel,
    get_current_version,
    get_latest_version,
    install_wheel,
    is_update_available,
)


class TestGetCurrentVersion:
    """Test get_current_version function."""

    def test_returns_string(self):
        """Should return a version string."""
        result = get_current_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_follows_semver_pattern(self):
        """Should return a version that looks like X.Y.Z."""
        result = get_current_version()
        parts = result.split(".")
        assert len(parts) >= 2, f"Version '{result}' doesn't look like semver"


class TestGetLatestVersion:
    """Test get_latest_version function."""

    def test_returns_none_on_network_error(self):
        """Should return None when the API call fails."""
        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = get_latest_version("owner/repo")
        assert result is None

    def test_returns_version_from_api(self):
        """Should extract version tag from GitHub API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v2.0.0"}

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = get_latest_version("owner/repo")

        assert result == "2.0.0"

    def test_strips_v_prefix(self):
        """Should strip 'v' prefix from tag name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v1.5.0"}

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = get_latest_version("owner/repo")

        assert result == "1.5.0"

    def test_returns_none_on_404(self):
        """Should return None when release not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = get_latest_version("owner/repo")

        assert result is None


class TestIsUpdateAvailable:
    """Test is_update_available function."""

    def test_returns_true_when_newer(self):
        """Should return True when latest > current."""
        assert is_update_available("1.0.0", "2.0.0") is True

    def test_returns_false_when_same(self):
        """Should return False when versions match."""
        assert is_update_available("1.0.0", "1.0.0") is False

    def test_returns_false_when_current_newer(self):
        """Should return False when current is ahead."""
        assert is_update_available("2.0.0", "1.0.0") is False

    def test_handles_prerelease(self):
        """Should handle pre-release version comparison."""
        # 1.0.0 < 1.1.0-beta < 1.1.0
        assert is_update_available("1.0.0", "1.1.0-beta") is True

    def test_handles_patch_versions(self):
        """Should correctly compare patch versions."""
        assert is_update_available("1.0.0", "1.0.1") is True
        assert is_update_available("1.0.1", "1.0.0") is False


class TestDownloadWheel:
    """Test download_wheel function."""

    def test_downloads_to_destination(self, tmp_path):
        """Should download file to the specified path."""
        dest = tmp_path / "test.whl"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake wheel data"

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = download_wheel("https://example.com/test.whl", dest)

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == b"fake wheel data"

    def test_returns_false_on_error(self, tmp_path):
        """Should return False on download failure."""
        dest = tmp_path / "fail.whl"
        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Download failed")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = download_wheel("https://example.com/fail.whl", dest)

        assert result is False


class TestInstallWheel:
    """Test install_wheel function."""

    def test_returns_true_on_success(self, tmp_path):
        """Should return True when pip install succeeds."""
        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"fake")

        with patch("lupe.updater.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = install_wheel(wheel)

        assert result is True

    def test_returns_false_on_failure(self, tmp_path):
        """Should return False when pip install fails."""
        wheel = tmp_path / "bad.whl"
        wheel.write_bytes(b"fake")

        with patch("lupe.updater.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = install_wheel(wheel)

        assert result is False

    def test_returns_false_on_nonexistent(self, tmp_path):
        """Should return False when wheel file doesn't exist."""
        wheel = tmp_path / "missing.whl"
        result = install_wheel(wheel)
        assert result is False
