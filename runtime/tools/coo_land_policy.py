#!/usr/bin/env python3
"""Policy helpers for deterministic `coo land` gating."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, NamedTuple


class AllowlistError(ValueError):
    """Raised when an evidence-derived allowlist violates policy."""


def _validate_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        raise AllowlistError("empty path in allowlist")
    if stripped.startswith("/"):
        raise AllowlistError(f"absolute path not allowed: {stripped}")
    p = Path(stripped)
    if any(part == ".." for part in p.parts):
        raise AllowlistError(f"path traversal not allowed: {stripped}")
    return stripped


def normalize_allowlist(lines: Iterable[str]) -> list[str]:
    unique = set()
    for line in lines:
        unique.add(_validate_path(line))
    ordered = sorted(unique)
    if not ordered:
        raise AllowlistError("allowlist is empty")
    return ordered


def allowlist_hash(paths: Iterable[str]) -> str:
    payload = "\n".join(paths) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_allowlist(path: Path) -> list[str]:
    if not path.exists():
        raise AllowlistError(f"allowlist file not found: {path}")
    return normalize_allowlist(path.read_text(encoding="utf-8").splitlines())


def _git_stdout(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def is_eol_only_staged(repo: Path) -> bool:
    normal_diff = _git_stdout(repo, ["diff", "--cached", "--no-color"])
    if not normal_diff.strip():
        return False
    ignored_diff = _git_stdout(
        repo,
        ["diff", "--cached", "--ignore-space-at-eol", "--ignore-cr-at-eol", "--no-color"],
    )
    return not ignored_diff.strip()


def is_eol_only_worktree(repo: Path) -> bool:
    """Check if *unstaged* working-tree diff is EOL-only."""
    normal_diff = _git_stdout(repo, ["diff", "--no-color"])
    if not normal_diff.strip():
        return False
    ignored_diff = _git_stdout(
        repo,
        ["diff", "--ignore-space-at-eol", "--ignore-cr-at-eol", "--no-color"],
    )
    return not ignored_diff.strip()


# ---------------------------------------------------------------------------
# Config-aware clean invariant
# ---------------------------------------------------------------------------

def get_effective_autocrlf(repo: Path) -> str:
    """Return the effective core.autocrlf value (local > global > system).

    Returns the string value ('true', 'false', 'input') or 'unset'.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.autocrlf"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return "unset"
    return proc.stdout.strip().lower()


def check_eol_config_compliance(repo: Path) -> tuple[bool, str]:
    """Check that EOL-related git config is compliant.

    Compliant means core.autocrlf is 'false' (not 'true' or 'input').
    Returns (compliant, detail_string).
    """
    value = get_effective_autocrlf(repo)
    if value == "false":
        return True, f"core.autocrlf={value} (compliant)"
    return False, f"core.autocrlf={value} (non-compliant; must be 'false')"


class CleanCheckResult(NamedTuple):
    """Result of a full repo clean-invariant check."""

    clean: bool
    reason: str  # CLEAN | EOL_CHURN | CONTENT_DIRTY | CONFIG_NONCOMPLIANT
    file_count: int
    detail: str


def check_repo_clean(repo: Path) -> CleanCheckResult:
    """Full clean-invariant check: config compliance + working-tree state.

    Checks (in order):
    1. EOL config compliance (core.autocrlf must be false)
    2. Working-tree cleanliness (git status --porcelain)
    3. If dirty, classifies as EOL_CHURN vs CONTENT_DIRTY
    """
    # 1. Config compliance
    compliant, config_detail = check_eol_config_compliance(repo)
    if not compliant:
        return CleanCheckResult(
            clean=False,
            reason="CONFIG_NONCOMPLIANT",
            file_count=0,
            detail=config_detail,
        )

    # 2. Working-tree status
    status_output = _git_stdout(repo, ["status", "--porcelain=v1"]).strip()
    if not status_output:
        return CleanCheckResult(
            clean=True,
            reason="CLEAN",
            file_count=0,
            detail="working tree clean; " + config_detail,
        )

    file_count = len(status_output.splitlines())

    # 3. Classify: EOL-only or content?
    try:
        eol_only = is_eol_only_worktree(repo)
    except RuntimeError:
        eol_only = False

    if eol_only:
        return CleanCheckResult(
            clean=False,
            reason="EOL_CHURN",
            file_count=file_count,
            detail=(
                f"{file_count} files with EOL-only modifications; "
                "run: git add --renormalize . && git checkout -- ."
            ),
        )
    return CleanCheckResult(
        clean=False,
        reason="CONTENT_DIRTY",
        file_count=file_count,
        detail=f"{file_count} files with content modifications",
    )


