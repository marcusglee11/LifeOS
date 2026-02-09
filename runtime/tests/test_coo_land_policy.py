from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runtime.tools.coo_land_policy import AllowlistError, is_eol_only_staged, normalize_allowlist


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def test_normalize_allowlist_sorts_and_deduplicates() -> None:
    result = normalize_allowlist(["b/path.py", "a/path.py", "b/path.py"])
    assert result == ["a/path.py", "b/path.py"]


def test_normalize_allowlist_rejects_empty_after_trim() -> None:
    with pytest.raises(AllowlistError, match="empty"):
        normalize_allowlist(["", "   "])


def test_normalize_allowlist_rejects_absolute_or_parent_paths() -> None:
    with pytest.raises(AllowlistError):
        normalize_allowlist(["/absolute/path.py"])
    with pytest.raises(AllowlistError):
        normalize_allowlist(["../escape.py"])


def test_is_eol_only_staged_true_for_crlf_flip(tmp_path: Path) -> None:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_text("a\nb\n", encoding="utf-8")
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    f.write_bytes(b"a\r\nb\r\n")
    _run(["git", "add", "sample.txt"], tmp_path)
    assert is_eol_only_staged(tmp_path) is True


def test_is_eol_only_staged_false_for_content_change(tmp_path: Path) -> None:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_text("a\nb\n", encoding="utf-8")
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    f.write_text("a\nc\n", encoding="utf-8")
    _run(["git", "add", "sample.txt"], tmp_path)
    assert is_eol_only_staged(tmp_path) is False
