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

from runtime.tools.closure_policy import (  # noqa: E402
    CLOSURE_POLICY_VERSION,
    get_tier_execution_policy,
    resolve_closure_tier,
)
from runtime.tools.workflow_pack import (  # noqa: E402
    check_doc_stewardship,
    run_closure_tests,
    run_quality_gates,
)


def run_gate(repo_root: Path, branch: str | None = None) -> dict:
    """Execute closure gates and return structured verdict."""
    tier_info = resolve_closure_tier(repo_root, head_ref=branch or "HEAD")
    closure_tier = tier_info["closure_tier"]
    policy = get_tier_execution_policy(closure_tier)
    verdict = {
        "passed": False,
        "gate": "classification",
        "reason": "",
        "summary": "",
        "closure_policy_version": CLOSURE_POLICY_VERSION,
        "closure_tier": closure_tier,
        "selected_checks": list(policy["selected_checks"]),
        "skipped_checks": list(policy["skipped_checks"]),
        "post_merge_updates_suppressed": bool(policy["post_merge_updates_suppressed"]),
    }

    if tier_info["outcome"] == "no_changes":
        verdict.update(
            {
                "passed": True,
                "gate": "no_changes",
                "summary": "No changes to close.",
            }
        )
        return verdict

    changed_files = list(tier_info["changed_paths"])
    if tier_info["outcome"] == "full_fallback":
        verdict["summary"] = f"Classification fell back to full: {tier_info['classification_reason']}"

    if policy["run_doc_stewardship"]:
        doc_result = check_doc_stewardship(repo_root, changed_files, auto_fix=False)
        if not doc_result["passed"]:
            errors = "; ".join(doc_result["errors"]) if doc_result["errors"] else "doc stewardship failed"
            verdict.update(
                {
                    "gate": "doc_stewardship",
                    "reason": errors,
                    "summary": f"Doc stewardship gate failed: {errors}",
                }
            )
            return verdict

    if policy["quality_tools"]:
        quality_result = run_quality_gates(
            repo_root,
            changed_files,
            scope="changed",
            fix=False,
            tool_names=policy["quality_tools"],
        )
    elif policy["run_general_quality_gate"]:
        quality_result = run_quality_gates(repo_root, changed_files, scope="changed", fix=False)
    else:
        quality_result = {"passed": True, "summary": "Quality checks skipped.", "results": []}

    if not quality_result["passed"]:
        blocking_details = [
            row["details"]
            for row in quality_result["results"]
            if (not row["passed"]) and row["mode"] == "blocking" and row["details"]
        ]
        errors = "; ".join(str(item) for item in blocking_details) or quality_result["summary"]
        verdict.update(
            {
                "gate": "quality",
                "reason": errors,
                "summary": f"Quality gate failed: {quality_result['summary']}",
            }
        )
        return verdict

    test_result = run_closure_tests(
        repo_root,
        changed_files,
        closure_tier=closure_tier,
    )
    if not test_result["passed"]:
        verdict.update(
            {
                "gate": "tests",
                "reason": test_result["summary"],
                "summary": test_result["summary"],
            }
        )
        return verdict

    parts: list[str] = []
    if tier_info["outcome"] == "full_fallback":
        parts.append(verdict["summary"])
    parts.append(test_result["summary"])
    parts.append(quality_result["summary"])
    parts.append(
        "Doc stewardship passed." if policy["run_doc_stewardship"] else "Doc stewardship skipped."
    )
    verdict.update(
        {
            "passed": True,
            "gate": "all",
            "reason": "",
            "summary": " ".join(part for part in parts if part),
        }
    )
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Build branch being merged (enables branch-diff file detection from main context).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    verdict = run_gate(repo_root, branch=args.branch)
    print(json.dumps(verdict))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
