"""Tests for lupe.security.integrity — SHA256 verification for auto-updates.

Critical: ensures that a tampered wheel cannot be installed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


class TestComputeSha256:
    def test_empty_file(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256

        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        # SHA256 of empty input is a well-known constant
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert compute_sha256(p) == expected

    def test_known_payload(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256

        p = tmp_path / "data.bin"
        p.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert compute_sha256(p) == expected

    def test_large_file_streaming(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256

        p = tmp_path / "large.bin"
        # 1 MB of zeros
        p.write_bytes(b"\x00" * (1024 * 1024))
        expected = hashlib.sha256(b"\x00" * (1024 * 1024)).hexdigest()
        assert compute_sha256(p) == expected

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256

        with pytest.raises(OSError):
            compute_sha256(tmp_path / "does-not-exist")


class TestVerifyWheelIntegrity:
    def test_match_returns_true(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256, verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"fake wheel content for testing")
        digest = compute_sha256(wheel)
        assert verify_wheel_integrity(wheel, digest) is True

    def test_mismatch_returns_false(self, tmp_path: Path) -> None:
        from lupe.security.integrity import verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"original content")
        # A clearly-wrong but well-formed SHA256
        wrong = "0" * 64
        assert verify_wheel_integrity(wheel, wrong) is False

    def test_case_insensitive(self, tmp_path: Path) -> None:
        from lupe.security.integrity import compute_sha256, verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"data")
        digest = compute_sha256(wheel)
        # Uppercase should still match
        assert verify_wheel_integrity(wheel, digest.upper()) is True

    def test_invalid_expected_length_raises(self, tmp_path: Path) -> None:
        from lupe.security.integrity import verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"x")
        with pytest.raises(ValueError, match="64-char"):
            verify_wheel_integrity(wheel, "tooshort")

    def test_empty_expected_raises(self, tmp_path: Path) -> None:
        from lupe.security.integrity import verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"x")
        with pytest.raises(ValueError):
            verify_wheel_integrity(wheel, "")

    def test_tampered_wheel_detected(self, tmp_path: Path) -> None:
        """Critical: a wheel modified after the digest was published must fail."""
        from lupe.security.integrity import compute_sha256, verify_wheel_integrity

        wheel = tmp_path / "test.whl"
        wheel.write_bytes(b"clean wheel code")
        clean_digest = compute_sha256(wheel)

        # Attacker overwrites the wheel with a payload
        wheel.write_bytes(b"EVIL PAYLOAD \nrm -rf /")

        assert verify_wheel_integrity(wheel, clean_digest) is False


class TestParseSha256Line:
    def test_valid_line(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        digest = "a" * 64
        result = parse_sha256_line(f"{digest}  wheel.whl")
        assert result == ("wheel.whl", digest)

    def test_valid_line_binary_mode(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        digest = "b" * 64
        result = parse_sha256_line(f"*{digest}  wheel.whl")
        assert result == ("wheel.whl", digest)

    def test_valid_line_with_path(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        digest = "c" * 64
        result = parse_sha256_line(f"{digest}  dist/wheel.whl")
        assert result == ("dist/wheel.whl", digest)

    def test_comment_line(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        assert parse_sha256_line("# this is a comment") is None

    def test_empty_line(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        assert parse_sha256_line("") is None

    def test_malformed_line(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        assert parse_sha256_line("not a valid sha256 line") is None

    def test_wrong_length_digest(self) -> None:
        from lupe.security.integrity import parse_sha256_line

        assert parse_sha256_line(f"{'a' * 32}  wheel.whl") is None
