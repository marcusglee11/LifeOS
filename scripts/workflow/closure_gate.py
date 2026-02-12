#!/usr/bin/env python3
"""Run closure gates (tests + doc stewardship) and output JSON verdict.

Designed for use by PreToolUse hooks. Outputs a single JSON object to stdout:
    {"passed": bool, "gate": str, "reason": str, "summary": str}

auto_fix is disabled: hooks must not create uncommitted changes mid-merge.
"""

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
    check_doc_stewardship,
    discover_changed_files,
    run_closure_tests,
)


def run_gate(repo_root: Path) -> dict:
    """Execute closure gates and return structured verdict."""
    changed_files = discover_changed_files(repo_root)

    # Gate 1: targeted tests
    test_result = run_closure_tests(repo_root, changed_files)
    if not test_result["passed"]:
        return {
            "passed": False,
            "gate": "tests",
            "reason": test_result["summary"],
            "summary": test_result["summary"],
        }

    # Gate 2: doc stewardship (no auto-fix in hook context)
    doc_result = check_doc_stewardship(repo_root, changed_files, auto_fix=False)
    if not doc_result["passed"]:
        errors = "; ".join(doc_result["errors"]) if doc_result["errors"] else "doc stewardship failed"
        return {
            "passed": False,
            "gate": "doc_stewardship",
            "reason": errors,
            "summary": f"Doc stewardship gate failed: {errors}",
        }

    # Build summary
    parts = [test_result["summary"]]
    if doc_result["required"]:
        parts.append("Doc stewardship passed.")
    else:
        parts.append("Doc stewardship skipped (no docs changed).")

    return {
        "passed": True,
        "gate": "all",
        "reason": "",
        "summary": " ".join(parts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    verdict = run_gate(repo_root)
    print(json.dumps(verdict))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
