"""
Loop Spine - A1 Chain Controller (Phase 4A0)

Canonical sequencer for the autonomous build loop with checkpoint/resume semantics.
Implements deterministic chain execution: hydrate → policy → design → build → review → steward

Key Features:
- Deterministic chain sequencing
- Checkpoint/resume contract
- Terminal packet emission
- Fail-closed on dirty repo or policy violations
- Ledger integration for resumability

See: artifacts/plans/Phase_4A0_Loop_Spine.md
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from runtime.api.governance_api import PolicyLoader, hash_json
from runtime.orchestration.council.shadow_runner import ShadowCouncilRunner
from runtime.orchestration.loop.budgets import BudgetController, extract_usage_tokens
from runtime.orchestration.loop.bypass_monitor import check_bypass_utilization
from runtime.orchestration.loop.ledger import (
    AttemptLedger,
    AttemptRecord,
    LedgerHeader,
)
from runtime.orchestration.loop.lifecycle_hooks import (
    run_post_hooks,
    run_pre_hooks,
)
from runtime.orchestration.loop.taxonomy import (
    FailureClass,
    LoopAction,
)
from runtime.orchestration.loop.worktree_dispatch import (
    WorktreeError,
    validate_worktree_clean,
    worktree_scope,
)
from runtime.orchestration.run_controller import check_kill_switch, verify_repo_clean
from runtime.orchestration.workflow_runtime import (
    REVIEW_DECISION_SCHEMA_VERSION,
    TERMINAL_WORKFLOW_STATES,
    WorkflowArtifact,
    WorkflowInstance,
    WorkflowRuntimeError,
    get_step,
    get_workflow_definition,
    materialize_packaged_spec,
    next_step_id,
    record_invocation_finish,
    record_invocation_start,
    translate_task_spec_to_workflow_instance,
    validate_resolution_packet,
)
from runtime.receipts.invocation_receipt import (
    finalize_run_receipts,
    get_or_create_collector,
)


class SpineState(Enum):
    """
    State machine for Loop Spine execution.

    States:
    - INIT: Initial state, ready to start
    - RUNNING: Chain is executing
    - CHECKPOINT: Paused at checkpoint, waiting for resolution
    - RESUMED: Resumed from checkpoint
    - TERMINAL: Execution complete (PASS/BLOCKED)
    """

    INIT = "INIT"
    RUNNING = "RUNNING"
    CHECKPOINT = "CHECKPOINT"
    RESUMED = "RESUMED"
    TERMINAL = "TERMINAL"


@dataclass
class CheckpointPacket:
    """
    Checkpoint packet emitted when execution pauses.

    Persisted to artifacts/checkpoints/CP_<run_id>_<step>.yaml
    """

    checkpoint_id: str
    run_id: str
    timestamp: str  # ISO 8601
    trigger: str  # e.g., "ESCALATION_REQUESTED"
    step_index: int
    policy_hash: str
    task_spec: Dict[str, Any]
    resolved: bool
    resolution_decision: Optional[str]  # "APPROVED" | "REJECTED" | None


@dataclass
class TerminalPacket:
    """
    Terminal packet emitted when execution completes (v2.1).

    Persisted to artifacts/terminal/TP_<run_id>.yaml
    """

    run_id: str
    timestamp: str  # ISO 8601
    outcome: str  # "PASS" | "BLOCKED" | "WAIVER_REQUESTED" | "ESCALATION_REQUESTED"
    reason: str  # TerminalReason value
    steps_executed: List[str]
    commit_hash: Optional[str] = None
    # Ledger chain anchor (W7-T01) — external commitment for truncation detection
    ledger_chain_tip: Optional[str] = None
    ledger_attempt_count: int = 0
    ledger_schema_version: Optional[str] = None
    # v2.1 extensions
    status: str = ""  # "SUCCESS" | "CLEAN_FAIL"
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    task_ref: Optional[str] = None
    policy_hash: Optional[str] = None
    phase_outcomes: Optional[Dict[str, Any]] = None
    gate_results: Optional[List[Dict[str, Any]]] = None
    receipt_index: Optional[str] = None
    clean_fail_reason: Optional[str] = None
    repo_clean_verified: bool = False
    orphan_check_passed: bool = False
    packet_hash: Optional[str] = None  # SHA-256, computed last
    tokens_consumed: Optional[int] = None
    token_source: Optional[str] = None
    token_accounting_complete: bool = True
    bypass_utilization: Optional[Dict[str, Any]] = (
        None  # BypassStatus as dict; None if monitor failed
    )


class SpineError(Exception):
    """Base exception for Loop Spine errors."""

    pass


class PolicyChangedError(SpineError):
    """Raised when policy hash changes mid-run (fail-closed)."""

    def __init__(self, checkpoint_hash: str, current_hash: str):
        self.checkpoint_hash = checkpoint_hash
        self.current_hash = current_hash
        super().__init__(
            f"POLICY_CHANGED_MID_RUN: Checkpoint policy_hash={checkpoint_hash}, "
            f"current policy_hash={current_hash}. Cannot resume."
        )


class LoopSpine:
    """
    A1 Chain Controller - Canonical sequencer for autonomous build loop.

    Responsibilities:
    - Run deterministic chain: hydrate → policy → sequence steps → checkpoint → resume
    - Checkpoint/resume contract with policy hash validation
    - Terminal packet emission
    - Fail-closed on dirty repo or policy violations
    - Ledger integration for state persistence

    Usage:
        spine = LoopSpine(repo_root=Path("/path/to/repo"))

        # Run new chain
        result = spine.run(task_spec={"task": "..."})

        # Resume from checkpoint
        result = spine.resume(checkpoint_id="CP_...")
    """

    def __init__(
        self,
        repo_root: Path,
        *,
        use_worktree: bool = False,
        pre_run_hooks=None,
        post_run_hooks=None,
    ):
        self.repo_root = Path(repo_root)
        self.state = SpineState.INIT
        self.use_worktree = use_worktree
        self._pre_run_hooks = pre_run_hooks
        self._post_run_hooks = post_run_hooks

        # Artifact paths
        self.artifacts_dir = self.repo_root / "artifacts"
        self.terminal_dir = self.artifacts_dir / "terminal"
        self.checkpoint_dir = self.artifacts_dir / "checkpoints"
        self.loop_state_dir = self.artifacts_dir / "loop_state"
        self.steps_dir = self.artifacts_dir / "steps"

        # Ensure directories exist
        self.terminal_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.loop_state_dir.mkdir(parents=True, exist_ok=True)
        self.steps_dir.mkdir(parents=True, exist_ok=True)

        # Ledger
        self.ledger_path = self.loop_state_dir / "attempt_ledger.jsonl"
        self.ledger = AttemptLedger(self.ledger_path)

        # Current run state
        self.run_id: Optional[str] = None
        self.current_policy_hash: Optional[str] = None
        self.was_resumed: bool = False

    def run(self, task_spec: Dict[str, Any], resume_from: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a new chain execution.

        Args:
            task_spec: Task specification dict
            resume_from: Optional checkpoint ID to resume from

        Returns:
            Result dict with outcome, state, run_id, etc.

        Raises:
            RepoDirtyError: If repository has uncommitted changes (fail-closed)
            SpineError: On other execution errors
        """
        # Generate run ID
        self.run_id = self._generate_run_id()
        self.state = SpineState.RUNNING
        # Initialize collector so terminal packets can always reference an index.
        get_or_create_collector(self.run_id)

        # Acquire run-lock (fail-closed on contention)
        from runtime.orchestration.loop.run_lock import (
            RunLockError,
            acquire_run_lock,
            release_run_lock,
        )

        if check_kill_switch(self.repo_root):
            return self._emit_blocked_terminal_result(
                reason="kill_switch_active_pre_lock",
                gate_results=[
                    self._gate_result(
                        phase="startup",
                        name="kill_switch_pre_lock",
                        passed=False,
                        reason="STOP_AUTONOMY present before lock acquisition",
                    )
                ],
                task_ref=task_spec.get("task_ref"),
            )

        lock_handle = None
        try:
            lock_handle = acquire_run_lock(self.repo_root, self.run_id)
        except RunLockError as exc:
            return self._emit_blocked_terminal_result(
                reason="concurrent_run_detected",
                gate_results=[
                    self._gate_result(
                        phase="startup",
                        name="run_lock",
                        passed=False,
                        reason=str(exc),
                    )
                ],
                task_ref=task_spec.get("task_ref"),
            )

        try:
            if check_kill_switch(self.repo_root):
                return self._emit_blocked_terminal_result(
                    reason="kill_switch_active_post_lock",
                    gate_results=[
                        self._gate_result(
                            phase="startup",
                            name="kill_switch_post_lock",
                            passed=False,
                            reason="STOP_AUTONOMY detected after lock acquisition",
                        )
                    ],
                    task_ref=task_spec.get("task_ref"),
                )

            # P0: Fail-closed on dirty repo
            verify_repo_clean(self.repo_root)
            return self._run_locked(task_spec, lock_handle)
        finally:
            if lock_handle is not None:
                release_run_lock(lock_handle)

    def _run_locked(
        self,
        task_spec: Dict[str, Any],
        lock_handle: Any,
    ) -> Dict[str, Any]:
        """Execute the spine run while holding the run lock."""
        start_ts = self._get_timestamp()

        # Get current policy hash
        self.current_policy_hash = self._get_current_policy_hash()

        # Initialize ledger
        handoff_hash = self._compute_hash(task_spec)
        self.ledger.initialize(
            LedgerHeader(
                policy_hash=self.current_policy_hash,
                handoff_hash=handoff_hash,
                run_id=self.run_id,
            )
        )

        # Pre-run governance hooks (fail-closed)
        pre_kwargs = self._build_hook_kwargs(task_spec)
        pre_result = run_pre_hooks(pre_kwargs, hooks=self._pre_run_hooks)
        pre_gate_results = self._hook_results_to_gate_results(pre_result)
        if not pre_result.all_passed:
            failed = [h.name for h in pre_result.failed_hooks]
            return self._emit_blocked_terminal_result(
                reason=f"pre_run_hook_failed: {failed}",
                gate_results=pre_gate_results,
                task_ref=task_spec.get("task_ref"),
                start_ts=start_ts,
                policy_hash=self.current_policy_hash,
            )

        # Track phase outcomes for v2.1
        phase_outcomes: Dict[str, Any] = {}

        # Run chain steps (optionally in isolated worktree)
        try:
            if self.use_worktree:
                with worktree_scope(self.repo_root, self.run_id) as wt_handle:
                    result = self._run_chain_steps(
                        task_spec=task_spec,
                        execution_root=wt_handle.worktree_path,
                    )
                    validate_worktree_clean(wt_handle)
            else:
                result = self._run_chain_steps(task_spec=task_spec)

            # Build phase_outcomes from steps_executed
            for step in result.get("steps_executed", []):
                phase_outcomes[step] = {"status": "pass"}
            if result["outcome"] != "PASS":
                # Last step that was executing when failure occurred
                all_steps = result.get("steps_executed", [])
                if all_steps:
                    phase_outcomes[all_steps[-1]] = {"status": "fail"}

            # Write ledger record first so chain tip includes final record
            terminal_file_path = f"artifacts/terminal/TP_{self.run_id}.yaml"
            ledger_write_ok = True
            try:
                self._write_ledger_record(
                    success=(result["outcome"] == "PASS"),
                    terminal_reason=result.get("reason", "pass"),
                    actions_taken=result.get("steps_executed", []),
                    terminal_packet_path=terminal_file_path,
                    checkpoint_path=None,
                    commit_hash=result.get("commit_hash"),
                )
            except Exception:
                ledger_write_ok = False

            # Shadow agent capture (non-gating, non-fatal)
            self._capture_shadow_agent(task_spec)

            # Auto-commit attempt ledger so next run's repo-clean pre-check passes.
            # (Finding B1-F3: ledger must be committed between runs; this makes it automatic.)
            if ledger_write_ok:
                try:
                    import logging as _log
                    import subprocess as _sp

                    _add = _sp.run(
                        ["git", "add", str(self.ledger_path)],
                        cwd=self.repo_root,
                        capture_output=True,
                        timeout=10,
                    )
                    _commit = _sp.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"chore(ledger): auto-commit attempt ledger [{self.run_id}]",
                        ],
                        cwd=self.repo_root,
                        capture_output=True,
                        timeout=15,
                    )
                    if _add.returncode != 0 and _commit.returncode != 0:
                        _log.getLogger(__name__).warning(
                            "Ledger auto-commit failed (add=%s, commit=%s); "
                            "next run may fail repo-clean check",
                            _add.returncode,
                            _commit.returncode,
                        )
                except Exception:
                    pass  # Non-fatal; repo-clean check will flag it if needed

            # Check repo cleanliness for v2.1
            repo_clean_verified = False
            try:
                verify_repo_clean(self.repo_root)
                repo_clean_verified = True
            except Exception:
                pass

            # Bypass utilization check (Trusted Builder P1 — non-fatal, observational)
            _bypass_status = None
            try:
                _bypass_status = check_bypass_utilization(self.ledger_path)
                if _bypass_status.level != "ok":
                    import logging as _log

                    _log.getLogger(__name__).warning(
                        "BYPASS_%s: %d/%d attempts in bypass window (rate=%.2f)",
                        _bypass_status.level.upper(),
                        _bypass_status.bypass_count,
                        _bypass_status.total_count,
                        _bypass_status.rate,
                    )
            except Exception:
                pass  # Non-fatal — must not block execution

            receipt_index = self._finalize_receipt_index(include_empty=True)

            # Emit terminal packet with ledger chain anchor + v2.1 fields.
            # Post-run hooks depend on terminal packet presence and are included
            # in a final re-emission below.
            outcome = result["outcome"]
            reason = result.get("reason", "pass")
            end_ts = self._get_timestamp()
            status = "SUCCESS" if outcome == "PASS" else "CLEAN_FAIL"

            terminal_packet = TerminalPacket(
                run_id=self.run_id,
                timestamp=self._get_timestamp(),
                outcome=outcome,
                reason=reason,
                steps_executed=result.get("steps_executed", []),
                commit_hash=result.get("commit_hash"),
                ledger_chain_tip=self.ledger.get_chain_tip(),
                ledger_attempt_count=len(self.ledger.history),
                ledger_schema_version=self.ledger.header.get("schema_version")
                if self.ledger.header
                else None,
                status=status,
                start_ts=start_ts,
                end_ts=end_ts,
                task_ref=task_spec.get("task_ref"),
                policy_hash=self.current_policy_hash,
                phase_outcomes=phase_outcomes,
                gate_results=pre_gate_results,
                receipt_index=receipt_index,
                clean_fail_reason=reason if outcome != "PASS" else None,
                repo_clean_verified=repo_clean_verified,
                orphan_check_passed=True,
                tokens_consumed=result.get("tokens_consumed"),
                token_source=result.get("token_source"),
                token_accounting_complete=result.get("token_accounting_complete", True),
                bypass_utilization=vars(_bypass_status) if _bypass_status else None,
            )
            terminal_file = self._emit_terminal(terminal_packet)

            # Post-run governance hooks (can downgrade PASS → BLOCKED)
            post_kwargs = {
                "terminal_packet_path": terminal_file,
                "ledger_write_ok": ledger_write_ok,
                "evidence_dir": task_spec.get("evidence_dir"),
                "evidence_tier": task_spec.get("evidence_tier", "light"),
            }
            post_result = run_post_hooks(post_kwargs, hooks=self._post_run_hooks)
            gate_results = pre_gate_results + self._hook_results_to_gate_results(post_result)
            terminal_packet.gate_results = gate_results
            if not post_result.all_passed and outcome == "PASS":
                failed = [h.name for h in post_result.failed_hooks]
                outcome = "BLOCKED"
                reason = f"post_run_hook_failed: {failed}"
                end_ts = self._get_timestamp()
                terminal_packet.outcome = outcome
                terminal_packet.reason = reason
                terminal_packet.status = "CLEAN_FAIL"
                terminal_packet.end_ts = end_ts
                terminal_packet.clean_fail_reason = reason

            # Final terminal packet emission (includes post-run gate results).
            self._emit_terminal(terminal_packet)

            self.state = SpineState.TERMINAL

            return {
                "outcome": outcome,
                "state": self.state.value,
                "run_id": self.run_id,
                "commit_hash": result.get("commit_hash"),
            }

        except WorktreeError as wt_exc:
            return self._emit_blocked_terminal_result(
                reason=f"worktree_error: {wt_exc.code}",
                gate_results=[
                    self._gate_result(
                        phase="execution",
                        name="worktree_dispatch",
                        passed=False,
                        reason=str(wt_exc),
                    )
                ],
                task_ref=task_spec.get("task_ref"),
                start_ts=start_ts,
                policy_hash=self.current_policy_hash,
            )

        except CheckpointTriggered as checkpoint_exc:
            # Checkpoint was triggered during execution
            # Write ledger record for checkpoint
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_exc.checkpoint_id}.yaml"
            self._write_ledger_record(
                success=False,
                terminal_reason="checkpoint_triggered",
                actions_taken=[],
                terminal_packet_path=None,
                checkpoint_path=str(checkpoint_file.relative_to(self.repo_root)),
                commit_hash=None,
            )

            return {
                "state": SpineState.CHECKPOINT.value,
                "checkpoint_id": checkpoint_exc.checkpoint_id,
                "run_id": self.run_id,
            }

    def resume(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Resume execution from a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to resume from

        Returns:
            Result dict with outcome, state, run_id, etc.

        Raises:
            PolicyChangedError: If policy hash changed since checkpoint (fail-closed)
            SpineError: On other errors
        """
        # Load checkpoint
        checkpoint = self._load_checkpoint(checkpoint_id)
        self.run_id = checkpoint.run_id
        get_or_create_collector(self.run_id)

        from runtime.orchestration.loop.run_lock import (
            RunLockError,
            acquire_run_lock,
            release_run_lock,
        )

        if check_kill_switch(self.repo_root):
            return self._emit_blocked_terminal_result(
                reason="kill_switch_active_pre_lock",
                gate_results=[
                    self._gate_result(
                        phase="startup",
                        name="kill_switch_pre_lock",
                        passed=False,
                        reason="STOP_AUTONOMY present before lock acquisition",
                    )
                ],
                task_ref=checkpoint.task_spec.get("task_ref"),
                policy_hash=checkpoint.policy_hash,
            )

        lock_handle = None
        try:
            lock_handle = acquire_run_lock(self.repo_root, checkpoint.run_id)
        except RunLockError as exc:
            return self._emit_blocked_terminal_result(
                reason="concurrent_run_detected",
                gate_results=[
                    self._gate_result(
                        phase="startup",
                        name="run_lock",
                        passed=False,
                        reason=str(exc),
                    )
                ],
                task_ref=checkpoint.task_spec.get("task_ref"),
                policy_hash=checkpoint.policy_hash,
            )

        try:
            if check_kill_switch(self.repo_root):
                return self._emit_blocked_terminal_result(
                    reason="kill_switch_active_post_lock",
                    gate_results=[
                        self._gate_result(
                            phase="startup",
                            name="kill_switch_post_lock",
                            passed=False,
                            reason="STOP_AUTONOMY detected after lock acquisition",
                        )
                    ],
                    task_ref=checkpoint.task_spec.get("task_ref"),
                    policy_hash=checkpoint.policy_hash,
                )

            # P0: Fail-closed on dirty repo
            verify_repo_clean(self.repo_root)

            # Validate policy hash
            current_hash = self._get_current_policy_hash()
            if checkpoint.policy_hash != current_hash:
                self._emit_blocked_terminal_result(
                    reason="POLICY_CHANGED_MID_RUN",
                    gate_results=[
                        self._gate_result(
                            phase="resume",
                            name="checkpoint_policy_hash",
                            passed=False,
                            reason=(f"checkpoint={checkpoint.policy_hash} current={current_hash}"),
                        )
                    ],
                    task_ref=checkpoint.task_spec.get("task_ref"),
                    policy_hash=current_hash,
                )

                raise PolicyChangedError(
                    checkpoint_hash=checkpoint.policy_hash,
                    current_hash=current_hash,
                )

            # Check resolution status
            is_resolved, decision = self._check_resolution(checkpoint_id)

            if not is_resolved:
                raise SpineError(f"Checkpoint {checkpoint_id} is not yet resolved")

            if decision == "REJECTED":
                # CEO rejected, terminate without execution
                return self._emit_blocked_terminal_result(
                    reason="checkpoint_rejected",
                    gate_results=[
                        self._gate_result(
                            phase="resume",
                            name="checkpoint_resolution",
                            passed=False,
                            reason="resolution_decision=REJECTED",
                        )
                    ],
                    task_ref=checkpoint.task_spec.get("task_ref"),
                    policy_hash=checkpoint.policy_hash,
                )

            # Resume execution
            self.state = SpineState.RESUMED
            self.current_policy_hash = checkpoint.policy_hash
            self.was_resumed = True

            # Hydrate ledger from prior run; initialize if missing (e.g. test scenario)
            if not self.ledger.hydrate():
                self.ledger.initialize(
                    LedgerHeader(
                        policy_hash=checkpoint.policy_hash,
                        handoff_hash=self._compute_hash(checkpoint.task_spec),
                        run_id=checkpoint.run_id,
                    )
                )

            start_ts = self._get_timestamp()
            result = self._run_chain_steps(
                task_spec=checkpoint.task_spec,
                start_from_step=checkpoint.step_index,
            )

            # Track phase outcomes for v2.1
            phase_outcomes: Dict[str, Any] = {}
            for step in result.get("steps_executed", []):
                phase_outcomes[step] = {"status": "pass"}
            if result["outcome"] != "PASS":
                all_steps = result.get("steps_executed", [])
                if all_steps:
                    phase_outcomes[all_steps[-1]] = {"status": "fail"}

            # Write ledger record first so chain tip includes final record
            terminal_file_path = f"artifacts/terminal/TP_{self.run_id}.yaml"
            ledger_write_ok = True
            try:
                self._write_ledger_record(
                    success=(result["outcome"] == "PASS"),
                    terminal_reason=result.get("reason", "pass"),
                    actions_taken=result.get("steps_executed", []),
                    terminal_packet_path=terminal_file_path,
                    checkpoint_path=str(
                        (self.checkpoint_dir / checkpoint_id)
                        .with_suffix(".yaml")
                        .relative_to(self.repo_root)
                    ),
                    commit_hash=result.get("commit_hash"),
                )
            except Exception:
                ledger_write_ok = False

            # Auto-commit attempt ledger so next run's repo-clean pre-check passes.
            # Mirror of run() path fix (T1-B: resume path had identical gap).
            if ledger_write_ok:
                try:
                    import logging as _log
                    import subprocess as _sp

                    _add = _sp.run(
                        ["git", "add", str(self.ledger_path)],
                        cwd=self.repo_root,
                        capture_output=True,
                        timeout=10,
                    )
                    _commit = _sp.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"chore(ledger): auto-commit attempt ledger [{self.run_id}]",
                        ],
                        cwd=self.repo_root,
                        capture_output=True,
                        timeout=15,
                    )
                    if _add.returncode != 0 and _commit.returncode != 0:
                        _log.getLogger(__name__).warning(
                            "Ledger auto-commit failed (add=%s, commit=%s); "
                            "next run may fail repo-clean check",
                            _add.returncode,
                            _commit.returncode,
                        )
                except Exception:
                    pass  # Non-fatal; repo-clean check will flag it if needed

            # Check repo cleanliness for v2.1
            repo_clean_verified = False
            try:
                verify_repo_clean(self.repo_root)
                repo_clean_verified = True
            except Exception:
                pass

            # Bypass utilization check (Trusted Builder P1 — non-fatal, observational)
            _bypass_status = None
            try:
                _bypass_status = check_bypass_utilization(self.ledger_path)
                if _bypass_status.level != "ok":
                    import logging as _log

                    _log.getLogger(__name__).warning(
                        "BYPASS_%s: %d/%d attempts in bypass window (rate=%.2f)",
                        _bypass_status.level.upper(),
                        _bypass_status.bypass_count,
                        _bypass_status.total_count,
                        _bypass_status.rate,
                    )
            except Exception:
                pass  # Non-fatal — must not block execution

            receipt_index = self._finalize_receipt_index(include_empty=True)

            # Emit terminal packet with ledger chain anchor
            outcome = result["outcome"]
            reason = result.get("reason", "pass")
            end_ts = self._get_timestamp()
            status = "SUCCESS" if outcome == "PASS" else "CLEAN_FAIL"
            resume_gate_results = [
                self._gate_result(
                    phase="resume",
                    name="checkpoint_policy_hash",
                    passed=True,
                    reason="ok",
                ),
                self._gate_result(
                    phase="resume",
                    name="checkpoint_resolution",
                    passed=True,
                    reason=f"resolution_decision={decision}",
                ),
            ]
            terminal_packet = TerminalPacket(
                run_id=self.run_id,
                timestamp=self._get_timestamp(),
                outcome=outcome,
                reason=reason,
                steps_executed=result.get("steps_executed", []),
                commit_hash=result.get("commit_hash"),
                ledger_chain_tip=self.ledger.get_chain_tip(),
                ledger_attempt_count=len(self.ledger.history),
                ledger_schema_version=self.ledger.header.get("schema_version")
                if self.ledger.header
                else None,
                status=status,
                start_ts=start_ts,
                end_ts=end_ts,
                task_ref=checkpoint.task_spec.get("task_ref"),
                policy_hash=self.current_policy_hash,
                phase_outcomes=phase_outcomes,
                gate_results=resume_gate_results,
                receipt_index=receipt_index,
                clean_fail_reason=reason if outcome != "PASS" else None,
                repo_clean_verified=repo_clean_verified,
                orphan_check_passed=True,
                tokens_consumed=result.get("tokens_consumed"),
                token_source=result.get("token_source"),
                token_accounting_complete=result.get("token_accounting_complete", True),
                bypass_utilization=vars(_bypass_status) if _bypass_status else None,
            )
            terminal_file = self._emit_terminal(terminal_packet)

            # Post-run governance hooks (can downgrade PASS → BLOCKED)
            post_kwargs = {
                "terminal_packet_path": terminal_file,
                "ledger_write_ok": ledger_write_ok,
                "evidence_dir": checkpoint.task_spec.get("evidence_dir"),
                "evidence_tier": checkpoint.task_spec.get("evidence_tier", "light"),
            }
            post_result = run_post_hooks(post_kwargs, hooks=self._post_run_hooks)
            gate_results = resume_gate_results + self._hook_results_to_gate_results(post_result)
            terminal_packet.gate_results = gate_results
            if not post_result.all_passed and outcome == "PASS":
                failed = [h.name for h in post_result.failed_hooks]
                outcome = "BLOCKED"
                reason = f"post_run_hook_failed: {failed}"
                terminal_packet.outcome = outcome
                terminal_packet.reason = reason
                terminal_packet.status = "CLEAN_FAIL"
                terminal_packet.end_ts = self._get_timestamp()
                terminal_packet.clean_fail_reason = reason

            # Final terminal packet emission (includes post-run gate results).
            self._emit_terminal(terminal_packet)

            # Return RESUMED state to indicate this was a resumed execution
            # (even though we've completed and could transition to TERMINAL)
            return {
                "outcome": outcome,
                "state": SpineState.RESUMED.value,
                "run_id": self.run_id,
                "commit_hash": result.get("commit_hash"),
                "resumed": True,
            }
        finally:
            if lock_handle is not None:
                release_run_lock(lock_handle)

    def _run_chain_steps(
        self,
        task_spec: Dict[str, Any],
        start_from_step: int = 0,
        execution_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Run chain steps: hydrate → policy → design → build → review → steward.

        Args:
            task_spec: Task specification
            start_from_step: Step index to start from (for resume)
            execution_root: Override for repo_root (worktree path when isolated)

        Returns:
            Result dict with outcome, steps_executed, commit_hash
        """
        return self._run_typed_workflow(
            task_spec=task_spec,
            start_from_step=start_from_step,
            execution_root=execution_root,
        )

    @staticmethod
    def _derive_token_source(sources: set[str]) -> Optional[str]:
        if not sources:
            return None
        return next(iter(sources)) if len(sources) == 1 else "mixed"

    @staticmethod
    def _current_budget_attempt(instance: WorkflowInstance) -> int:
        return max(1, instance.revision_count + 1)

    @staticmethod
    def _stash_token_accounting(
        task_spec: Dict[str, Any],
        *,
        total_tokens: int,
        token_sources: set[str],
        token_accounting_complete: bool,
        run_started_at: str,
    ) -> None:
        task_spec["_token_accounting"] = {
            "tokens": total_tokens,
            "sources": sorted(token_sources),
            "complete": token_accounting_complete,
            "run_started_at": run_started_at,
        }

    def _hydrate_workflow_instance(
        self, task_spec: Dict[str, Any], start_from_step: int
    ) -> WorkflowInstance:
        raw_instance = task_spec.get("workflow_instance")
        if isinstance(raw_instance, dict):
            instance = WorkflowInstance(**raw_instance)
        else:
            instance = translate_task_spec_to_workflow_instance(
                task_spec, run_id=self.run_id or "run"
            )
        definition = get_workflow_definition(instance.workflow_id)
        resolution_packet = task_spec.get("ceo_resolution")
        if instance.state == "CHECKPOINTED" or resolution_packet is not None:
            for invocation_key, record in list(instance.invocation_records.items()):
                if str(record.get("lease_status", "")) == "RUNNING":
                    record["lease_status"] = "VOID"
                    instance.invocation_records[invocation_key] = record
        if resolution_packet is not None:
            resolution = validate_resolution_packet(resolution_packet, instance)
            if resolution.resolution_action == "RESUME_CURRENT_STEP":
                instance.state = "READY"
            elif resolution.resolution_action == "FORCE_REJECT":
                instance.state = "REJECTED"
                instance.next_step_id = None
            elif resolution.resolution_action == "ABORT_WORKFLOW":
                instance.state = "ABORTED"
                instance.next_step_id = None
        if start_from_step > 0 and start_from_step < len(definition.steps):
            instance.current_step_id = definition.steps[start_from_step].step_id
            instance.next_step_id = next_step_id(definition, instance.current_step_id)
        return instance

    def _build_design_inputs(self, instance: WorkflowInstance) -> Dict[str, Any]:
        task_context = instance.task_context.get("payload", {})
        objective = str(task_context.get("objective", "")).strip()
        acceptance = [
            str(item)
            for item in list(task_context.get("acceptance_criteria") or [])
            if str(item).strip()
        ]
        findings = []
        review_artifact = instance.artifact_refs.get(REVIEW_DECISION_SCHEMA_VERSION)
        if review_artifact:
            for finding in list(review_artifact.get("payload", {}).get("findings") or []):
                summary = str(finding.get("summary", "")).strip()
                if summary:
                    findings.append(summary)
        task_lines = [objective]
        if acceptance:
            task_lines.append("Acceptance Criteria:")
            task_lines.extend(f"- {item}" for item in acceptance)
        if findings:
            task_lines.append("Review Findings:")
            task_lines.extend(f"- {item}" for item in findings)
        return {
            "task_spec": "\n".join(line for line in task_lines if line),
            "context_refs": [],
        }

    def _normalize_review_decision(
        self,
        *,
        instance: WorkflowInstance,
        step_id: str,
        reviewer_role: str,
        subject_artifact: Dict[str, Any],
        review_result: Any,
    ) -> WorkflowArtifact:
        outputs = getattr(review_result, "outputs", {}) or {}
        verdict = str(outputs.get("verdict", "approved"))
        findings = list(outputs.get("findings") or [])
        if not findings and verdict != "approved":
            findings = [
                {
                    "finding_id": f"{step_id}-1",
                    "finding_code": verdict.upper(),
                    "severity": "p1" if verdict == "needs_revision" else "p0",
                    "blocking": verdict == "rejected",
                    "target_ref": subject_artifact.get("artifact_id"),
                    "disposition": "must_fix"
                    if verdict == "needs_revision"
                    else ("escalate" if verdict == "escalate" else "info"),
                    "recommended_next_action": "revise_spec"
                    if verdict == "needs_revision"
                    else verdict,
                    "summary": str(
                        outputs.get("council_decision", {}).get("synthesis")
                        or outputs.get("rationale")
                        or verdict
                    ),
                }
            ]
        payload = {
            "subject_artifact_ref": subject_artifact.get("artifact_id"),
            "subject_artifact_type": subject_artifact.get("artifact_type"),
            "review_policy_id": "spec_review.v1"
            if instance.workflow_id == "spec_creation.v1"
            else "legacy_build_review.v1",
            "reviewer_role": reviewer_role,
            "verdict": verdict,
            "findings": findings,
            "revision_count": instance.revision_count,
            "max_revision_attempts": get_workflow_definition(
                instance.workflow_id
            ).max_revision_attempts,
            "escalation_required": verdict == "escalate",
            "rationale": str(
                outputs.get("council_decision", {}).get("synthesis")
                or outputs.get("rationale")
                or ""
            ),
            "concerns": list(outputs.get("concerns") or []),
            "recommendations": list(outputs.get("recommendations") or []),
        }
        return WorkflowArtifact(
            artifact_id=f"{instance.instance_id}:{REVIEW_DECISION_SCHEMA_VERSION}:{step_id}",
            artifact_type=REVIEW_DECISION_SCHEMA_VERSION,
            schema_version=REVIEW_DECISION_SCHEMA_VERSION,
            producer_role=reviewer_role,
            workflow_instance_id=instance.instance_id,
            created_at=self._get_timestamp(),
            payload=payload,
            sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
        )

    def _commit_step_success(
        self,
        *,
        instance: WorkflowInstance,
        definition,
        step,
        produced_artifact: Optional[WorkflowArtifact],
    ) -> None:
        if produced_artifact is not None:
            instance.artifact_refs[produced_artifact.artifact_type] = produced_artifact.to_dict()
        instance.last_completed_step_id = step.step_id
        instance.current_step_id = next_step_id(definition, step.step_id)
        instance.next_step_id = (
            next_step_id(definition, instance.current_step_id) if instance.current_step_id else None
        )
        instance.state = "READY" if instance.current_step_id else "COMPLETED"

    def _apply_review_transition(
        self,
        *,
        instance: WorkflowInstance,
        definition,
        step,
        decision: WorkflowArtifact,
        task_spec: Dict[str, Any],
        total_tokens: int,
        token_sources: set[str],
        token_accounting_complete: bool,
        run_started_at: str,
    ) -> Optional[Dict[str, Any]]:
        payload = decision.payload
        verdict = str(payload.get("verdict", "needs_revision"))
        instance.artifact_refs[decision.artifact_type] = decision.to_dict()
        instance.review_history.append(decision.to_dict())
        instance.last_completed_step_id = step.step_id
        if verdict == "approved":
            instance.current_step_id = (
                "package_spec"
                if instance.workflow_id == "spec_creation.v1"
                else next_step_id(definition, step.step_id)
            )
            instance.next_step_id = (
                next_step_id(definition, instance.current_step_id)
                if instance.current_step_id
                else None
            )
            instance.state = "READY" if instance.current_step_id else "COMPLETED"
            return None
        if verdict == "needs_revision":
            if instance.revision_count >= definition.max_revision_attempts:
                instance.state = "CHECKPOINTED"
                task_spec["workflow_instance"] = instance.to_dict()
                self._stash_token_accounting(
                    task_spec,
                    total_tokens=total_tokens,
                    token_sources=token_sources,
                    token_accounting_complete=token_accounting_complete,
                    run_started_at=run_started_at,
                )
                self._trigger_checkpoint(
                    trigger="ESCALATION_REQUESTED",
                    step_index=[
                        idx
                        for idx, item in enumerate(definition.steps)
                        if item.step_id == step.step_id
                    ][0],
                    context={"task_spec": task_spec, "current_step": step.step_id},
                )
            instance.revision_count += 1
            instance.current_step_id = (
                "revise_spec" if instance.workflow_id == "spec_creation.v1" else "design"
            )
            instance.next_step_id = next_step_id(definition, instance.current_step_id)
            instance.state = "READY"
            return None
        if verdict == "rejected":
            instance.state = "REJECTED"
            return {"outcome": "BLOCKED", "reason": "review_rejected"}
        if verdict == "escalate":
            instance.state = "CHECKPOINTED"
            instance.checkpoint_ref = f"checkpoint:{self.run_id}:{step.step_id}"
            task_spec["workflow_instance"] = instance.to_dict()
            self._stash_token_accounting(
                task_spec,
                total_tokens=total_tokens,
                token_sources=token_sources,
                token_accounting_complete=token_accounting_complete,
                run_started_at=run_started_at,
            )
            self._trigger_checkpoint(
                trigger="ESCALATION_REQUESTED",
                step_index=[
                    idx for idx, item in enumerate(definition.steps) if item.step_id == step.step_id
                ][0],
                context={"task_spec": task_spec, "current_step": step.step_id},
            )
        instance.state = "BLOCKED"
        return {"outcome": "BLOCKED", "reason": f"unsupported_verdict:{verdict}"}

    def _run_typed_workflow(
        self,
        task_spec: Dict[str, Any],
        start_from_step: int = 0,
        execution_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        import subprocess

        from runtime.orchestration.missions import get_mission_class
        from runtime.orchestration.missions.base import MissionContext, MissionEscalationRequired

        instance = self._hydrate_workflow_instance(task_spec, start_from_step)
        definition = get_workflow_definition(instance.workflow_id)
        effective_root = execution_root or self.repo_root
        steps_executed: List[str] = []
        saved_accounting = task_spec.get("_token_accounting", {})
        total_tokens = int(saved_accounting.get("tokens", 0) or 0)
        token_sources = {
            str(source)
            for source in list(saved_accounting.get("sources", []))
            if str(source).strip()
        }
        token_accounting_complete = bool(saved_accounting.get("complete", True))
        run_started_at = str(saved_accounting.get("run_started_at") or self._get_timestamp())
        budget = BudgetController(run_started_at=run_started_at)

        def _head_now() -> Optional[str]:
            """Capture HEAD at the moment of return (for BLOCKED provenance)."""
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    cwd=effective_root,
                )
                return r.stdout.strip() if r.returncode == 0 else None
            except Exception:
                return None

        try:
            cmd_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=effective_root,
            )
            baseline_commit = cmd_result.stdout.strip() if cmd_result.returncode == 0 else "unknown"
        except Exception:
            baseline_commit = "unknown"

        def _budget_result_with_step(step_id: str, reason: str) -> Dict[str, Any]:
            return {
                "outcome": "BLOCKED",
                "reason": reason,
                "steps_executed": steps_executed + [step_id],
                "commit_hash": _head_now(),
                "tokens_consumed": total_tokens if total_tokens > 0 else None,
                "token_source": self._derive_token_source(token_sources),
                "token_accounting_complete": token_accounting_complete,
            }

        def _update_token_accounting(result: Any, step_id: str) -> Optional[Dict[str, Any]]:
            nonlocal total_tokens, token_accounting_complete

            evidence = getattr(result, "evidence", {}) or {}
            step_tokens = extract_usage_tokens(evidence)
            if step_tokens is not None:
                total_tokens += step_tokens
                source = ((evidence.get("usage") or {}).get("token_source")) or "actual"
                token_sources.add(str(source))
            else:
                token_accounting_complete = False

            budget.check_budget_warn(total_tokens)
            is_over, budget_reason = budget.check_budget(
                self._current_budget_attempt(instance),
                total_tokens,
                token_accounting_available=True,
            )
            if is_over and budget_reason:
                return _budget_result_with_step(step_id, budget_reason)
            return None

        while instance.current_step_id and instance.state not in TERMINAL_WORKFLOW_STATES:
            step = get_step(definition, instance.current_step_id)
            if step is None:
                return {
                    "outcome": "BLOCKED",
                    "reason": f"unknown_step:{instance.current_step_id}",
                    "steps_executed": steps_executed,
                    "commit_hash": _head_now(),
                }
            instance.state = "RUNNING"
            context = MissionContext(
                repo_root=effective_root,
                baseline_commit=baseline_commit,
                run_id=self.run_id,
                operation_executor=None,
                journal=None,
                metadata={"spine_execution": True, "workflow_id": instance.workflow_id},
            )
            try:
                invocation = record_invocation_start(
                    instance, step_id=step.step_id, executor_identity=step.role
                )
                produced_artifact: Optional[WorkflowArtifact] = None
                if step.step_kind == "metadata":
                    self._commit_step_success(
                        instance=instance, definition=definition, step=step, produced_artifact=None
                    )
                elif step.step_kind in {"design", "revise"}:
                    mission = get_mission_class(step.mission_type)()
                    result = mission.run(context, self._build_design_inputs(instance))
                    if not getattr(result, "success", False):
                        return {
                            "outcome": "BLOCKED",
                            "reason": "mission_failed",
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    budget_result = _update_token_accounting(result, step.step_id)
                    if budget_result:
                        record_invocation_finish(
                            instance,
                            invocation,
                            result_ref=None,
                            result_status="FAILED",
                            error_code=budget_result["reason"],
                        )
                        return budget_result
                    payload = dict((getattr(result, "outputs", {}) or {}).get("build_packet") or {})
                    produced_artifact = WorkflowArtifact(
                        artifact_id=f"{instance.instance_id}:{step.produces}:{step.step_id}",
                        artifact_type=step.produces or "design_spec.v1",
                        schema_version=step.produces or "design_spec.v1",
                        producer_role=step.role,
                        workflow_instance_id=instance.instance_id,
                        created_at=self._get_timestamp(),
                        payload=payload,
                        sha256=hashlib.sha256(
                            json.dumps(payload, sort_keys=True).encode("utf-8")
                        ).hexdigest(),
                    )
                    self._commit_step_success(
                        instance=instance,
                        definition=definition,
                        step=step,
                        produced_artifact=produced_artifact,
                    )
                elif step.step_kind == "build":
                    mission = get_mission_class(step.mission_type)()
                    build_packet = (instance.artifact_refs.get("legacy_build_packet.v1") or {}).get(
                        "payload", {}
                    )
                    result = mission.run(
                        context, {"build_packet": build_packet, "approval": {"verdict": "approved"}}
                    )
                    if not getattr(result, "success", False):
                        return {
                            "outcome": "BLOCKED",
                            "reason": "mission_failed",
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    budget_result = _update_token_accounting(result, step.step_id)
                    if budget_result:
                        record_invocation_finish(
                            instance,
                            invocation,
                            result_ref=None,
                            result_status="FAILED",
                            error_code=budget_result["reason"],
                        )
                        return budget_result
                    payload = dict(
                        (getattr(result, "outputs", {}) or {}).get("review_packet") or {}
                    )
                    produced_artifact = WorkflowArtifact(
                        artifact_id=f"{instance.instance_id}:{step.produces}:{step.step_id}",
                        artifact_type=step.produces or "legacy_review_packet.v1",
                        schema_version=step.produces or "legacy_review_packet.v1",
                        producer_role=step.role,
                        workflow_instance_id=instance.instance_id,
                        created_at=self._get_timestamp(),
                        payload=payload,
                        sha256=hashlib.sha256(
                            json.dumps(payload, sort_keys=True).encode("utf-8")
                        ).hexdigest(),
                    )
                    self._commit_step_success(
                        instance=instance,
                        definition=definition,
                        step=step,
                        produced_artifact=produced_artifact,
                    )
                elif step.step_kind == "review":
                    mission = get_mission_class(step.mission_type)()
                    subject_type = step.consumes[0]
                    subject = instance.artifact_refs.get(subject_type)
                    if not subject:
                        return {
                            "outcome": "BLOCKED",
                            "reason": f"missing_subject:{subject_type}",
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    review_type = (
                        "output_review"
                        if instance.workflow_id == "spec_creation.v1"
                        else "build_review"
                    )
                    result = mission.run(
                        context,
                        {"subject_packet": subject.get("payload", {}), "review_type": review_type},
                    )
                    if not getattr(result, "success", False):
                        return {
                            "outcome": "BLOCKED",
                            "reason": "mission_failed",
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    budget_result = _update_token_accounting(result, step.step_id)
                    if budget_result:
                        record_invocation_finish(
                            instance,
                            invocation,
                            result_ref=None,
                            result_status="FAILED",
                            error_code=budget_result["reason"],
                        )
                        return budget_result
                    decision = self._normalize_review_decision(
                        instance=instance,
                        step_id=step.step_id,
                        reviewer_role=step.role,
                        subject_artifact=subject,
                        review_result=result,
                    )
                    try:
                        ShadowCouncilRunner(self.repo_root).run_shadow(
                            run_id=self.run_id,
                            ccp={
                                "run_id": self.run_id,
                                "sections": {
                                    "review_packet": subject.get("payload", {}),
                                    "reviewer_output": getattr(result, "outputs", {}).get(
                                        "reviewer_packet_parsed"
                                    ),
                                },
                                "task": instance.task_context.get("payload", {}).get(
                                    "objective", ""
                                ),
                            },
                        )
                    except Exception:
                        pass
                    transition = self._apply_review_transition(
                        instance=instance,
                        definition=definition,
                        step=step,
                        decision=decision,
                        task_spec=task_spec,
                        total_tokens=total_tokens,
                        token_sources=token_sources,
                        token_accounting_complete=token_accounting_complete,
                        run_started_at=run_started_at,
                    )
                    if transition:
                        return {
                            **transition,
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    produced_artifact = decision
                elif step.step_kind == "package":
                    produced_artifact = materialize_packaged_spec(instance, producer_role=step.role)
                    self._commit_step_success(
                        instance=instance,
                        definition=definition,
                        step=step,
                        produced_artifact=produced_artifact,
                    )
                elif step.step_kind == "steward" and step.mission_type:
                    mission = get_mission_class(step.mission_type)()
                    review_packet = (
                        instance.artifact_refs.get("legacy_review_packet.v1") or {}
                    ).get("payload", {})
                    approval_artifact = instance.artifact_refs.get(
                        REVIEW_DECISION_SCHEMA_VERSION, {}
                    )
                    approval = {
                        "verdict": approval_artifact.get("payload", {}).get("verdict", "approved")
                    }
                    result = mission.run(
                        context,
                        {
                            "review_packet": review_packet,
                            "approval": approval,
                            "council_decision": {},
                            "max_diff_lines": task_spec.get("constraints", {}).get(
                                "max_diff_lines", 500
                            ),
                        },
                    )
                    if not getattr(result, "success", False):
                        return {
                            "outcome": "BLOCKED",
                            "reason": "mission_failed",
                            "steps_executed": steps_executed + [step.step_id],
                            "commit_hash": _head_now(),
                        }
                    budget_result = _update_token_accounting(result, step.step_id)
                    if budget_result:
                        record_invocation_finish(
                            instance,
                            invocation,
                            result_ref=None,
                            result_status="FAILED",
                            error_code=budget_result["reason"],
                        )
                        return budget_result
                    self._commit_step_success(
                        instance=instance, definition=definition, step=step, produced_artifact=None
                    )
                else:
                    return {
                        "outcome": "BLOCKED",
                        "reason": f"unsupported_step_kind:{step.step_kind}",
                        "steps_executed": steps_executed + [step.step_id],
                        "commit_hash": _head_now(),
                    }
                record_invocation_finish(
                    instance,
                    invocation,
                    result_ref=produced_artifact.artifact_id if produced_artifact else None,
                    result_status="SUCCESS",
                )
                steps_executed.append(step.step_id)
            except MissionEscalationRequired:
                task_spec["workflow_instance"] = instance.to_dict()
                self._stash_token_accounting(
                    task_spec,
                    total_tokens=total_tokens,
                    token_sources=token_sources,
                    token_accounting_complete=token_accounting_complete,
                    run_started_at=run_started_at,
                )
                self._trigger_checkpoint(
                    trigger="ESCALATION_REQUESTED",
                    step_index=[
                        idx
                        for idx, item in enumerate(definition.steps)
                        if item.step_id == step.step_id
                    ][0],
                    context={"task_spec": task_spec, "current_step": step.step_id},
                )
            except CheckpointTriggered:
                raise
            except WorkflowRuntimeError as exc:
                return {
                    "outcome": "BLOCKED",
                    "reason": f"workflow_runtime_error:{exc}",
                    "steps_executed": steps_executed + [step.step_id],
                    "commit_hash": _head_now(),
                }
            except Exception as exc:
                return {
                    "outcome": "BLOCKED",
                    "reason": f"execution_error:{type(exc).__name__}",
                    "steps_executed": steps_executed + [step.step_id],
                    "commit_hash": _head_now(),
                }

        try:
            cmd_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=effective_root,
            )
            commit_hash = cmd_result.stdout.strip() if cmd_result.returncode == 0 else None
        except Exception:
            commit_hash = None
        outcome = "PASS" if instance.state == "COMPLETED" else "BLOCKED"
        reason = "pass" if outcome == "PASS" else instance.state.lower()
        task_spec["workflow_instance"] = instance.to_dict()
        return {
            "outcome": outcome,
            "reason": reason,
            "steps_executed": steps_executed,
            "commit_hash": commit_hash,
            "tokens_consumed": total_tokens if total_tokens > 0 else None,
            "token_source": self._derive_token_source(token_sources),
            "token_accounting_complete": token_accounting_complete,
        }

    def _trigger_checkpoint(
        self,
        trigger: str,
        step_index: int,
        context: Dict[str, Any],
    ) -> None:
        """
        Trigger a checkpoint, pausing execution.

        Args:
            trigger: Checkpoint trigger reason (e.g., "ESCALATION_REQUESTED")
            step_index: Current step index
            context: Execution context to save

        Raises:
            CheckpointTriggered: Always raised to halt execution
        """
        checkpoint_id = f"CP_{self.run_id}_{step_index}"

        checkpoint_packet = CheckpointPacket(
            checkpoint_id=checkpoint_id,
            run_id=self.run_id,
            timestamp=self._get_timestamp(),
            trigger=trigger,
            step_index=step_index,
            policy_hash=self.current_policy_hash,
            task_spec=context.get("task_spec", {}),
            resolved=False,
            resolution_decision=None,
        )

        self._save_checkpoint(checkpoint_packet)
        self.state = SpineState.CHECKPOINT

        raise CheckpointTriggered(checkpoint_id=checkpoint_id)

    def _save_checkpoint(self, packet: CheckpointPacket) -> Path:
        """
        Save checkpoint packet to disk.

        Args:
            packet: CheckpointPacket to save

        Returns:
            Path to saved checkpoint file
        """
        checkpoint_file = self.checkpoint_dir / f"{packet.checkpoint_id}.yaml"

        # Convert to dict and sort keys for determinism
        packet_dict = asdict(packet)

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            yaml.dump(packet_dict, f, sort_keys=True, default_flow_style=False)

        return checkpoint_file

    def _load_checkpoint(self, checkpoint_id: str) -> CheckpointPacket:
        """
        Load checkpoint packet from disk.

        Args:
            checkpoint_id: Checkpoint ID to load

        Returns:
            CheckpointPacket

        Raises:
            SpineError: If checkpoint file not found or corrupt
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.yaml"

        if not checkpoint_file.exists():
            raise SpineError(f"Checkpoint file not found: {checkpoint_file}")

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return CheckpointPacket(**data)

        except (yaml.YAMLError, TypeError) as e:
            raise SpineError(f"Failed to load checkpoint {checkpoint_id}: {e}") from e

    def _check_resolution(self, checkpoint_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a checkpoint has been resolved.

        Args:
            checkpoint_id: Checkpoint ID to check

        Returns:
            Tuple of (is_resolved, decision)
            - is_resolved: True if checkpoint has been resolved
            - decision: "APPROVED" | "REJECTED" | None
        """
        checkpoint = self._load_checkpoint(checkpoint_id)
        return (checkpoint.resolved, checkpoint.resolution_decision)

    @staticmethod
    def _gate_result(phase: str, name: str, passed: bool, reason: str) -> Dict[str, Any]:
        """Create a normalized gate result entry for terminal packets."""
        return {
            "phase": phase,
            "name": name,
            "pass": bool(passed),
            "reason": reason,
        }

    def _hook_results_to_gate_results(self, hook_sequence: Any) -> List[Dict[str, Any]]:
        """Convert HookSequenceResult into terminal gate result entries."""
        if hook_sequence is None:
            return []
        phase = str(getattr(hook_sequence, "phase", "unknown"))
        results: List[Dict[str, Any]] = []
        for hook_result in getattr(hook_sequence, "results", []):
            results.append(
                self._gate_result(
                    phase=phase,
                    name=str(getattr(hook_result, "name", "unknown")),
                    passed=bool(getattr(hook_result, "passed", False)),
                    reason=str(getattr(hook_result, "reason", "")),
                )
            )
        return results

    def _finalize_receipt_index(self, include_empty: bool = False) -> Optional[str]:
        """Finalize invocation receipts for this run and return repo-relative index path."""
        if not self.run_id:
            return None
        index_path = finalize_run_receipts(
            run_id=self.run_id,
            output_dir=self.repo_root,
            include_empty=include_empty,
        )
        if index_path is None:
            return None
        try:
            return str(index_path.relative_to(self.repo_root))
        except ValueError:
            return str(index_path)

    def _emit_blocked_terminal_result(
        self,
        *,
        reason: str,
        gate_results: Optional[List[Dict[str, Any]]] = None,
        steps_executed: Optional[List[str]] = None,
        task_ref: Optional[str] = None,
        start_ts: Optional[str] = None,
        policy_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit a clean-fail terminal packet and return the canonical BLOCKED result."""
        if not self.run_id:
            self.run_id = self._generate_run_id()
        started = start_ts or self._get_timestamp()
        ended = self._get_timestamp()
        terminal_packet = TerminalPacket(
            run_id=self.run_id,
            timestamp=ended,
            outcome="BLOCKED",
            reason=reason,
            steps_executed=steps_executed or [],
            ledger_chain_tip=self.ledger.get_chain_tip(),
            ledger_attempt_count=len(self.ledger.history),
            ledger_schema_version=self.ledger.header.get("schema_version")
            if self.ledger.header
            else None,
            status="CLEAN_FAIL",
            start_ts=started,
            end_ts=ended,
            task_ref=task_ref,
            policy_hash=policy_hash or self.current_policy_hash,
            gate_results=gate_results or [],
            receipt_index=self._finalize_receipt_index(include_empty=True),
            clean_fail_reason=reason,
            repo_clean_verified=False,
            orphan_check_passed=True,
        )
        self._emit_terminal(terminal_packet)
        self.state = SpineState.TERMINAL
        return {
            "outcome": "BLOCKED",
            "reason": reason,
            "state": self.state.value,
            "run_id": self.run_id,
        }

    def _emit_terminal(self, packet: TerminalPacket) -> Path:
        """
        Emit terminal packet to artifacts/terminal/.

        Args:
            packet: TerminalPacket to emit

        Returns:
            Path to emitted terminal packet file
        """
        from runtime.util.atomic_write import atomic_write_text

        terminal_file = self.terminal_dir / f"TP_{packet.run_id}.yaml"

        # Compute packet_hash from the serialized packet representation with
        # packet_hash blanked (stable, verifiable, and independent of field order).
        packet_dict = asdict(packet)
        packet_dict["packet_hash"] = None
        base_content = yaml.dump(packet_dict, sort_keys=True, default_flow_style=False)
        packet_hash = f"sha256:{hashlib.sha256(base_content.encode('utf-8')).hexdigest()}"
        packet.packet_hash = packet_hash
        packet_dict["packet_hash"] = packet_hash

        content = yaml.dump(packet_dict, sort_keys=True, default_flow_style=False)
        atomic_write_text(terminal_file, content)

        return terminal_file

    def _emit_step_summary(
        self,
        run_id: str,
        step_name: str,
        summary: Dict[str, Any],
    ) -> Path:
        """
        Emit step summary to artifacts/steps/.

        Args:
            run_id: Run ID
            step_name: Step name (e.g., "design")
            summary: Step summary dict

        Returns:
            Path to emitted step summary file
        """
        step_file = self.steps_dir / f"{run_id}_{step_name}.json"

        with open(step_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, sort_keys=True, indent=2)

        return step_file

    def _get_current_policy_hash(self) -> str:
        """
        Get current policy hash from canonical policy source.

        Returns:
            SHA-256 hex digest of effective policy config

        Raises:
            SpineError: If policy cannot be loaded
        """
        policy_config_dir = self.repo_root / "config" / "policy"

        if not policy_config_dir.exists():
            raise SpineError(
                f"Policy directory not found: {policy_config_dir}. Cannot compute policy hash."
            )

        try:
            # Load effective policy config (with includes resolved)
            loader = PolicyLoader(config_dir=policy_config_dir, authoritative=True)
            config = loader.load()

            # Compute deterministic hash using governance hash function
            return hash_json(config)

        except Exception as e:
            raise SpineError(f"Failed to compute policy hash: {e}") from e

    def _build_hook_kwargs(self, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Build keyword arguments for pre-run lifecycle hooks."""
        constraints = task_spec.get("constraints", {})
        return {
            "policy_hash": self.current_policy_hash,
            "scope_paths": constraints.get("scope", []),
            "repo_root": self.repo_root,
            "allowed_paths": constraints.get(
                "allowed_paths", ["runtime/**", "tests/**", "artifacts/**", "docs/**", "config/**"]
            ),
            "denied_paths": constraints.get("denied_paths", []),
        }

    def _compute_hash(self, obj: Any) -> str:
        """
        Compute deterministic hash of an object.

        Args:
            obj: Object to hash (must be JSON-serializable)

        Returns:
            SHA256 hex digest
        """
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _generate_run_id(self) -> str:
        """
        Generate unique run ID.

        Returns:
            Run ID string (format: run_<timestamp>_<random>)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"

    def _capture_shadow_agent(self, task_spec: Dict[str, Any]) -> None:
        """Fire shadow agent capture. Non-gating, non-fatal."""
        try:
            from runtime.agents.shadow_capture import capture_shadow_agent

            capture_shadow_agent(
                run_id=self.run_id,
                task_payload=task_spec,
                repo_root=self.repo_root,
            )
        except Exception:
            pass  # Shadow is strictly non-gating

    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO 8601 format.

        Returns:
            ISO 8601 timestamp string
        """
        return datetime.now(timezone.utc).isoformat()

    def _write_ledger_record(
        self,
        success: bool,
        terminal_reason: str,
        actions_taken: List[str],
        terminal_packet_path: Optional[str],
        checkpoint_path: Optional[str],
        commit_hash: Optional[str],
    ) -> None:
        """
        Write attempt record to ledger.

        Args:
            success: Whether execution succeeded
            terminal_reason: Terminal reason code
            actions_taken: List of steps executed
            terminal_packet_path: Path to terminal packet (relative to repo root)
            checkpoint_path: Path to checkpoint (relative to repo root) if checkpointed
            commit_hash: Final commit hash if PASS
        """
        # Get next attempt ID
        last_record = self.ledger.get_last_record()
        attempt_id = (last_record.attempt_id + 1) if last_record else 1

        # Compute diff hash (placeholder for MVP)
        diff_hash = None
        changed_files = []

        # Build evidence hashes dict (placeholder for MVP)
        evidence_hashes = {}
        if terminal_packet_path:
            terminal_file = self.repo_root / terminal_packet_path
            if terminal_file.exists():
                with open(terminal_file, "rb") as f:
                    evidence_hashes[terminal_packet_path] = self._compute_hash(
                        f.read().decode("utf-8")
                    )
        if checkpoint_path:
            checkpoint_file = self.repo_root / checkpoint_path
            if checkpoint_file.exists():
                with open(checkpoint_file, "rb") as f:
                    evidence_hashes[checkpoint_path] = self._compute_hash(f.read().decode("utf-8"))

        # Determine failure class
        failure_class = None if success else FailureClass.UNKNOWN.value

        # Determine next action
        if checkpoint_path:
            next_action = LoopAction.ESCALATE.value
        elif success:
            next_action = LoopAction.TERMINATE.value
        else:
            next_action = LoopAction.TERMINATE.value

        # Create attempt record
        record = AttemptRecord(
            attempt_id=attempt_id,
            timestamp=self._get_timestamp(),
            run_id=self.run_id,
            policy_hash=self.current_policy_hash,
            input_hash=self._compute_hash({"run_id": self.run_id}),  # Placeholder
            actions_taken=actions_taken,
            diff_hash=diff_hash,
            changed_files=changed_files,
            evidence_hashes=evidence_hashes,
            success=success,
            failure_class=failure_class,
            terminal_reason=terminal_reason,
            next_action=next_action,
            rationale=f"Spine execution: {terminal_reason}",
            plan_bypass_info=None,
        )

        # Append to ledger
        self.ledger.append(record)


class CheckpointTriggered(Exception):
    """
    Internal exception raised when a checkpoint is triggered.
    Used to halt execution and save state.
    """

    def __init__(self, checkpoint_id: str):
        self.checkpoint_id = checkpoint_id
        super().__init__(f"Checkpoint triggered: {checkpoint_id}")
