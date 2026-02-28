#!/usr/bin/env python3
"""Thin wrapper for close-build lifecycle with optional JSON output."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository/worktree root (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Run gates only")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip post-merge cleanup")
    parser.add_argument("--no-state-update", action="store_true", help="Skip STATE/BACKLOG updates")
    parser.add_argument("--json", action="store_true", help="Emit structured output")
    args = parser.parse_args()

    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "workflow" / "closure_pack.py")]
    if args.repo_root:
        cmd.extend(["--repo-root", args.repo_root])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.no_cleanup:
        cmd.append("--no-cleanup")
    if args.no_state_update:
        cmd.append("--no-state-update")

    proc = subprocess.run(
        cmd,
        cwd=Path(args.repo_root).resolve(),
        capture_output=True,
        text=True,
        check=False,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": proc.returncode == 0,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "",
                    "command": cmd,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