def cli_allowlist(args: argparse.Namespace) -> int:
    try:
        ordered = load_allowlist(Path(args.input))
    except AllowlistError as exc:
        print(f"ALLOWLIST_ERROR: {exc}", file=sys.stderr)
        return 2
    Path(args.output).write_text("\n".join(ordered) + "\n", encoding="utf-8")
    Path(args.hash_output).write_text(allowlist_hash(ordered) + "\n", encoding="utf-8")
    return 0


def cli_eol_only(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    try:
        result = is_eol_only_staged(repo)
    except Exception as exc:
        print(f"EOL_CHECK_ERROR: {exc}", file=sys.stderr)
        return 2
    print("1" if result else "0")
    return 0


def cli_clean_check(args: argparse.Namespace) -> int:
    """CLI: full clean-invariant check (config + status)."""
    repo = Path(args.repo)
    try:
        result = check_repo_clean(repo)
    except Exception as exc:
        print(f"CLEAN_CHECK_ERROR: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "receipt", None):
        _write_receipt(repo, result, Path(args.receipt))

    if result.clean:
        print(f"CLEAN: {result.detail}")
        return 0
    print(f"BLOCKED ({result.reason}): {result.detail}")
    if args.auto_fix and result.reason == "CONFIG_NONCOMPLIANT":
        print("AUTO_FIX: setting core.autocrlf=false at repo level")
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "core.autocrlf", "false"],
            check=True,
        )
        print("AUTO_FIX: re-running clean check...")
        return cli_clean_check(args)
    return 1


def _write_receipt(repo: Path, result: CleanCheckResult, receipt_path: Path) -> None:
    """Emit a machine-verifiable JSON receipt for clean-check."""
    head_sha = _git_stdout(repo, ["rev-parse", "HEAD"]).strip()
    status_porcelain = _git_stdout(repo, ["status", "--porcelain=v1"]).strip()

    # core.autocrlf --show-origin (captures provenance)
    ac_proc = subprocess.run(
        ["git", "-C", str(repo), "config", "--show-origin", "--get", "core.autocrlf"],
        check=False, capture_output=True, text=True,
    )
    autocrlf_show_origin = ac_proc.stdout.strip() if ac_proc.returncode == 0 else "(unset)"

    receipt = {
        "repo": str(repo.resolve()),
        "head_sha": head_sha,
        "git_status_porcelain": status_porcelain or "(empty)",
        "core_autocrlf_show_origin": autocrlf_show_origin,
        "result_clean": result.clean,
        "result_reason": result.reason,
        "result_file_count": result.file_count,
        "result_detail": result.detail,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Policy helpers for coo land.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    allowlist_parser = sub.add_parser("allowlist", help="Normalize and hash allowlist file.")
    allowlist_parser.add_argument("--input", required=True)
    allowlist_parser.add_argument("--output", required=True)
    allowlist_parser.add_argument("--hash-output", required=True)
    allowlist_parser.set_defaults(func=cli_allowlist)

    eol_parser = sub.add_parser("eol-only", help="Check staged diff for EOL-only changes.")
    eol_parser.add_argument("--repo", required=True)
    eol_parser.set_defaults(func=cli_eol_only)

    clean_parser = sub.add_parser(
        "clean-check",
        help="Full clean-invariant check (config + working-tree status).",
    )
    clean_parser.add_argument("--repo", required=True)
    clean_parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Auto-fix config non-compliance (sets core.autocrlf=false locally).",
    )
    clean_parser.add_argument(
        "--receipt",
        metavar="PATH",
        help="Write machine-verifiable JSON receipt to PATH.",
    )
    clean_parser.set_defaults(func=cli_clean_check)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
