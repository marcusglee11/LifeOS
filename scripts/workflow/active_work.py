#!/usr/bin/env python3
"""Manage .context/active_work.yaml compact context artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    read_active_work,
    write_active_work,
)


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _parse_finding(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split(":", 2)]
    if len(parts) != 3 or any(not part for part in parts):
        raise argparse.ArgumentTypeError(
            "finding must be formatted as id:severity:status"
        )
    return {"id": parts[0], "severity": parts[1], "status": parts[2]}


def cmd_refresh(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    branch = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    commit_lines = _git_stdout(
        repo_root,
        ["log", "--oneline", f"-n{args.commit_limit}"],
    ).splitlines()

    payload = build_active_work_payload(
        branch=branch,
        latest_commits=commit_lines,
        focus=args.focus or [],
        tests_targeted=args.test or [],
        findings_open=args.finding or [],
    )
    output_path = write_active_work(repo_root, payload)
    print(output_path)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    payload = read_active_work(repo_root)
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_refresh = sub.add_parser("refresh", help="Refresh active context from git + flags.")
    p_refresh.add_argument("--commit-limit", type=int, default=5)
    p_refresh.add_argument("--focus", action="append", default=[])
    p_refresh.add_argument("--test", action="append", default=[])
    p_refresh.add_argument("--finding", action="append", type=_parse_finding, default=[])
    p_refresh.set_defaults(func=cmd_refresh)

    p_show = sub.add_parser("show", help="Print active_work.yaml normalized content.")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
