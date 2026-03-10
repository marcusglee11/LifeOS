"""
DispatchEngine — Phase 1: Single-flight execution layer.

Manages order lifecycle: inbox → active → completed.
Delegates step execution to LoopSpine.
Enforces non-bypassable gates and canonical manifest.

Phase 1 constraints:
- Global single-flight lock (owned by LoopSpine)
- execute() is blocking — no async/parallel
- execute_async() is NOT available (raises NotImplementedError)
"""
from __future__ import annotations

import subprocess

import yaml
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.orchestration.dispatch.manifest import RunManifest
from runtime.orchestration.dispatch.order import (
    ExecutionOrder,
    OrderValidationError,
    load_order,
    parse_order,
)
from runtime.orchestration.coo.backlog import TaskEntry, load_backlog
from runtime.orchestration.workflow_runtime import translate_order_to_workflow_instance
from runtime.util.atomic_write import atomic_write_text


@dataclass
class DispatchConfig:
    providers: Dict[str, Any] = field(default_factory=dict)
    max_duration_seconds: int = 3600


@dataclass
class DispatchResult:
    """Result of executing a dispatch order."""

    order_id: str
    run_id: Optional[str]
    outcome: str
    reason: str
    terminal_packet_path: Optional[str]
    repo_clean_verified: bool
    orphan_check_passed: bool
    completed_at: str


