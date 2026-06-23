"""Auto-update module for Lupe CTI (PR-33).

Checks GitHub releases for newer versions and installs wheel updates.
Wheel downloads are verified against the SHA256 published in the
release's ``SHA256SUMS.txt`` before installation.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import httpx
from packaging.version import Version

logger = logging.getLogger(__name__)


def get_current_version() -> str:
    """Return the currently installed version of lupe-cti.

    Uses importlib.metadata to read the version from the installed package.

    Returns:
        Version string (e.g. '1.0.0').
    """
    from importlib.metadata import version

    return version("lupe-cti")


def get_latest_version(github_repo: str) -> str | None:
    """Fetch the latest release version from GitHub.

    Args:
        github_repo: GitHub repo in 'owner/repo' format.

    Returns:
        Version string without 'v' prefix, or None on error.
    """
    url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if resp.status_code != 200:
            return None
        data = resp.json()
        tag = data.get("tag_name", "")
        return tag.lstrip("v") if tag else None
    except Exception:
        return None


def is_update_available(current: str, latest: str) -> bool:
    """Compare current and latest versions.

    Args:
        current: Current version string.
        latest: Latest version string.

    Returns:
        True if latest is newer than current.
    """
    try:
        return Version(latest) > Version(current)
    except Exception:
        return False


def download_wheel(url: str, dest_path: Path) -> bool:
    """Download a wheel file from a URL.

    Args:
        url: URL to download the wheel from.
        dest_path: Local path to save the wheel.

    Returns:
        True on success, False on error.
    """
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return False
        dest_path.write_bytes(resp.content)
        return True
    except Exception:
        return False


def fetch_sha256sums(github_repo: str, tag: str) -> str | None:
    """Fetch the ``SHA256SUMS.txt`` file from a GitHub release.

    Args:
        github_repo: GitHub repo in 'owner/repo' format.
        tag: Release tag (with or without leading 'v').

    Returns:
        The text content of SHA256SUMS.txt, or None if not available.
    """
    tag_clean = tag.lstrip("v")
    urls = [
        f"https://github.com/{github_repo}/releases/download/v{tag_clean}/SHA256SUMS.txt",
        f"https://github.com/{github_repo}/releases/download/{tag_clean}/SHA256SUMS.txt",
    ]
    for url in urls:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            continue
    return None


def lookup_expected_sha256(sha256_text: str, wheel_filename: str) -> str | None:
    """Find the expected SHA256 digest for *wheel_filename* in SHA256SUMS text.

    Args:
        sha256_text: The contents of a SHA256SUMS.txt file.
        wheel_filename: Filename to look up (basename).

    Returns:
        The 64-char hex digest if found, else None.
    """
    # Local import to avoid module-level cycle on package import
    from lupe.security.integrity import parse_sha256_line

    for line in sha256_text.splitlines():
        parsed = parse_sha256_line(line)
        if parsed is None:
            continue
        filename, digest = parsed
        # Match by basename to be tolerant of path prefixes
        if filename.endswith("/" + wheel_filename) or filename == wheel_filename:
            return digest
    return None


def download_wheel_with_verification(
    wheel_url: str,
    dest_path: Path,
    github_repo: str,
    tag: str,
) -> tuple[bool, str]:
    """Download a wheel, verify its SHA256 against the release, and return the result.

    Behavior:
        1. Downloads the wheel to *dest_path*.
        2. Fetches the release's SHA256SUMS.txt.
        3. Looks up the expected hash for the wheel's filename.
        4. If a hash is published and the actual hash does not match,
           deletes the downloaded file and returns (False, "mismatch").
        5. If no SHA256SUMS.txt is published (older releases),
           logs a warning and accepts the download (backward compat).
        6. If a SHA256SUMS.txt is published but the wheel isn't listed,
           logs a warning and accepts the download (manual release).

    Args:
        wheel_url: Direct download URL for the wheel.
        dest_path: Local path to save the wheel to.
        github_repo: GitHub repo in 'owner/repo' format.
        tag: Release tag (e.g. 'v1.0.1' or '1.0.1').

    Returns:
        Tuple of (success, reason). reason is one of:
        "ok", "mismatch", "download_failed".
    """
    if not download_wheel(wheel_url, dest_path):
        return False, "download_failed"

    # Try to verify against SHA256SUMS
    try:
        sha256_text = fetch_sha256sums(github_repo, tag)
    except Exception as exc:
        logger.warning("Could not fetch SHA256SUMS.txt: %s", exc)
        sha256_text = None

    if sha256_text is None:
        logger.warning(
            "No SHA256SUMS.txt published for release %s — skipping integrity check. "
            "This release predates the integrity-check feature.",
            tag,
        )
        return True, "ok"

    expected = lookup_expected_sha256(sha256_text, dest_path.name)
    if expected is None:
        logger.warning(
            "Wheel %s not listed in SHA256SUMS.txt — accepting download without "
            "integrity check. This is unexpected for a published release.",
            dest_path.name,
        )
        return True, "ok"

    # Local import to avoid module-level cycle
    from lupe.security.integrity import verify_wheel_integrity

    try:
        if not verify_wheel_integrity(dest_path, expected):
            dest_path.unlink(missing_ok=True)
            logger.error(
                "SHA256 mismatch for %s — refusing to install. "
                "Expected %s, got something else.",
                dest_path.name,
                expected,
            )
            return False, "mismatch"
    except OSError as exc:
        dest_path.unlink(missing_ok=True)
        logger.error("Could not read downloaded wheel for verification: %s", exc)
        return False, "download_failed"

    return True, "ok"


def install_wheel(wheel_path: Path) -> bool:
    """Install a downloaded wheel using pip.

    Args:
        wheel_path: Path to the .whl file.

    Returns:
        True on success, False on error.
    """
    if not wheel_path.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", str(wheel_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False
