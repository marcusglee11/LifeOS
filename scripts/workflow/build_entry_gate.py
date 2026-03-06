#!/usr/bin/env python3
"""Build entry gate: qualifying file changes must be in a managed build worktree."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

QUALIFYING_PREFIXES = (
    "runtime/",
    "scripts/",
    "config/",
    "schemas/",
    "tests/",
    ".github/workflows/",
)
QUALIFYING_ROOT_FILES = frozenset({"pyproject.toml", "pytest.ini"})
QUALIFYING_ROOT_STARTSWITH = ("requirements",)
SCOPED_PREFIXES = ("build/", "fix/", "hotfix/", "spike/")


def _git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def _git_stdout(repo: Path, args: list[str]) -> str:
    r = _git(repo, args)
    return r.stdout.strip() if r.returncode == 0 else ""


def is_qualifying(path: str) -> bool:
    """Return True if this file path requires managed-build enforcement."""
    for prefix in QUALIFYING_PREFIXES:
        if path.startswith(prefix):
            return True
    name = Path(path).name
    if name in QUALIFYING_ROOT_FILES:
        return True
    for prefix in QUALIFYING_ROOT_STARTSWITH:
        if name.startswith(prefix):
            return True
    return False


def _get_staged_files(repo: Path) -> list[str]:
    out = _git_stdout(repo, ["diff", "--cached", "--name-only"])
    return [f for f in out.splitlines() if f.strip()]


def _load_bypass_token(git_common: Path, slug: str) -> dict | None:
    path = git_common / "lifeos" / "bypass" / f"{slug}.json"
    if not path.exists():
        return None
    try:
        token = json.loads(path.read_text())
        expires_str = token.get("expires_at_utc", "2000-01-01T00:00:00")
        expires = datetime.fromisoformat(expires_str)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            path.unlink(missing_ok=True)
            return None
        return token
    except Exception:
        return None


def _load_build_record(git_common: Path, slug: str) -> dict | None:
    path = git_common / "lifeos" / "builds" / f"{slug}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def check_gate(
    repo_path: Path | None = None,
    staged_files: list[str] | None = None,
) -> dict:
    """Run the build entry gate and return a structured verdict."""
    repo = repo_path or REPO_ROOT

    if staged_files is None:
        staged_files = _get_staged_files(repo)

    qualifying_files = [f for f in staged_files if is_qualifying(f)]

    if not qualifying_files:
        return {
            "passed": True,
            "qualifying": False,
            "reason": "No qualifying files staged.",
            "guidance": None,
            "branch": "",
            "on_worktree": False,
            "has_record": False,
            "bypass_active": False,
        }

    branch = _git_stdout(repo, ["symbolic-ref", "--short", "HEAD"])
    git_common_raw = _git_stdout(repo, ["rev-parse", "--git-common-dir"])

    git_common: Path | None = None
    on_worktree = False
    if git_common_raw:
        git_common = Path(git_common_raw)
        on_worktree = git_common.is_absolute()
        if not on_worktree:
            git_common = repo / git_common

    slug = branch.replace("/", "__") if branch else ""
    bypass_token = _load_bypass_token(git_common, slug) if git_common and slug else None
    bypass_active = bypass_token is not None
    record = _load_build_record(git_common, slug) if git_common and slug else None
    has_record = bool(record and record.get("status") == "active")

    def _pass_bypass() -> dict:
        return {
            "passed": True, "qualifying": True,
            "reason": "Bypass token active.",
            "guidance": None, "branch": branch, "on_worktree": on_worktree,
            "has_record": has_record, "bypass_active": True,
        }

    if not branch or not any(branch.startswith(p) for p in SCOPED_PREFIXES):
        if bypass_active:
            return _pass_bypass()
        return {
            "passed": False, "qualifying": True,
            "reason": f"Branch '{branch or '(detached)'}' is not a scoped build branch.",
            "guidance": "Run: python3 scripts/workflow/start_build.py <topic> [--kind ...]",
            "branch": branch, "on_worktree": on_worktree,
            "has_record": has_record, "bypass_active": False,
        }

    if bypass_active:
        return _pass_bypass()

    if not on_worktree:
        return {
            "passed": False, "qualifying": True,
            "reason": "Changes are in the primary worktree, not a linked worktree.",
            "guidance": "Run: python3 scripts/workflow/start_build.py --recover-primary",
            "branch": branch, "on_worktree": False,
            "has_record": has_record, "bypass_active": False,
        }

    if not has_record:
        return {
            "passed": False, "qualifying": True,
            "reason": "No active build record found for this branch.",
            "guidance": "Run: python3 scripts/workflow/start_build.py --recover-primary",
            "branch": branch, "on_worktree": on_worktree,
            "has_record": False, "bypass_active": False,
        }

    return {
        "passed": True, "qualifying": True,
        "reason": "All gate checks passed.",
        "guidance": None, "branch": branch, "on_worktree": on_worktree,
        "has_record": True, "bypass_active": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged-files", nargs="*", metavar="FILE",
        help="Explicit staged file list (skips git diff --cached)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON verdict to stdout")
    args = parser.parse_args()

    result = check_gate(staged_files=args.staged_files if args.staged_files else None)

    if args.json:
        print(json.dumps(result, indent=2))
        if not result["qualifying"]:
            return 2
        return 0 if result["passed"] else 1

    if not result["qualifying"]:
        return 2

    if not result["passed"]:
        print(f"❌ Build entry gate: {result['reason']}", file=sys.stderr)
        if result.get("guidance"):
            print(f"   {result['guidance']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
