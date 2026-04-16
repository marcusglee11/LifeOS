from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Sequence


CLOSURE_POLICY_VERSION = "v1"
BASE_BRANCH = "main"
STRUCTURED_DOC_PYTEST_COMMANDS = (
    "pytest -q runtime/tests/test_doc_hygiene.py",
    "pytest -q runtime/tests/test_backlog_parser.py",
)

_GENERAL_DOC_EXCLUDES = (
    "docs/00_foundations/",
    "docs/01_governance/",
    "docs/02_protocols/",
    "docs/03_runtime/",
    "docs/11_admin/",
)
_STRUCTURED_DOC_PREFIXES = (
    "docs/02_protocols/",
    "docs/03_runtime/",
)
_FULL_PREFIXES = (
    "docs/00_foundations/",
    "docs/01_governance/",
    "docs/11_admin/",
    "config/",
    "runtime/",
    "scripts/",
    "tests/",
    "doc_steward/",
    "project_builder/",
    "recursive_kernel/",
    "context/",
    ".github/",
)
_ALLOWED_ARTIFACT_PREFIX = "artifacts/"
_KNOWN_TIER_ROOTS = ("artifacts/", "docs/")
_CHECK_ORDER = (
    "targeted_pytest",
    "quality_gate",
    "doc_stewardship",
    "markdownlint",
    "yamllint",
    "review_checkpoint",
    "runtime_status_regeneration",
    "state_backlog_updates",
    "structured_backlog_updates",
)


def _git_stdout(repo_root: Path, args: Sequence[str]) -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0, proc.stdout.strip()


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = _normalize_path(value)
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _classify_path(path: str) -> str:
    normalized = _normalize_path(path)
    if not normalized:
        return "full"
    if normalized.startswith(_ALLOWED_ARTIFACT_PREFIX):
        return "artifact_only"
    if normalized.startswith(_STRUCTURED_DOC_PREFIXES):
        return "structured_docs"
    if normalized.startswith("docs/"):
        if normalized.startswith(_GENERAL_DOC_EXCLUDES):
            return "full"
        return "general_docs"
    if normalized.startswith(_FULL_PREFIXES):
        return "full"
    if normalized.startswith(_KNOWN_TIER_ROOTS):
        return "full"
    return "full"


def classify_paths(paths: Sequence[str]) -> dict:
    normalized = _unique_ordered(paths)
    if not normalized:
        return {
            "closure_tier": "no_changes",
            "classification_reason": "Valid diff with zero changed paths.",
            "changed_paths": [],
        }

    categories = {_classify_path(path) for path in normalized}
    if "full" in categories:
        return {
            "closure_tier": "full",
            "classification_reason": "Full-tier or unknown path detected in change-set.",
            "changed_paths": normalized,
        }
    if categories == {"artifact_only"}:
        return {
            "closure_tier": "artifact_only",
            "classification_reason": "All changed paths are under artifacts/.",
            "changed_paths": normalized,
        }
    if categories == {"general_docs"}:
        return {
            "closure_tier": "general_docs",
            "classification_reason": "All changed paths are general docs under docs/.",
            "changed_paths": normalized,
        }
    if categories == {"structured_docs"}:
        return {
            "closure_tier": "structured_docs",
            "classification_reason": "All changed paths are structured docs under docs/02_protocols or docs/03_runtime.",
            "changed_paths": normalized,
        }
    return {
        "closure_tier": "full",
        "classification_reason": "Mixed change-set crosses closure tiers; strictest tier applied.",
        "changed_paths": normalized,
    }


def discover_normalized_change_set(repo_root: Path, head_ref: str = "HEAD") -> dict:
    ok, merge_base = _git_stdout(repo_root, ["merge-base", BASE_BRANCH, head_ref])
    if not ok or not merge_base:
        return {
            "ok": False,
            "base_branch": BASE_BRANCH,
            "head_ref": head_ref,
            "merge_base": merge_base if ok else "",
            "reason": "Unable to resolve merge-base for closure diff.",
            "entries": [],
            "changed_paths": [],
        }

    ok, stdout = _git_stdout(repo_root, ["diff", "--name-status", "-M", f"{merge_base}..{head_ref}"])
    if not ok:
        return {
            "ok": False,
            "base_branch": BASE_BRANCH,
            "head_ref": head_ref,
            "merge_base": merge_base,
            "reason": "Unable to collect closure diff.",
            "entries": [],
            "changed_paths": [],
        }

    entries: list[dict[str, object]] = []
    changed_paths: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        if not status:
            return {
                "ok": False,
                "base_branch": BASE_BRANCH,
                "head_ref": head_ref,
                "merge_base": merge_base,
                "reason": f"Unsupported diff status line: {raw_line}",
                "entries": [],
                "changed_paths": [],
            }
        kind = status[0]
        if kind in {"A", "M", "D"} and len(parts) == 2:
            path = _normalize_path(parts[1])
            entries.append(
                {
                    "status": kind,
                    "old_path": path if kind == "D" else None,
                    "new_path": path if kind != "D" else None,
                    "paths": [path],
                }
            )
            changed_paths.append(path)
            continue
        if kind == "R" and len(parts) == 3:
            old_path = _normalize_path(parts[1])
            new_path = _normalize_path(parts[2])
            entries.append(
                {
                    "status": "R",
                    "old_path": old_path,
                    "new_path": new_path,
                    "paths": [old_path, new_path],
                }
            )
            changed_paths.extend([old_path, new_path])
            continue
        return {
            "ok": False,
            "base_branch": BASE_BRANCH,
            "head_ref": head_ref,
            "merge_base": merge_base,
            "reason": f"Unsupported diff status line: {raw_line}",
            "entries": [],
            "changed_paths": [],
        }

    return {
        "ok": True,
        "base_branch": BASE_BRANCH,
        "head_ref": head_ref,
        "merge_base": merge_base,
        "reason": "",
        "entries": entries,
        "changed_paths": _unique_ordered(changed_paths),
    }