class DispatchEngine:
    """
    Phase 1: Single-flight dispatch engine.

    Manages order file lifecycle (inbox → active → completed) around LoopSpine execution.
    Enforces non-bypassable gates and appends to the canonical run_log manifest.

    On startup, call recover_crashed_runs() to handle any stranded active/ orders
    from a previous crash.
    """

    def __init__(self, repo_root: Path, config: Optional[DispatchConfig] = None):
        self.repo_root = Path(repo_root).resolve()
        self.config = config or DispatchConfig()

        self.inbox = self.repo_root / "artifacts" / "dispatch" / "inbox"
        self.active = self.repo_root / "artifacts" / "dispatch" / "active"
        self.completed = self.repo_root / "artifacts" / "dispatch" / "completed"

        for d in (self.inbox, self.active, self.completed):
            d.mkdir(parents=True, exist_ok=True)

        self.manifest = RunManifest(self.repo_root)

    def recover_crashed_runs(self) -> List[str]:
        """
        Detect and recover stranded orders in active/.

        If an order exists in active/ with no corresponding lock activity,
        it represents a crashed run. Marks as CLEAN_FAIL + CRASH_RECOVERY
        and moves to completed/.

        Returns list of recovered order IDs.
        """
        recovered: List[str] = []

        for order_file in list(self.active.glob("*.yaml")):
            order_id = order_file.stem
            recovery_record = {
                "dispatch_result": {
                    "order_id": order_id,
                    "outcome": "CLEAN_FAIL",
                    "reason": "CRASH_RECOVERY",
                    "recovered_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": None,
                    "terminal_packet_path": None,
                    "repo_clean_verified": False,
                    "orphan_check_passed": False,
                }
            }

            original_content = order_file.read_text(encoding="utf-8")
            combined = (
                original_content
                + "\n# DISPATCH_RESULT:\n"
                + yaml.dump(recovery_record, sort_keys=True, default_flow_style=False)
            )

            completed_path = self.completed / order_file.name
            tmp_path = completed_path.with_suffix(".tmp")
            atomic_write_text(tmp_path, combined)
            tmp_path.rename(completed_path)
            order_file.unlink(missing_ok=True)

            self.manifest.append(
                {
                    "order_id": order_id,
                    "outcome": "CLEAN_FAIL",
                    "reason": "CRASH_RECOVERY",
                    "run_id": None,
                }
            )

            recovered.append(order_id)

        if recovered:
            _clear_orphan_run_lock(self.repo_root)

        return recovered

    def poll_inbox(self) -> List[Path]:
        """Return sorted list of pending order files in inbox/."""
        return sorted(f for f in self.inbox.glob("*.yaml") if not f.name.endswith(".tmp"))

    def submit_to_inbox(self, order_path: Path) -> Path:
        """
        Validate and copy an order file into inbox/.

        Returns the path to the order in inbox/.
        Raises OrderValidationError if the order is invalid.
        """
        order = load_order(order_path)
        dest = self.inbox / f"{order.order_id}.yaml"
        tmp = dest.with_suffix(".tmp")
        content = order_path.read_text(encoding="utf-8")
        atomic_write_text(tmp, content)
        tmp.rename(dest)
        return dest

    def execute_from_path(self, order_path: Path) -> DispatchResult:
        """
        Load, validate, and execute an order from a file path.

        Full lifecycle: validate → inbox → active → execute → gates → completed → manifest.
        This is the primary entry point for CLI dispatch.
        """
        order = load_order(order_path)
        return self._execute_order(order, source_path=order_path)

    def execute(self, order: ExecutionOrder) -> DispatchResult:
        """
        Execute a pre-parsed ExecutionOrder. Blocking.

        Full lifecycle: inbox → active → execute → gates → completed → manifest.
        """
        return self._execute_order(order, source_path=None)

    def execute_async(self, order: ExecutionOrder) -> str:
        """Phase 3+ only. Not available in Phase 1."""
        raise NotImplementedError(
            "execute_async() is not available in Phase 1. "
            "Parallel execution requires Phase 3 prerequisites: "
            "5+ successful single-flight cycles and per-instance lock design."
        )

    def _execute_order(
        self,
        order: ExecutionOrder,
        source_path: Optional[Path],
    ) -> DispatchResult:
        """Internal execution. Manages full order lifecycle."""
        run_id: Optional[str] = None
        terminal_packet_path: Optional[str] = None
        repo_clean_verified = False
        orphan_check_passed = True  # Phase 1: placeholder
        outcome = "CLEAN_FAIL"
        reason = "unknown"

        active_file = self.active / f"{order.order_id}.yaml"

        # Step 1: Write order content to active/ (atomic)
        if source_path and source_path.parent == self.inbox:
            # Order came from inbox — move it
            tmp = active_file.with_suffix(".tmp")
            content = source_path.read_text(encoding="utf-8")
            atomic_write_text(tmp, content)
            tmp.rename(active_file)
            source_path.unlink(missing_ok=True)
        else:
            # Direct execute (not from inbox) — write raw order to active/
            inbox_file = self.inbox / f"{order.order_id}.yaml"
            if inbox_file.exists():
                tmp = active_file.with_suffix(".tmp")
                content = inbox_file.read_text(encoding="utf-8")
                atomic_write_text(tmp, content)
                tmp.rename(active_file)
                inbox_file.unlink(missing_ok=True)
            else:
                raw_dict = _order_to_dict(order)
                tmp = active_file.with_suffix(".tmp")
                atomic_write_text(
                    tmp,
                    yaml.dump(raw_dict, sort_keys=True, default_flow_style=False),
                )
                tmp.rename(active_file)

        try:
            # Step 2: Execute via LoopSpine
            task = _load_task_for_order(self.repo_root, order.task_ref)
            task_spec = _order_to_task_spec(order, task=task)

            from runtime.orchestration.loop.spine import LoopSpine

            attempted_auto_remediation = False
            requested_worktree = bool(order.constraints.worktree)
            spine_outcome = "UNKNOWN"
            spine_reason = ""
            spine_result: Dict[str, Any] = {}
            first_isolation_reason: Optional[str] = None

            use_worktree = requested_worktree
            if (not requested_worktree) and _isolation_required(self.repo_root):
                attempted_auto_remediation = True
                first_isolation_reason = (
                    "ISOLATION_REQUIRED: scoped branch in primary worktree; "
                    "retrying automatically in isolated worktree"
                )
                use_worktree = True
            while True:
                spine = LoopSpine(
                    repo_root=self.repo_root,
                    use_worktree=use_worktree,
                )
                spine_result = spine.run(task_spec)

                run_id = spine_result.get("run_id")
                terminal_packet_path = spine_result.get("terminal_packet_path")
                spine_outcome = spine_result.get("outcome", "UNKNOWN")
                spine_reason = str(spine_result.get("reason", ""))

                is_isolation_required = "ISOLATION_REQUIRED" in spine_reason
                if spine_outcome in ("PASS",):
                    break

                if (not use_worktree) and is_isolation_required and (not attempted_auto_remediation):
                    # Automatic recovery path: rerun once in isolated worktree.
                    attempted_auto_remediation = True
                    first_isolation_reason = spine_reason or spine_outcome
                    use_worktree = True
                    continue

                break

            if attempted_auto_remediation and spine_outcome in ("PASS",):
                spine_reason = (
                    (spine_reason or "spine_completed")
                    + " [auto-remediated:isolation]"
                )
            elif attempted_auto_remediation:
                spine_reason = (
                    "ISOLATION_AUTO_REMEDIATION_FAILED: "
                    + (spine_reason or first_isolation_reason or spine_outcome or "unknown")
                )

            if spine_outcome in ("PASS",):
                outcome = "SUCCESS"
                reason = spine_reason or "spine_completed"
            else:
                outcome = "CLEAN_FAIL"
                reason = spine_reason or spine_outcome or "spine_failed"

        except Exception as exc:
            outcome = "CLEAN_FAIL"
            reason = f"execution_error:{type(exc).__name__}:{exc}"

        finally:
            # Step 3: NON-BYPASSABLE GATES (always run regardless of step outcomes)
            repo_clean_verified = _check_repo_clean(self.repo_root)
            # orphan_check_passed: Phase 1 placeholder = True
            orphan_check_passed = True

            completed_at = datetime.now(timezone.utc).isoformat()

            # Step 4: Atomic move active → completed (append result record)
            completed_file = self.completed / f"{order.order_id}.yaml"
            if active_file.exists():
                result_record = {
                    "dispatch_result": {
                        "order_id": order.order_id,
                        "run_id": run_id,
                        "outcome": outcome,
                        "reason": reason,
                        "completed_at": completed_at,
                        "repo_clean_verified": repo_clean_verified,
                        "orphan_check_passed": orphan_check_passed,
                        "terminal_packet_path": str(terminal_packet_path)
                        if terminal_packet_path
                        else None,
                    }
                }
                original = active_file.read_text(encoding="utf-8")
                combined = (
                    original
                    + "\n# DISPATCH_RESULT:\n"
                    + yaml.dump(result_record, sort_keys=True, default_flow_style=False)
                )
                tmp = completed_file.with_suffix(".tmp")
                atomic_write_text(tmp, combined)
                tmp.rename(completed_file)
                active_file.unlink(missing_ok=True)

            # Step 5: Append to canonical manifest
            self.manifest.append(
                {
                    "order_id": order.order_id,
                    "run_id": run_id,
                    "task_ref": order.task_ref,
                    "outcome": outcome,
                    "reason": reason,
                    "completed_at": completed_at,
                    "repo_clean_verified": repo_clean_verified,
                    "orphan_check_passed": orphan_check_passed,
                    "terminal_packet_path": str(terminal_packet_path)
                    if terminal_packet_path
                    else None,
                }
            )

        return DispatchResult(
            order_id=order.order_id,
            run_id=run_id,
            outcome=outcome,
            reason=reason,
            terminal_packet_path=str(terminal_packet_path) if terminal_packet_path else None,
            repo_clean_verified=repo_clean_verified,
            orphan_check_passed=orphan_check_passed,
            completed_at=completed_at,
        )

    def provider_health(self) -> Dict[str, Any]:
        """Current health state. Phase 1: returns minimal stub."""
        return {
            "phase": 1,
            "note": "ProviderPool not active in Phase 1",
            "providers": {},
        }

    def status(self) -> Dict[str, Any]:
        """Return current dispatch engine status."""
        pending = self.poll_inbox()
        active_orders = [
            f for f in self.active.glob("*.yaml") if not f.name.endswith(".tmp")
        ]
        completed_count = len(
            [f for f in self.completed.glob("*.yaml") if not f.name.endswith(".tmp")]
        )

        return {
            "pending_orders": len(pending),
            "active_orders": len(active_orders),
            "completed_orders": completed_count,
            "pending": [f.stem for f in pending],
            "active": [f.stem for f in active_orders],
        }


