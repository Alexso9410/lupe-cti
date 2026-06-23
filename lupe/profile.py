"""Profile management for multi-user support (PR-32).

Provides lightweight "profiles" so multiple analysts can use Lupe CTI
without mixing data. Each profile gets its own SQLite DB under
~/.local/share/lupe/profiles/{name}/lupe.db.

The active profile is stored in ~/.config/lupe/active_profile.txt.
"""

from __future__ import annotations

import shutil

from lupe.config import get_config_dir, get_data_dir

ACTIVE_PROFILE_FILE = "active_profile.txt"


def get_active_profile() -> str:
    """Return the currently active profile name.

    Reads from ~/.config/lupe/active_profile.txt.
    Returns 'default' if the file doesn't exist.
    """
    profile_file = get_config_dir() / ACTIVE_PROFILE_FILE
    if not profile_file.exists():
        return "default"
    return profile_file.read_text().strip() or "default"


def set_active_profile(name: str) -> None:
    """Set the active profile.

    Args:
        name: Profile name to activate.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / ACTIVE_PROFILE_FILE).write_text(name)


def list_profiles() -> list[str]:
    """List all existing profile names.

    Returns:
        Sorted list of profile directory names under profiles/.
    """
    profiles_dir = get_data_dir() / "profiles"
    if not profiles_dir.exists():
        return []
    return sorted(entry.name for entry in profiles_dir.iterdir() if entry.is_dir())


def create_profile(name: str) -> None:
    """Create a new profile with its own DB.

    Args:
        name: Profile name (alphanumeric, hyphens, underscores).

    Raises:
        ValueError: If name is empty, invalid, or already exists.
    """
    if not name or not name.strip():
        raise ValueError("Profile name cannot be empty")
    name = name.strip()

    # Security: reject path traversal
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"Invalid profile name: {name}")

    profiles_dir = get_data_dir() / "profiles"
    profile_dir = profiles_dir / name

    if profile_dir.exists():
        raise ValueError(f"Profile '{name}' already exists")

    profile_dir.mkdir(parents=True, exist_ok=True)

    # Initialize an empty DB for this profile
    from lupe.db import Database

    db_path = str(profile_dir / "lupe.db")
    db = Database(db_path)
    db.close()


def delete_profile(name: str) -> None:
    """Delete a profile and all its data.

    Args:
        name: Profile name to delete.

    Raises:
        ValueError: If name is 'default', or profile not found.
    """
    if name == "default":
        raise ValueError("Cannot delete the 'default' profile")

    profile_dir = get_data_dir() / "profiles" / name
    if not profile_dir.exists():
        raise ValueError(f"Profile '{name}' not found")

    shutil.rmtree(profile_dir)


def get_profile_db_path(name: str) -> str:
    """Return the DB path for a given profile.

    Args:
        name: Profile name.

    Returns:
        Absolute path to the profile's lupe.db file.
    """
    return str(get_data_dir() / "profiles" / name / "lupe.db")


def migrate_legacy_db() -> bool:
    """Migrate legacy single-DB to the default profile.

    Moves ~/.local/share/lupe/lupe.db to
    ~/.local/share/lupe/profiles/default/lupe.db

    Returns:
        True if migration was performed, False otherwise.
    """
    data_dir = get_data_dir()
    legacy_db = data_dir / "lupe.db"
    default_dir = data_dir / "profiles" / "default"
    target_db = default_dir / "lupe.db"

    # Nothing to migrate
    if not legacy_db.exists():
        return False

    # Already migrated
    if target_db.exists():
        return False

    default_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(legacy_db), str(target_db))
    return True
