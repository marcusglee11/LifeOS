#!/usr/bin/env python3
"""CLI wrapper for COO sync-check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from runtime.orchestration.coo.sync_check import render_sync_check, run_sync_check
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from runtime.orchestration.coo.sync_check import render_sync_check, run_sync_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect structured COO state drift")
    parser.add_argument("--json", action="store_true", help="Output drift report as JSON")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Override repository root for testing",
    )
    args = parser.parse_args(argv)

    result = run_sync_check(args.repo_root.resolve())
    print(render_sync_check(result, as_json=args.json))
    return 1 if result["drift_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
