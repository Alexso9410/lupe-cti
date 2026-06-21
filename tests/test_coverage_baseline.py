"""Tests for coverage infrastructure (PR-0, Task 0.1)."""
from __future__ import annotations

import subprocess
import sys


class TestCoverageBaseline:
    def test_pytest_cov_installed(self) -> None:
        """Verify pytest-cov plugin is importable."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--co", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # pytest --co should succeed (just collecting, not running)
        assert result.returncode == 0, f"pytest collection failed: {result.stderr}"

    def test_coverage_source_configured(self) -> None:
        """Verify pyproject.toml has coverage source configured."""
        import tomllib
        from pathlib import Path

        pyproject = Path("pyproject.toml")
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        coverage = data.get("tool", {}).get("coverage", {})
        run_config = coverage.get("run", {})
        assert "lupe" in run_config.get("source", []), (
            "coverage.run.source must include 'lupe'"
        )