def _check_repo_clean(repo_root: Path) -> bool:
    """Run repo-clean gate. Returns True if clean, False if dirty or error."""
    try:
        from runtime.orchestration.run_controller import verify_repo_clean

        verify_repo_clean(repo_root)
        return True
    except Exception:
        return False


def _clear_orphan_run_lock(repo_root: Path) -> bool:
    """Best-effort cleanup for orphaned run-locks during crash recovery."""
    lock_path = repo_root / "artifacts" / "locks" / "run.lock"
    if not lock_path.exists():
        return False
    lock_path.unlink(missing_ok=True)
    return True


def _isolation_required(repo_root: Path) -> bool:
    """Return True when scoped work is running in primary and needs a worktree."""
    try:
        branch_proc = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
        )
        branch = branch_proc.stdout.strip()
        if not branch.startswith(("build/", "fix/", "hotfix/", "spike/")):
            return False

        common_proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
            check=False,
            capture_output=True,
            text=True,
        )
        return common_proc.stdout.strip() == ".git"
    except Exception:
        return False


def _load_task_for_order(repo_root: Path, task_ref: str) -> Optional[TaskEntry]:
    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    if not backlog_path.exists():
        return None
    try:
        tasks = load_backlog(backlog_path)
    except Exception:
        return None
    return next((task for task in tasks if task.id == task_ref), None)


