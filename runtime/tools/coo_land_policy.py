#!/usr/bin/env python3
"""Policy helpers for deterministic `coo land` gating."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Iterable


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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
