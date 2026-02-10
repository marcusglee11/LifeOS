from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runtime.tools.coo_land_policy import (
    AllowlistError,
    CleanCheckResult,
    _write_receipt,
    check_eol_config_compliance,
    check_repo_clean,
    is_eol_only_staged,
    is_eol_only_worktree,
    normalize_allowlist,
)


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
    """When core.autocrlf=true (the broken config), staging a CRLF file
    against an LF-committed original produces an EOL-only diff."""
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    _run(["git", "config", "core.autocrlf", "input"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_bytes(b"a\nb\n")  # store LF
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    # Now change autocrlf to true so git sees CRLF in index
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
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


# ---------------------------------------------------------------------------
# is_eol_only_worktree (unstaged variant)
# ---------------------------------------------------------------------------


def test_is_eol_only_worktree_true_for_crlf_flip(tmp_path: Path) -> None:
    """Without .gitattributes eol normalization, CRLF on disk shows as dirty."""
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
    # No .gitattributes -- raw binary comparison detects CRLF
    f = tmp_path / "sample.txt"
    f.write_bytes(b"a\nb\n")  # store LF
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    # Write CRLF to disk (unstaged)
    f.write_bytes(b"a\r\nb\r\n")
    assert is_eol_only_worktree(tmp_path) is True


def test_is_eol_only_worktree_crlf_invisible_with_gitattributes(tmp_path: Path) -> None:
    """With proper .gitattributes eol=lf, CRLF on disk is NOT dirty.
    This is the desired end state after the EOL fix."""
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
    (tmp_path / ".gitattributes").write_text("* text eol=lf\n", encoding="utf-8")
    _run(["git", "add", ".gitattributes"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_bytes(b"a\nb\n")
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    # CRLF on disk — but .gitattributes normalizes, so no diff visible
    f.write_bytes(b"a\r\nb\r\n")
    assert is_eol_only_worktree(tmp_path) is False  # No diff seen!


def test_is_eol_only_worktree_false_for_content_change(tmp_path: Path) -> None:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_text("a\nb\n", encoding="utf-8")
    _run(["git", "add", "sample.txt"], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    f.write_text("a\nc\n", encoding="utf-8")
    assert is_eol_only_worktree(tmp_path) is False


# ---------------------------------------------------------------------------
# check_eol_config_compliance
# ---------------------------------------------------------------------------


def test_config_compliance_false_is_compliant(tmp_path: Path) -> None:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
    compliant, detail = check_eol_config_compliance(tmp_path)
    assert compliant is True
    assert "compliant" in detail


def test_config_compliance_true_is_noncompliant(tmp_path: Path) -> None:
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "core.autocrlf", "true"], tmp_path)
    compliant, detail = check_eol_config_compliance(tmp_path)
    assert compliant is False
    assert "non-compliant" in detail


# ---------------------------------------------------------------------------
# check_repo_clean (integration)
# ---------------------------------------------------------------------------


def _init_clean_repo(tmp_path: Path) -> Path:
    """Create a minimal clean git repo with autocrlf=false and .gitattributes."""
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
    (tmp_path / ".gitattributes").write_text("* text eol=lf\n", encoding="utf-8")
    f = tmp_path / "sample.txt"
    f.write_text("hello\n", encoding="utf-8")
    _run(["git", "add", "."], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)
    return tmp_path


def test_check_repo_clean_on_clean_repo(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path)
    result = check_repo_clean(repo)
    assert result.clean is True
    assert result.reason == "CLEAN"
    assert result.file_count == 0


def test_check_repo_clean_detects_config_noncompliant(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path)
    _run(["git", "config", "core.autocrlf", "true"], repo)
    result = check_repo_clean(repo)
    assert result.clean is False
    assert result.reason == "CONFIG_NONCOMPLIANT"


def test_check_repo_clean_detects_eol_churn(tmp_path: Path) -> None:
    """Without .gitattributes normalization, CRLF on disk causes EOL_CHURN."""
    # Use a repo WITHOUT .gitattributes so CRLF is visible
    _run(["git", "init"], tmp_path)
    _run(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run(["git", "config", "user.name", "Test User"], tmp_path)
    _run(["git", "config", "core.autocrlf", "false"], tmp_path)
    f = tmp_path / "sample.txt"
    f.write_bytes(b"hello\n")  # LF in index
    _run(["git", "add", "."], tmp_path)
    _run(["git", "commit", "-m", "init"], tmp_path)

    f.write_bytes(b"hello\r\n")  # CRLF flip
    result = check_repo_clean(tmp_path)
    assert result.clean is False
    assert result.reason == "EOL_CHURN"
    assert result.file_count == 1


def test_check_repo_clean_detects_content_dirty(tmp_path: Path) -> None:
    repo = _init_clean_repo(tmp_path)
    f = repo / "sample.txt"
    f.write_text("changed content\n", encoding="utf-8")
    result = check_repo_clean(repo)
    assert result.clean is False
    assert result.reason == "CONTENT_DIRTY"
    assert result.file_count == 1


def test_write_receipt_emits_json(tmp_path: Path) -> None:
    """_write_receipt produces a valid JSON file with required fields."""
    import json

    repo = _init_clean_repo(tmp_path)
    result = check_repo_clean(repo)
    receipt = tmp_path / "receipt.json"
    _write_receipt(repo, result, receipt)

    assert receipt.exists()
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["result_clean"] is True
    assert data["result_reason"] == "CLEAN"
    assert "head_sha" in data
    assert len(data["head_sha"]) == 40
    assert "core_autocrlf_show_origin" in data
    assert "git_status_porcelain" in data

