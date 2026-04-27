#!/usr/bin/env python3
"""Phase 0 validator for LifeOS Work Management Framework v0.1.

Validates WI-YYYY-NNN items in config/tasks/backlog.yaml against the WMF invariants
defined in docs/02_protocols/Work_Management_Framework_v0.1.md.

Exit 0 = no violations. Exit 1 = violations found.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_WMF_ID_RE = re.compile(r"^WI-\d{4}-\d{3}$")

VALID_WMF_STATUSES = {
    "INTAKE",
    "TRIAGED",
    "READY",
    "DISPATCHED",
    "REVIEW",
    "CLOSED",
    "BLOCKED",
    "DEFERRED",
    "REJECTED",
    "DUPLICATE",
    "SUPERSEDED",
}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_RISKS = {"low", "med", "high"}
VALID_TASK_TYPES = {"build", "content", "hygiene"}
VALID_PLAN_MODES = {"none", "plan_lite", "formal"}

# Statuses where github_issue is required.
STATUSES_REQUIRING_GITHUB_ISSUE = VALID_WMF_STATUSES - {"INTAKE"}

# Statuses where acceptance_criteria or acceptance_ref is required.
STATUSES_REQUIRING_ACCEPTANCE = {"READY", "DISPATCHED"}

DERIVED_HEADER_MARKER = "DERIVED VIEW"


@dataclass
class WMFViolation:
    item_id: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.item_id}] {self.field}: {self.message}"


def _find_repo_root() -> Optional[Path]:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return None


def _acceptance_criteria_valid(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and all(isinstance(v, str) and v.strip() for v in value)
    return False


def _check_backlog_v1_compat(item: Dict[str, Any], item_id: str) -> List[WMFViolation]:
    """Check that a WMF item has all backlog.v1 required fields."""
    violations: List[WMFViolation] = []
    required_fields = [
        "id",
        "title",
        "priority",
        "risk",
        "status",
        "task_type",
        "objective_ref",
        "created_at",
    ]
    for field in required_fields:
        if not item.get(field):
            violations.append(
                WMFViolation(
                    item_id, field, f"required backlog.v1 field '{field}' is missing or empty"
                )
            )

    scope_paths = item.get("scope_paths")
    if scope_paths is not None and not isinstance(scope_paths, list):
        violations.append(WMFViolation(item_id, "scope_paths", "must be a list"))

    tags = item.get("tags")
    if tags is not None and not isinstance(tags, list):
        violations.append(WMFViolation(item_id, "tags", "must be a list"))

    risk = item.get("risk", "")
    if risk and risk not in VALID_RISKS:
        violations.append(WMFViolation(item_id, "risk", f"{risk!r} not in {sorted(VALID_RISKS)}"))

    task_type = item.get("task_type", "")
    if task_type and task_type not in VALID_TASK_TYPES:
        violations.append(
            WMFViolation(item_id, "task_type", f"{task_type!r} not in {sorted(VALID_TASK_TYPES)}")
        )

    return violations


def validate_backlog(
    backlog_path: Path,
    workstreams_path: Path,
) -> List[WMFViolation]:
    """Validate all WMF candidates in backlog_path. Return list of violations."""
    violations: List[WMFViolation] = []

    with open(backlog_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    tasks = raw.get("tasks") or [] if isinstance(raw, dict) else []

    # Load valid workstream slugs.
    valid_workstreams: set[str] = set()
    if workstreams_path.exists():
        with open(workstreams_path, "r", encoding="utf-8") as f:
            ws_raw = yaml.safe_load(f)
        if isinstance(ws_raw, dict):
            valid_workstreams = set(ws_raw.keys())

    seen_ids: set[str] = set()

    for item in tasks:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()

        # Only check WMF candidates (id starts with "WI-").
        if not item_id.startswith("WI-"):
            continue

        # Check 1: ID format.
        if not _WMF_ID_RE.match(item_id):
            violations.append(
                WMFViolation(
                    item_id, "id", f"invalid WMF id format. Expected WI-YYYY-NNN, got {item_id!r}"
                )
            )
            continue  # Can't meaningfully validate the rest with a malformed ID.

        # Check 2: Unique IDs.
        if item_id in seen_ids:
            violations.append(WMFViolation(item_id, "id", "duplicate WI ID"))
        seen_ids.add(item_id)

        # Check 0: backlog.v1 compatibility.
        violations.extend(_check_backlog_v1_compat(item, item_id))

        status = str(item.get("status", "")).strip()

        # Check 3: Valid WMF status.
        if status not in VALID_WMF_STATUSES:
            violations.append(WMFViolation(item_id, "status", f"{status!r} not in WMF status set"))

        # Check 4: Valid priority.
        priority = str(item.get("priority", "")).strip()
        if priority not in VALID_PRIORITIES:
            violations.append(
                WMFViolation(item_id, "priority", f"{priority!r} not in {sorted(VALID_PRIORITIES)}")
            )

        # Check 5: github_issue required at TRIAGED+.
        if status in STATUSES_REQUIRING_GITHUB_ISSUE:
            if not item.get("github_issue"):
                violations.append(
                    WMFViolation(item_id, "github_issue", f"required at status {status!r}")
                )

        # Check 6: workstream required and must be valid.
        workstream = item.get("workstream")
        if not workstream or not str(workstream).strip():
            violations.append(WMFViolation(item_id, "workstream", "field is required"))
        elif valid_workstreams and str(workstream).strip() not in valid_workstreams:
            violations.append(
                WMFViolation(
                    item_id,
                    "workstream",
                    f"{workstream!r} not in workstreams.yaml ({sorted(valid_workstreams)})",
                )
            )

        # Check 7: acceptance_criteria or acceptance_ref at READY/DISPATCHED.
        if status in STATUSES_REQUIRING_ACCEPTANCE:
            ac = item.get("acceptance_criteria")
            ar = item.get("acceptance_ref")
            if not _acceptance_criteria_valid(ac) and not (ar and str(ar).strip()):
                violations.append(
                    WMFViolation(
                        item_id,
                        "acceptance_criteria",
                        f"required (or acceptance_ref) at status {status!r}",
                    )
                )

        # Check 8: plan_mode required and must be valid enum.
        plan_mode = item.get("plan_mode")
        if plan_mode is None or plan_mode == "":
            violations.append(
                WMFViolation(
                    item_id, "plan_mode", f"required; must be one of {sorted(VALID_PLAN_MODES)}"
                )
            )
        elif str(plan_mode).strip() not in VALID_PLAN_MODES:
            violations.append(
                WMFViolation(
                    item_id, "plan_mode", f"{plan_mode!r} not in {sorted(VALID_PLAN_MODES)}"
                )
            )
        else:
            plan_mode = str(plan_mode).strip()

            # Check 9: plan_mode=formal requires plan_path. No exceptions.
            if plan_mode == "formal" and not item.get("plan_path"):
                violations.append(
                    WMFViolation(item_id, "plan_path", "required when plan_mode=formal")
                )

        # Check 10: P0 expedited + CLOSED requires followup_backlog_item.
        plan_followup_required = bool(item.get("plan_followup_required", False))
        is_p0_expedited = (
            priority == "P0"
            and isinstance(plan_mode, str)
            and plan_mode == "plan_lite"
            and plan_followup_required
        )
        if is_p0_expedited and status == "CLOSED":
            if not item.get("followup_backlog_item"):
                violations.append(
                    WMFViolation(
                        item_id,
                        "followup_backlog_item",
                        "required before CLOSED on P0 expedited items",
                    )
                )

        # Check 11: CLOSED requires closure_evidence.
        if status == "CLOSED":
            ce = item.get("closure_evidence")
            if not ce or not isinstance(ce, list) or len(ce) == 0:
                violations.append(
                    WMFViolation(
                        item_id, "closure_evidence", "required and must be non-empty list at CLOSED"
                    )
                )
            else:
                # Check 12: each entry has type, ref, note (all non-empty strings).
                for i, entry in enumerate(ce):
                    if not isinstance(entry, dict):
                        violations.append(
                            WMFViolation(item_id, f"closure_evidence[{i}]", "must be a dict")
                        )
                        continue
                    for key in ("type", "ref", "note"):
                        val = entry.get(key)
                        if not val or not str(val).strip():
                            violations.append(
                                WMFViolation(
                                    item_id,
                                    f"closure_evidence[{i}].{key}",
                                    "required and non-empty",
                                )
                            )

    return violations


def validate_backlog_md_header(backlog_md_path: Path) -> List[WMFViolation]:
    """Check 13: BACKLOG.md must contain derived/view-only header."""
    violations: List[WMFViolation] = []
    if not backlog_md_path.exists():
        return violations
    content = backlog_md_path.read_text(encoding="utf-8")
    if DERIVED_HEADER_MARKER not in content:
        violations.append(
            WMFViolation(
                "BACKLOG.md",
                "header",
                f"derived/view-only header marker {DERIVED_HEADER_MARKER!r} not found",
            )
        )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backlog", default=None, help="Path to backlog.yaml (default: auto-detect from repo root)"
    )
    parser.add_argument(
        "--workstreams", default=None, help="Path to workstreams.yaml (default: auto-detect)"
    )
    parser.add_argument(
        "--backlog-md", default=None, help="Path to BACKLOG.md (default: auto-detect)"
    )
    parser.add_argument(
        "--repo-root", default=None, help="Repo root (default: git rev-parse --show-toplevel)"
    )
    args = parser.parse_args()

    repo_root: Optional[Path] = Path(args.repo_root) if args.repo_root else _find_repo_root()
    if repo_root is None:
        print("ERROR: could not determine repo root. Use --repo-root.", file=sys.stderr)
        return 1

    backlog_path = (
        Path(args.backlog) if args.backlog else repo_root / "config" / "tasks" / "backlog.yaml"
    )
    workstreams_path = (
        Path(args.workstreams) if args.workstreams else repo_root / "artifacts" / "workstreams.yaml"
    )
    backlog_md_path = (
        Path(args.backlog_md) if args.backlog_md else repo_root / "docs" / "11_admin" / "BACKLOG.md"
    )

    all_violations: List[WMFViolation] = []

    if not backlog_path.exists():
        print(f"ERROR: backlog file not found: {backlog_path}", file=sys.stderr)
        return 1

    all_violations.extend(validate_backlog(backlog_path, workstreams_path))
    all_violations.extend(validate_backlog_md_header(backlog_md_path))

    if all_violations:
        print(f"WMF validator: {len(all_violations)} violation(s) found\n")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("WMF validator: OK (0 violations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