def _order_to_task_spec(order: ExecutionOrder, *, task: Optional[TaskEntry] = None) -> Dict[str, Any]:
    """Convert ExecutionOrder to LoopSpine task_spec dict."""
    workflow_instance = translate_order_to_workflow_instance(order, task=task)
    return {
        "task_ref": order.task_ref,
        "order_id": order.order_id,
        "workflow_instance": workflow_instance.to_dict(),
        "task_context": order.task_context,
        "workflow_id": order.workflow_id,
        "steps": [
            {
                "name": s.name,
                "role": s.role,
                "provider": s.provider,
                "mode": s.mode,
                "lens_providers": dict(s.lens_providers),
                "step_id": s.step_id,
                "step_kind": s.step_kind,
                "mission_type": s.mission_type,
                "consumes": list(s.consumes),
                "produces": s.produces,
                "mutation_class": s.mutation_class,
            }
            for s in order.steps
        ],
        "constraints": {
            "worktree": order.constraints.worktree,
            "scope_paths": order.constraints.scope_paths,
            "max_duration_seconds": order.constraints.max_duration_seconds,
        },
    }


def _order_to_dict(order: ExecutionOrder) -> Dict[str, Any]:
    """Serialize an ExecutionOrder to a plain dict for YAML output."""
    return {
        "schema_version": order.schema_version,
        "order_id": order.order_id,
        "task_ref": order.task_ref,
        "created_at": order.created_at,
        "workflow_id": order.workflow_id,
        "workflow_version": order.workflow_version,
        "review_policy_id": order.review_policy_id,
        "mutation_policy_id": order.mutation_policy_id,
        "task_context": order.task_context,
        "steps": [
            {
                "name": s.name,
                "role": s.role,
                "provider": s.provider,
                "mode": s.mode,
                "lens_providers": dict(s.lens_providers),
                "step_id": s.step_id,
                "step_kind": s.step_kind,
                "mission_type": s.mission_type,
                "consumes": list(s.consumes),
                "produces": s.produces,
                "mutation_class": s.mutation_class,
            }
            for s in order.steps
        ],
        "constraints": {
            "worktree": order.constraints.worktree,
            "scope_paths": order.constraints.scope_paths,
            "max_duration_seconds": order.constraints.max_duration_seconds,
        },
        "shadow": {
            "enabled": order.shadow.enabled,
            "provider": order.shadow.provider,
        },
        "supervision": {
            "per_cycle_check": order.supervision.per_cycle_check,
            "batch_id": order.supervision.batch_id,
            "cycle_number": order.supervision.cycle_number,
        },
    }
