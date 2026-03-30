"""
Claim verifier for COO output.

Pure-function architecture — no side effects, fully testable without mocking
the COO. Checks COO output text for unsupported execution claims by comparing
against durable evidence sources.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class EvidenceSnapshot:
    """Frozen view of all durable evidence at a point in time."""

    tasks: list  # list[TaskEntry] — typed as list to avoid circular import issues
    inbox_orders: list[str]  # order_ids in inbox/
    active_orders: list[str]  # order_ids in active/
    completed_orders: dict[str, str]  # order_id -> outcome
    manifest_entries: list[dict]  # from run_log.jsonl
    escalation_ids: list[str]  # pending escalation IDs


@dataclass
class ClaimViolation:
    claim_text: str  # the substring making the unsupported claim
    claim_type: str  # "execution_state", "branch", "push", "ci", "commit", "merge", "test"
    required_evidence: str  # what evidence would be needed
    found_evidence: str  # what was actually found (or "none")


# Patterns for execution state claims — task_id + verb combos
_STARTED_RE = re.compile(
    r"\b(started|began|beginning|in progress)\b.{0,60}?\b(T-\w+)\b",
    re.IGNORECASE,
)
_COMPLETED_RE = re.compile(
    r"\b(T-\w+)\b.{0,60}?\b(completed|finished|succeeded)\b"
    r"|\b(completed|finished|succeeded)\b.{0,60}?\b(T-\w+)\b",
    re.IGNORECASE,
)
# Also match "T-XXX has been dispatched/completed"
_TASK_PAST_RE = re.compile(
    r"\b(T-\w+)\b.{0,20}?\bhas been\b.{0,40}?\b(dispatched|completed|started|run|executed)\b",
    re.IGNORECASE,
)

# Push / merge claims
_PUSH_RE = re.compile(r"\b(pushed|created PR|merged)\b", re.IGNORECASE)

# CI claims
_CI_RE = re.compile(r"\b(CI passed|tests passed|build passed|pipeline passed)\b", re.IGNORECASE)

# Commit SHA (40-char hex string)
_SHA_RE = re.compile(r"\b([0-9a-f]{40})\b", re.IGNORECASE)


def collect_evidence(repo_root: Path) -> EvidenceSnapshot:
    """Build a frozen evidence snapshot from durable sources."""
    from runtime.orchestration.coo.backlog import load_backlog

    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    tasks = []
    if backlog_path.exists():
        try:
            tasks = load_backlog(backlog_path)
        except Exception:
            tasks = []

    dispatch_base = repo_root / "artifacts" / "dispatch"
    inbox_dir = dispatch_base / "inbox"
    active_dir = dispatch_base / "active"
    completed_dir = dispatch_base / "completed"

    inbox_orders = (
        [f.stem for f in inbox_dir.glob("*.yaml") if not f.name.endswith(".tmp")]
        if inbox_dir.exists()
        else []
    )

    active_orders = (
        [f.stem for f in active_dir.glob("*.yaml") if not f.name.endswith(".tmp")]
        if active_dir.exists()
        else []
    )

    completed_orders: dict[str, str] = {}
    if completed_dir.exists():
        for f in completed_dir.glob("*.yaml"):
            if f.name.endswith(".tmp"):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                raw = yaml.safe_load(content)
                if isinstance(raw, dict):
                    dr = raw.get("dispatch_result", {})
                    if isinstance(dr, dict) and dr.get("order_id"):
                        completed_orders[str(dr["order_id"])] = str(dr.get("outcome", "UNKNOWN"))
            except Exception:
                pass

    manifest_entries: list[dict] = []
    manifest_path = repo_root / "artifacts" / "dispatch" / "run_log.jsonl"
    if manifest_path.exists():
        import json

        try:
            for line in manifest_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        manifest_entries.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass

    escalation_ids: list[str] = []
    try:
        from runtime.orchestration.ceo_queue import CEOQueue

        queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
        entries = queue.get_pending()
        escalation_ids = [str(e.id) for e in entries]
    except Exception:
        pass

    return EvidenceSnapshot(
        tasks=tasks,
        inbox_orders=inbox_orders,
        active_orders=active_orders,
        completed_orders=completed_orders,
        manifest_entries=manifest_entries,
        escalation_ids=escalation_ids,
    )


def _find_order_for_task(task_id: str, evidence: EvidenceSnapshot) -> Optional[str]:
    """Return order_id if any order in active or completed maps to this task_id."""
    # Search completed orders: order_id often encodes task_id (ORD-T-XXX-...)
    for oid in evidence.active_orders:
        if task_id.replace("-", "") in oid.replace("-", "").upper() or task_id in oid:
            return oid
    for oid in evidence.completed_orders:
        if task_id.replace("-", "") in oid.replace("-", "").upper() or task_id in oid:
            return oid
    # Also check manifest entries
    for entry in evidence.manifest_entries:
        if entry.get("task_ref") == task_id:
            return str(entry.get("order_id", ""))
    return None


def _sha_exists_in_git(sha: str, repo_root: Optional[Path] = None) -> bool:
    """Return True if SHA exists in the git history."""
    try:
        cmd = ["git"]
        if repo_root:
            cmd += ["-C", str(repo_root)]
        cmd += ["cat-file", "-e", sha]
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def verify_claims(
    coo_output: str, evidence: EvidenceSnapshot, repo_root: Optional[Path] = None
) -> list[ClaimViolation]:
    """Check COO output text for unsupported execution claims.

    Returns a list of ClaimViolation for each unsupported claim found.
    Empty list means all claims are supported (or no claims were made).
    """
    violations: list[ClaimViolation] = []

    # Check "started T-XXX" patterns
    for match in _STARTED_RE.finditer(coo_output):
        task_id = match.group(2)
        # Check if there is an active order for this task
        if not any(task_id in oid for oid in evidence.active_orders):
            order_ref = _find_order_for_task(task_id, evidence)
            violations.append(
                ClaimViolation(
                    claim_text=match.group(0),
                    claim_type="execution_state",
                    required_evidence=f"order in active/ for task {task_id}",
                    found_evidence=f"active_order:{order_ref}" if order_ref else "none",
                )
            )

    # Check "T-XXX completed/finished/done" patterns
    for match in _COMPLETED_RE.finditer(coo_output):
        # Extract task_id from either group position
        task_id = (
            match.group(1) if match.group(1) and match.group(1).startswith("T-") else match.group(4)
        )
        if task_id is None:
            continue
        # Check if there's a SUCCESS completed order for this task
        has_success = False
        for oid, outcome in evidence.completed_orders.items():
            if task_id in oid and outcome == "SUCCESS":
                has_success = True
                break
        # Also check manifest
        if not has_success:
            for entry in evidence.manifest_entries:
                if entry.get("task_ref") == task_id and entry.get("outcome") == "SUCCESS":
                    has_success = True
                    break
        if not has_success:
            violations.append(
                ClaimViolation(
                    claim_text=match.group(0),
                    claim_type="execution_state",
                    required_evidence=f"order in completed/ with SUCCESS for task {task_id}",
                    found_evidence="none",
                )
            )

    # Check "T-XXX has been dispatched/completed/etc"
    for match in _TASK_PAST_RE.finditer(coo_output):
        task_id = match.group(1)
        verb = match.group(2).lower()
        if verb in ("dispatched", "started", "run", "executed"):
            if not any(task_id in oid for oid in evidence.active_orders):
                violations.append(
                    ClaimViolation(
                        claim_text=match.group(0),
                        claim_type="execution_state",
                        required_evidence=f"order in active/ for task {task_id}",
                        found_evidence="none",
                    )
                )
        elif verb == "completed":
            has_success = any(
                task_id in oid and outcome == "SUCCESS"
                for oid, outcome in evidence.completed_orders.items()
            )
            if not has_success:
                violations.append(
                    ClaimViolation(
                        claim_text=match.group(0),
                        claim_type="execution_state",
                        required_evidence=f"order in completed/ with SUCCESS for task {task_id}",
                        found_evidence="none",
                    )
                )

    # Check push/merge claims
    push_match = _PUSH_RE.search(coo_output)
    if push_match:
        # Require matching manifest entry or completed order
        has_evidence = len(evidence.completed_orders) > 0 or len(evidence.manifest_entries) > 0
        if not has_evidence:
            violations.append(
                ClaimViolation(
                    claim_text=push_match.group(0),
                    claim_type="push",
                    required_evidence="matching entry in manifest or completed order",
                    found_evidence="none",
                )
            )

    # Check CI claims
    ci_match = _CI_RE.search(coo_output)
    if ci_match:
        has_evidence = any(
            entry.get("repo_clean_verified") is True for entry in evidence.manifest_entries
        )
        if not has_evidence:
            # Also check completed orders for repo_clean_verified
            violations.append(
                ClaimViolation(
                    claim_text=ci_match.group(0),
                    claim_type="ci",
                    required_evidence="repo_clean_verified: true in completed order",
                    found_evidence="none",
                )
            )

    # Check commit SHA claims
    for sha_match in _SHA_RE.finditer(coo_output):
        sha = sha_match.group(1)
        if repo_root and not _sha_exists_in_git(sha, repo_root):
            violations.append(
                ClaimViolation(
                    claim_text=sha,
                    claim_type="commit",
                    required_evidence=f"SHA {sha} exists in git history",
                    found_evidence="unverifiable" if repo_root is None else "not in git",
                )
            )
        elif repo_root is None:
            violations.append(
                ClaimViolation(
                    claim_text=sha,
                    claim_type="commit",
                    required_evidence=f"SHA {sha} exists in git history",
                    found_evidence="unverifiable",
                )
            )

    # Deduplicate violations by claim_text — overlapping patterns can match the same span
    seen_texts: set[str] = set()
    deduped: list[ClaimViolation] = []
    for v in violations:
        if v.claim_text not in seen_texts:
            seen_texts.add(v.claim_text)
            deduped.append(v)

    return deduped


def verify_progress_obligation(coo_output: str, evidence: EvidenceSnapshot) -> Optional[str]:
    """If COO declines to proceed, verify it provides a concrete blocker.

    Returns None if obligation met, or error string if violated.
    """
    # Check for nothing_to_propose or decline patterns
    decline_patterns = [
        r"nothing_to_propose",
        r"cannot proceed",
        r"recommend waiting",
        r"suggest waiting",
        r"nothing actionable",
        r"no tasks to",
    ]
    has_decline = any(re.search(p, coo_output, re.IGNORECASE) for p in decline_patterns)
    if not has_decline:
        return None

    # Valid blocker indicators
    concrete_blocker_patterns = [
        # Policy rule reference
        r"\b(policy|rule|constraint|section|article|L[0-9])\b.{0,80}",
        # Missing artifact
        r"(missing|not found|absent|unavailable).{0,40}(file|artifact|path|\.yaml|\.md|\.json)",
        # Blocked task ID
        r"\b(T-\w+)\b.{0,20}(blocked|failing|failed)",
        # Protected path
        r"protected.{0,30}path",
        r"docs/0[01]_",
    ]
    has_concrete_blocker = any(
        re.search(p, coo_output, re.IGNORECASE) for p in concrete_blocker_patterns
    )

    if not has_concrete_blocker:
        return (
            "PROGRESS_OBLIGATION_VIOLATION: COO declined to proceed without citing "
            "a specific blocker (policy rule, missing evidence, blocked dependency, "
            "or protected path). Generic caution is not a valid reason."
        )

    return None