def resolve_closure_tier(repo_root: Path, head_ref: str = "HEAD") -> dict:
    change_set = discover_normalized_change_set(repo_root, head_ref=head_ref)
    if not change_set["ok"]:
        return {
            "closure_policy_version": CLOSURE_POLICY_VERSION,
            "base_branch": BASE_BRANCH,
            "head_ref": head_ref,
            "merge_base": change_set.get("merge_base", ""),
            "diff_ok": False,
            "outcome": "full_fallback",
            "closure_tier": "full",
            "classification_reason": str(change_set.get("reason", "")),
            "changed_entries": [],
            "changed_paths": [],
        }

    classified = classify_paths(change_set["changed_paths"])
    outcome = "classified"
    if classified["closure_tier"] == "no_changes":
        outcome = "no_changes"
    return {
        "closure_policy_version": CLOSURE_POLICY_VERSION,
        "base_branch": BASE_BRANCH,
        "head_ref": head_ref,
        "merge_base": change_set["merge_base"],
        "diff_ok": True,
        "outcome": outcome,
        "closure_tier": classified["closure_tier"],
        "classification_reason": classified["classification_reason"],
        "changed_entries": change_set["entries"],
        "changed_paths": classified["changed_paths"],
    }


def get_tier_execution_policy(closure_tier: str) -> dict:
    policies = {
        "no_changes": {
            "selected_checks": [],
            "skipped_checks": list(_CHECK_ORDER),
            "run_doc_stewardship": False,
            "run_general_quality_gate": False,
            "quality_tools": [],
            "run_targeted_pytest": False,
            "targeted_pytest_commands": [],
            "run_review_checkpoint": False,
            "post_merge_updates_suppressed": True,
            "run_runtime_status_regeneration": False,
            "run_state_backlog_updates": False,
            "run_structured_backlog_updates": False,
        },
        "artifact_only": {
            "selected_checks": [],
            "skipped_checks": [
                "targeted_pytest",
                "quality_gate",
                "doc_stewardship",
                "markdownlint",
                "yamllint",
                "review_checkpoint",
                "runtime_status_regeneration",
                "state_backlog_updates",
                "structured_backlog_updates",
            ],
            "run_doc_stewardship": False,
            "run_general_quality_gate": False,
            "quality_tools": [],
            "run_targeted_pytest": False,
            "targeted_pytest_commands": [],
            "run_review_checkpoint": False,
            "post_merge_updates_suppressed": True,
            "run_runtime_status_regeneration": False,
            "run_state_backlog_updates": False,
            "run_structured_backlog_updates": False,
        },
        "general_docs": {
            "selected_checks": ["doc_stewardship", "markdownlint"],
            "skipped_checks": [
                "targeted_pytest",
                "quality_gate",
                "yamllint",
                "review_checkpoint",
                "runtime_status_regeneration",
                "state_backlog_updates",
                "structured_backlog_updates",
            ],
            "run_doc_stewardship": True,
            "run_general_quality_gate": False,
            "quality_tools": ["markdownlint"],
            "run_targeted_pytest": False,
            "targeted_pytest_commands": [],
            "run_review_checkpoint": False,
            "post_merge_updates_suppressed": True,
            "run_runtime_status_regeneration": False,
            "run_state_backlog_updates": False,
            "run_structured_backlog_updates": False,
        },
        "structured_docs": {
            "selected_checks": ["doc_stewardship", "markdownlint", "yamllint", "targeted_pytest", "review_checkpoint"],
            "skipped_checks": [
                "quality_gate",
                "runtime_status_regeneration",
                "state_backlog_updates",
                "structured_backlog_updates",
            ],
            "run_doc_stewardship": True,
            "run_general_quality_gate": False,
            "quality_tools": ["markdownlint", "yamllint"],
            "run_targeted_pytest": True,
            "targeted_pytest_commands": list(STRUCTURED_DOC_PYTEST_COMMANDS),
            "run_review_checkpoint": True,
            "post_merge_updates_suppressed": True,
            "run_runtime_status_regeneration": False,
            "run_state_backlog_updates": False,
            "run_structured_backlog_updates": False,
        },
        "full": {
            "selected_checks": ["targeted_pytest", "quality_gate", "doc_stewardship", "review_checkpoint"],
            "skipped_checks": [],
            "run_doc_stewardship": True,
            "run_general_quality_gate": True,
            "quality_tools": [],
            "run_targeted_pytest": True,
            "targeted_pytest_commands": [],
            "run_review_checkpoint": True,
            "post_merge_updates_suppressed": False,
            "run_runtime_status_regeneration": True,
            "run_state_backlog_updates": True,
            "run_structured_backlog_updates": True,
        },
    }
    return dict(policies.get(closure_tier, policies["full"]))
