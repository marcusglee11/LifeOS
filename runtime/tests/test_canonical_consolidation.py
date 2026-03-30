"""
Canonical Consolidation Tests — verify all sha256/canonical_json go through
runtime.util.canonical and produce consistent results.
"""

import hashlib
from pathlib import Path

import pytest

from runtime.util.canonical import (
    canonical_json,
    canonical_json_str,
    sha256_file,  # NEW — does not exist yet
)


class TestSha256File:
    """Test the new sha256_file function in canonical.py."""

    def test_sha256_file_basic(self, tmp_path):
        """Hash a known file and verify against manual hashlib."""
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert sha256_file(f) == expected

    def test_sha256_file_empty(self, tmp_path):
        """Empty file should hash to sha256 of empty bytes."""
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert sha256_file(f) == expected

    def test_sha256_file_large(self, tmp_path):
        """File larger than chunk size should still hash correctly."""
        f = tmp_path / "large.bin"
        data = b"x" * 100_000
        f.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert sha256_file(f) == expected

    def test_sha256_file_missing_raises(self, tmp_path):
        """Missing file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            sha256_file(tmp_path / "nonexistent.txt")

    def test_sha256_file_accepts_str(self, tmp_path):
        """Should accept str path as well as Path."""
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert sha256_file(str(f)) == expected


class TestCanonicalJsonConsistency:
    """Verify canonical_json produces identical output regardless of entry point."""

    def test_bytes_and_str_agree(self):
        """canonical_json (bytes) and canonical_json_str (str) must agree."""
        obj = {"z": 1, "a": 2, "m": [3, 1]}
        assert canonical_json(obj).decode("utf-8") == canonical_json_str(obj)

    def test_sorted_keys(self):
        """Keys must be lexicographically sorted."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_json_str(obj)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_no_nan_allowed(self):
        """NaN must raise ValueError (fail-closed)."""
        with pytest.raises(ValueError):
            canonical_json({"val": float("nan")})

    def test_no_trailing_newline(self):
        """Canonical JSON must NOT have trailing newline."""
        result = canonical_json_str({"a": 1})
        assert not result.endswith("\n")

    def test_ensure_ascii_false(self):
        """Non-ASCII chars must be preserved, not escaped."""
        obj = {"name": "日本語"}
        result = canonical_json_str(obj)
        assert "日本語" in result
        assert "\\u" not in result


class TestNoDuplicateImplementations:
    """Verify that known duplicate files now import from canonical."""

    def test_agents_api_uses_canonical(self):
        """runtime/agents/api.py should import canonical_json from util."""
        import runtime.agents.api as api_mod

        source = Path(api_mod.__file__).read_text(encoding="utf-8")
        assert "from runtime.util.canonical import" in source, (
            "runtime/agents/api.py should import from runtime.util.canonical"
        )

    def test_validation_reporting_uses_canonical(self):
        """runtime/validation/reporting.py should import from util."""
        import runtime.validation.reporting as rep_mod

        source = Path(rep_mod.__file__).read_text(encoding="utf-8")
        assert "from runtime.util.canonical import" in source, (
            "runtime/validation/reporting.py should import from runtime.util.canonical"
        )

    def test_cli_uses_canonical(self):
        """runtime/cli.py should import from util.canonical."""
        import runtime.cli as cli_mod

        source = Path(cli_mod.__file__).read_text(encoding="utf-8")
        assert "from runtime.util.canonical import" in source, (
            "runtime/cli.py should import from runtime.util.canonical"
        )
