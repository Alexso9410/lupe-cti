"""Auto-update module for Lupe CTI (PR-33).

Checks GitHub releases for newer versions and installs wheel updates.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx
from packaging.version import Version


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
