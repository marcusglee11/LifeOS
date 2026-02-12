#!/usr/bin/env python3
"""Route changed files to targeted pytest commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.workflow_pack import discover_changed_files, route_targeted_tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Changed file paths. If omitted, auto-discover from git diff.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    files = args.files if args.files else discover_changed_files(repo_root)
    commands = route_targeted_tests(files)
    for command in commands:
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
