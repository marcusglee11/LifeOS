"""
Auto-dispatch eligibility predicate for COO orchestration.

Pure function — no side effects. Checks whether a task qualifies for
auto-dispatch without CEO approval based on the delegation envelope policy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.coo.closures import (
    ClosureValidationError,
    validate_council_request_packet,
)

# Task types that are eligible for auto-dispatch.
# This is a safeguard: future task types default to ineligible.
_ELIGIBLE_TASK_TYPES = frozenset({"build", "content", "hygiene"})


def is_auto_dispatchable(task: TaskEntry, envelope: dict[str, Any]) -> tuple[bool, str]:
    """Check if a task qualifies for auto-dispatch without CEO approval.

    Args:
        task: The TaskEntry to evaluate.
        envelope: The delegation envelope dict (from delegation_envelope.yaml).

    Returns:
        (eligible, reason) tuple.
        eligible=True only when ALL predicates pass.
    """
    # Predicate 1: requires_approval must be False
    if task.requires_approval:
        return (False, "requires_approval is true")

    # Predicate 2: risk must be low
    if task.risk != "low":
        return (False, f"risk is {task.risk}, not low")

    # Predicate 3: task must be pending (not already started or finished)
    if task.status != "pending":
        return (False, f"status is {task.status!r}, must be pending")

    # Predicate 4: scope_paths must not overlap with protected_paths in envelope
    protected_paths = envelope.get("protected_paths", [])
    for scope_path in task.scope_paths:
        for protected in protected_paths:
            # Overlap check: either is a prefix of the other (normalize trailing slashes)
            sp = scope_path.rstrip("/")
            pp = protected.rstrip("/")
            if sp.startswith(pp) or pp.startswith(sp):
                return (
                    False,
                    f"scope_path {scope_path!r} overlaps with protected path {protected!r}",
                )

    # Predicate 5: task_type must be in the eligible set
    if task.task_type not in _ELIGIBLE_TASK_TYPES:
        return (
            False,
            f"task_type {task.task_type!r} is not in eligible types {sorted(_ELIGIBLE_TASK_TYPES)}",
        )

    # Predicate 6: no other in_progress task shares any scope_path
    # (Concurrency guard via scope_path overlap proxy for dependencies)
    # This check requires the caller to pass all tasks; handled via backlog kwarg.
    # This predicate is checked externally (see check_scope_overlap_with_in_progress).
    # If the caller didn't verify it, we treat it as passed (conservative but caller's
    # responsibility — see check_scope_overlap_with_in_progress() below).

    return (True, "all predicates pass")


def check_scope_overlap_with_in_progress(
    task: TaskEntry, all_tasks: list[TaskEntry]
) -> tuple[bool, str]:
    """Check predicate 6: no in_progress task shares a scope_path with task.

    Args:
        task: The candidate task.
        all_tasks: All tasks in the backlog (used to find in_progress tasks).

    Returns:
        (eligible, reason) — eligible=True if no overlap found.
    """
    in_progress_tasks = [t for t in all_tasks if t.status == "in_progress" and t.id != task.id]
    for in_progress_task in in_progress_tasks:
        for candidate_path in task.scope_paths:
            for active_path in in_progress_task.scope_paths:
                cp = candidate_path.rstrip("/")
                ap = active_path.rstrip("/")
                if cp.startswith(ap) or ap.startswith(cp):
                    return (
                        False,
                        (
                            f"scope_path overlap with in_progress task {in_progress_task.id}: "
                            f"{candidate_path!r} overlaps {active_path!r}"
                        ),
                    )
    return (True, "no scope_path overlap with in_progress tasks")


def _council_cleared(task: TaskEntry, closures_dir: Path) -> tuple[bool, str]:
    """Check predicate 7: flagged tasks need a resolved latest council request."""
    if not task.decision_support_required:
        return (True, "decision support not required")

    if not closures_dir.exists():
        return (False, "decision_support_required is true and no closures directory exists")

    matching_requests: list[dict[str, Any]] = []
    for path in sorted(closures_dir.glob("CR-*.yaml")):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            return (False, f"invalid council request YAML in {path.name}: {exc}")
        if not isinstance(payload, dict):
            return (False, f"invalid council request payload in {path.name}")
        try:
            validate_council_request_packet(payload)
        except ClosureValidationError as exc:
            return (False, f"invalid council request {path.name}: {exc}")
        if task.id in payload.get("related_tasks", []):
            matching_requests.append(payload)

    if not matching_requests:
        return (False, f"decision_support_required is true and no matching council request exists")

    latest = max(matching_requests, key=lambda packet: str(packet.get("requested_at", "")))
    if not latest.get("resolved", False):
        return (
            False,
            f"latest council request {latest.get('request_id', 'unknown')} is unresolved",
        )
    if not str(latest.get("resolved_at", "")).strip():
        return (
            False,
            f"latest council request {latest.get('request_id', 'unknown')} lacks resolved_at",
        )
    return (True, f"council request {latest.get('request_id', 'unknown')} is resolved")


def is_fully_auto_dispatchable(
    task: TaskEntry,
    all_tasks: list[TaskEntry],
    envelope: dict[str, Any],
    repo_root: Path | None = None,
) -> tuple[bool, str]:
    """Combined eligibility check including scope_path concurrency guard.

    Runs all 6 predicates. Returns (eligible, reason).
    """
    eligible, reason = is_auto_dispatchable(task, envelope)
    if not eligible:
        return (eligible, reason)

    eligible, reason = check_scope_overlap_with_in_progress(task, all_tasks)
    if not eligible:
        return (eligible, reason)

    if repo_root is None:
        if task.decision_support_required:
            return (False, "decision_support_required is true and repo_root was not provided")
        return (True, "all predicates pass")

    return _council_cleared(task, repo_root / "artifacts" / "dispatch" / "closures")
