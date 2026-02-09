from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from runtime.validation.cleanliness import CleanlinessError, verify_evidence_root_ignored, verify_repo_clean


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def test_verify_repo_clean_detects_dirty_repo(git_repo: Path) -> None:
    (git_repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(CleanlinessError) as exc:
        verify_repo_clean(git_repo, code="DIRTY_REPO_PRE")

    assert exc.value.code == "DIRTY_REPO_PRE"


def test_verify_evidence_root_ignore_proof(git_repo: Path) -> None:
    evidence_root = git_repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    proof = verify_evidence_root_ignored(git_repo, evidence_root)
    assert ".gitignore" in proof


def test_verify_evidence_root_ignore_failure(git_repo: Path) -> None:
    evidence_root = git_repo / "non_ignored" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(CleanlinessError) as exc:
        verify_evidence_root_ignored(git_repo, evidence_root)

    assert exc.value.code == "EVIDENCE_ROOT_NOT_IGNORED"
