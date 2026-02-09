"""Git cleanliness and evidence ignore proof checks."""

from __future__ import annotations

from pathlib import Path
import subprocess


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


def verify_repo_clean(repo_root: Path, code: str) -> None:
    result = _run_git(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode != 0:
        raise CleanlinessError(code, f"git status failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if output:
        raise CleanlinessError(code, f"Repository is dirty:\n{output}")


def verify_evidence_root_ignored(repo_root: Path, evidence_root: Path) -> str:
    try:
        target = evidence_root.relative_to(repo_root).as_posix()
    except ValueError:
        target = str(evidence_root)

    result = _run_git(repo_root, ["check-ignore", "-v", target])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    message = result.stderr.strip() if result.stderr.strip() else f"No ignore rule matched: {target}"
    raise CleanlinessError("EVIDENCE_ROOT_NOT_IGNORED", message)
