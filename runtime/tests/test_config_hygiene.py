"""
Config hygiene tests for repo-level test configuration accuracy.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestRequirements:
    """Verify requirements constraints match installed runtime versions."""

    def test_pytest_constraint_allows_installed_version(self):
        req_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

        pytest_line = None
        for line in req_text.splitlines():
            if line.startswith("pytest"):
                pytest_line = line
                break

        assert pytest_line is not None, "No pytest constraint line found in requirements.txt"

        installed = pytest.__version__
        major = int(installed.split(".")[0])
        upper_match = re.search(r"<(\d+)", pytest_line)
        assert upper_match, f"No upper bound found in pytest constraint: {pytest_line}"
        upper = int(upper_match.group(1))

        assert major < upper, (
            f"Installed pytest {installed} violates constraint {pytest_line} "
            f"(expected major < {upper})"
        )


class TestPyprojectIgnores:
    """Verify pyproject ignore list reflects current passing tests."""

    def test_e2e_smoke_timeout_not_ignored(self):
        content = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "test_e2e_smoke_timeout.py" not in content, (
            "test_e2e_smoke_timeout.py is still ignored in pyproject.toml "
            "but is expected to run."
        )
