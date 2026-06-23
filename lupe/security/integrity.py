"""Wheel and binary integrity verification via SHA256.

Used by the auto-updater to ensure that downloaded artifacts have not
been tampered with in transit or via a compromised release pipeline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256(file_path: Path, *, chunk_size: int = 65536) -> str:
    """Compute the SHA256 hex digest of *file_path* in streaming fashion.

    Reads the file in 64KB chunks to handle large wheels without
    loading them entirely into memory.

    Args:
        file_path: Path to the file to hash.
        chunk_size: Read buffer size in bytes.

    Returns:
        Lowercase hex SHA256 digest (64 chars).

    Raises:
        OSError: If the file cannot be read.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify_wheel_integrity(wheel_path: Path, expected_sha256: str) -> bool:
    """Verify that *wheel_path* matches *expected_sha256*.

    The comparison is constant-time-ish via ``hmac.compare_digest`` to
    avoid leaking the expected hash through timing side channels. Both
    digests are normalized to lowercase before comparison.

    Args:
        wheel_path: Local path to the downloaded wheel.
        expected_sha256: The 64-char lowercase hex digest published by
            the release author (e.g. from ``SHA256SUMS.txt``).

    Returns:
        True if the actual hash matches the expected hash.

    Raises:
        OSError: If *wheel_path* cannot be read.
        ValueError: If *expected_sha256* is not a 64-char hex string.
    """
    if not expected_sha256 or len(expected_sha256) != 64:
        raise ValueError(
            f"expected_sha256 must be a 64-char hex string, got {len(expected_sha256)} chars"
        )

    actual = compute_sha256(wheel_path)
    # Normalize and compare in a timing-safe-ish way
    import hmac

    return hmac.compare_digest(actual.lower(), expected_sha256.lower())


def parse_sha256_line(line: str) -> tuple[str, str] | None:
    """Parse a single line of a GNU coreutils ``sha256sum`` file.

    Format: ``<hex_sha256>  <filename>`` (two spaces, sometimes '*' prefix
    for binary mode on GNU systems).

    Args:
        line: A non-empty, stripped line.

    Returns:
        Tuple of (filename, hex_sha256) or None if the line is unparseable.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Strip binary-mode marker if present
    if line.startswith("*"):
        line = line[1:]
    parts = line.split(None, 1)
    if len(parts) != 2:
        return None
    digest, filename = parts
    if len(digest) != 64:
        return None
    return filename.strip(), digest.lower()
