"""Git cleanliness and evidence ignore proof checks."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Dict


class CleanlinessError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _to_git_target(repo_root: Path, target_path: Path) -> str:
    try:
        return target_path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(target_path)


def _check_ignored(repo_root: Path, target_path: Path, code: str) -> str:
    target = _to_git_target(repo_root, target_path)
    result = _run_git(repo_root, ["check-ignore", "-v", target])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    message = result.stderr.strip() if result.stderr.strip() else f"No ignore rule matched: {target}"
    raise CleanlinessError(code, message)


def verify_repo_clean(repo_root: Path, code: str) -> None:
    result = _run_git(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode != 0:
        raise CleanlinessError(code, f"git status failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if output:
        raise CleanlinessError(code, f"Repository is dirty:\n{output}")


def verify_evidence_root_ignored(repo_root: Path, evidence_root: Path) -> str:
    return _check_ignored(repo_root, evidence_root, code="EVIDENCE_ROOT_NOT_IGNORED")


def verify_output_roots_ignored(
    repo_root: Path,
    run_root: Path,
    attempt_dir: Path,
    evidence_root: Path,
) -> Dict[str, str]:
    """
    Verify ignore coverage for all output roots.

    P0.8 hardening: proving ignore only for evidence_root is insufficient, because
    unignored attempt/run roots can still dirty the workspace.
    """
    return {
        "run_root": _check_ignored(repo_root, run_root, code="EVIDENCE_ROOT_NOT_IGNORED"),
        "attempt_dir": _check_ignored(repo_root, attempt_dir, code="EVIDENCE_ROOT_NOT_IGNORED"),
        "evidence_root": _check_ignored(repo_root, evidence_root, code="EVIDENCE_ROOT_NOT_IGNORED"),
    }
