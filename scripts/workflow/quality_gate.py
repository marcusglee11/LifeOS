#!/usr/bin/env python3
"""Run manifest-driven code quality checks for LifeOS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import (  # noqa: E402
    doctor_quality_tools,
    load_quality_manifest,
    run_quality_gates,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check quality tool availability.")
    doctor_parser.add_argument("--repo-root", default=".", help="Repository root (default: current directory).")
    doctor_parser.add_argument("--json", action="store_true", help="Emit JSON output.")

    for name, help_text in (("check", "Run quality checks."), ("fix", "Apply safe auto-fixes.")):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--repo-root", default=".", help="Repository root (default: current directory).")
        sub.add_argument("--scope", choices=("changed", "repo"), default="changed")
        sub.add_argument(
            "--changed-file",
            action="append",
            default=[],
            dest="changed_files",
            help="Explicit changed file path. Repeatable.",
        )
        sub.add_argument("--json", action="store_true", help="Emit JSON output.")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "doctor":
        payload = doctor_quality_tools(repo_root)
    else:
        load_quality_manifest(repo_root)
        payload = run_quality_gates(
            repo_root,
            changed_files=args.changed_files,
            scope=args.scope,
            fix=args.command == "fix",
        )

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload["summary"])
        for row in payload.get("results", []):
            status = "PASS" if row.get("passed") else "FAIL"
            mode = row.get("mode", "blocking")
            print(f"- {status} [{mode}] {row.get('tool')}")
            details = str(row.get("details", "")).strip()
            if details:
                print(f"  {details}")

    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
