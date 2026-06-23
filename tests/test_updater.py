"""Tests for lupe.updater module — auto-update via GitHub releases (PR-33)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lupe.updater import (
    download_wheel,
    download_wheel_with_verification,
    get_current_version,
    get_latest_version,
    install_wheel,
    is_update_available,
    lookup_expected_sha256,
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


class TestLookupExpectedSha256:
    """lookup_expected_sha256 finds the right line in SHA256SUMS text."""

    def test_finds_match(self) -> None:
        sha256_text = (
            f"{'a' * 64}  lupe_cti-1.0.0-py3-none-any.whl\n"
            f"{'b' * 64}  lupe_cti-1.0.0.tar.gz\n"
        )
        result = lookup_expected_sha256(sha256_text, "lupe_cti-1.0.0-py3-none-any.whl")
        assert result == "a" * 64

    def test_returns_none_when_missing(self) -> None:
        sha256_text = f"{'a' * 64}  other-1.0.0.whl\n"
        result = lookup_expected_sha256(sha256_text, "lupe_cti-1.0.0.whl")
        assert result is None

    def test_handles_binary_mode_marker(self) -> None:
        sha256_text = f"*{'c' * 64}  lupe_cti-1.0.0.whl\n"
        result = lookup_expected_sha256(sha256_text, "lupe_cti-1.0.0.whl")
        assert result == "c" * 64

    def test_handles_path_prefix(self) -> None:
        sha256_text = f"{'d' * 64}  dist/lupe_cti-1.0.0.whl\n"
        result = lookup_expected_sha256(sha256_text, "lupe_cti-1.0.0.whl")
        assert result == "d" * 64


class TestDownloadWheelWithVerification:
    """CRITICAL: download_wheel_with_verification refuses tampered wheels."""

    def _mock_client(self, mock_client_cls, get_return_value=None, get_side_effect=None):
        mock_client = MagicMock()
        if get_return_value is not None:
            mock_client.get.return_value = get_return_value
        if get_side_effect is not None:
            mock_client.get.side_effect = get_side_effect
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        return mock_client

    def test_happy_path_with_matching_hash(self, tmp_path):
        import hashlib


        wheel_data = b"clean wheel data"
        digest = hashlib.sha256(wheel_data).hexdigest()
        sha256_text = f"{digest}  lupe_cti-1.0.1-py3-none-any.whl\n"

        dest = tmp_path / "lupe_cti-1.0.1-py3-none-any.whl"

        def _mock_get(url, **_kwargs):
            resp = MagicMock()
            if url.endswith("SHA256SUMS.txt"):
                resp.status_code = 200
                resp.text = sha256_text
            else:
                resp.status_code = 200
                resp.content = wheel_data
            return resp

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = _mock_get
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            ok, reason = download_wheel_with_verification(
                "https://github.com/o/r/releases/download/v1.0.1/lupe_cti-1.0.1-py3-none-any.whl",
                dest,
                "o/r",
                "v1.0.1",
            )

        assert ok is True
        assert reason == "ok"
        assert dest.read_bytes() == wheel_data

    def test_hash_mismatch_aborts(self, tmp_path):

        wheel_data = b"EVIL PAYLOAD"
        # Publish a hash that does NOT match
        sha256_text = f"{'0' * 64}  lupe_cti-1.0.1-py3-none-any.whl\n"

        dest = tmp_path / "lupe_cti-1.0.1-py3-none-any.whl"

        def _mock_get(url, **_kwargs):
            resp = MagicMock()
            if url.endswith("SHA256SUMS.txt"):
                resp.status_code = 200
                resp.text = sha256_text
            else:
                resp.status_code = 200
                resp.content = wheel_data
            return resp

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = _mock_get
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            ok, reason = download_wheel_with_verification(
                "https://github.com/o/r/releases/download/v1.0.1/lupe_cti-1.0.1-py3-none-any.whl",
                dest,
                "o/r",
                "v1.0.1",
            )

        assert ok is False
        assert reason == "mismatch"
        # Critical: file should have been deleted
        assert not dest.exists()

    def test_no_sha256sums_rejects(self, tmp_path):
        """Fail-closed: releases without SHA256SUMS.txt are refused."""

        wheel_data = b"wheel without sha256sums"
        dest = tmp_path / "lupe_cti-0.9.0-py3-none-any.whl"

        def _mock_get(url, **_kwargs):
            resp = MagicMock()
            if "SHA256SUMS" in url:
                resp.status_code = 404
            else:
                resp.status_code = 200
                resp.content = wheel_data
            return resp

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = _mock_get
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            ok, reason = download_wheel_with_verification(
                "https://github.com/o/r/releases/download/v0.9.0/lupe_cti-0.9.0-py3-none-any.whl",
                dest,
                "o/r",
                "v0.9.0",
            )

        assert ok is False
        assert reason == "no_sha256sums"
        assert not dest.exists()

    def test_download_failure_propagates(self, tmp_path):

        dest = tmp_path / "test.whl"

        with patch("lupe.updater.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Network down")
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            ok, reason = download_wheel_with_verification(
                "https://github.com/o/r/releases/download/v1.0.0/test.whl",
                dest,
                "o/r",
                "v1.0.0",
            )

        assert ok is False
        assert reason == "download_failed"
        assert not dest.exists()
