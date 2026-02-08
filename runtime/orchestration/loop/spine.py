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

import json
import hashlib
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from runtime.orchestration.run_controller import verify_repo_clean, RepoDirtyError
from runtime.orchestration.loop.ledger import (
    AttemptLedger,
    AttemptRecord,
    LedgerHeader,
    LedgerIntegrityError,
)
from runtime.orchestration.loop.taxonomy import (
    TerminalOutcome,
    TerminalReason,
    FailureClass,
    LoopAction,
)
from runtime.api.governance_api import PolicyLoader, hash_json


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
    Terminal packet emitted when execution completes.

    Persisted to artifacts/terminal/TP_<run_id>.yaml
    """
    run_id: str
    timestamp: str  # ISO 8601
    outcome: str  # "PASS" | "BLOCKED" | "WAIVER_REQUESTED" | "ESCALATION_REQUESTED"
    reason: str  # TerminalReason value
    steps_executed: List[str]
    commit_hash: Optional[str] = None


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

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root)
        self.state = SpineState.INIT

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
        # P0: Fail-closed on dirty repo
        verify_repo_clean()

        # Generate run ID
        self.run_id = self._generate_run_id()
        self.state = SpineState.RUNNING

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

        # Run chain steps
        try:
            result = self._run_chain_steps(task_spec=task_spec)

            # Emit terminal packet
            terminal_packet = TerminalPacket(
                run_id=self.run_id,
                timestamp=self._get_timestamp(),
                outcome=result["outcome"],
                reason=result.get("reason", "pass"),
                steps_executed=result.get("steps_executed", []),
                commit_hash=result.get("commit_hash"),
            )

            terminal_file = self._emit_terminal(terminal_packet)
            self.state = SpineState.TERMINAL

            # Write ledger record for completed execution
            self._write_ledger_record(
                success=(result["outcome"] == "PASS"),
                terminal_reason=result.get("reason", "pass"),
                actions_taken=result.get("steps_executed", []),
                terminal_packet_path=str(terminal_file.relative_to(self.repo_root)),
                checkpoint_path=None,
                commit_hash=result.get("commit_hash"),
            )

            return {
                "outcome": result["outcome"],
                "state": self.state.value,
                "run_id": self.run_id,
                "commit_hash": result.get("commit_hash"),
            }

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
        # P0: Fail-closed on dirty repo
        verify_repo_clean()

        # Load checkpoint
        checkpoint = self._load_checkpoint(checkpoint_id)

        # Validate policy hash
        current_hash = self._get_current_policy_hash()
        if checkpoint.policy_hash != current_hash:
            # Emit terminal packet for BLOCKED
            terminal_packet = TerminalPacket(
                run_id=checkpoint.run_id,
                timestamp=self._get_timestamp(),
                outcome="BLOCKED",
                reason="POLICY_CHANGED_MID_RUN",
                steps_executed=[],
            )
            self._emit_terminal(terminal_packet)

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
            terminal_packet = TerminalPacket(
                run_id=checkpoint.run_id,
                timestamp=self._get_timestamp(),
                outcome="BLOCKED",
                reason="checkpoint_rejected",
                steps_executed=[],
            )
            self._emit_terminal(terminal_packet)

            return {
                "outcome": "BLOCKED",
                "reason": "checkpoint_rejected",
                "state": SpineState.TERMINAL.value,
                "run_id": checkpoint.run_id,
            }

        # Resume execution
        self.run_id = checkpoint.run_id
        self.state = SpineState.RESUMED
        self.current_policy_hash = checkpoint.policy_hash
        self.was_resumed = True

        # Continue from checkpoint step
        result = self._run_chain_steps(
            task_spec=checkpoint.task_spec,
            start_from_step=checkpoint.step_index,
        )

        # Emit terminal packet
        terminal_packet = TerminalPacket(
            run_id=self.run_id,
            timestamp=self._get_timestamp(),
            outcome=result["outcome"],
            reason=result.get("reason", "pass"),
            steps_executed=result.get("steps_executed", []),
            commit_hash=result.get("commit_hash"),
        )

        terminal_file = self._emit_terminal(terminal_packet)

        # Write ledger record for resumed execution
        self._write_ledger_record(
            success=(result["outcome"] == "PASS"),
            terminal_reason=result.get("reason", "pass"),
            actions_taken=result.get("steps_executed", []),
            terminal_packet_path=str(terminal_file.relative_to(self.repo_root)),
            checkpoint_path=str((self.checkpoint_dir / checkpoint_id).with_suffix('.yaml').relative_to(self.repo_root)),
            commit_hash=result.get("commit_hash"),
        )

        # Return RESUMED state to indicate this was a resumed execution
        # (even though we've completed and could transition to TERMINAL)
        return {
            "outcome": result["outcome"],
            "state": SpineState.RESUMED.value,
            "run_id": self.run_id,
            "commit_hash": result.get("commit_hash"),
            "resumed": True,
        }

    def _run_chain_steps(
        self,
        task_spec: Dict[str, Any],
        start_from_step: int = 0,
    ) -> Dict[str, Any]:
        """
        Run chain steps: hydrate → policy → design → build → review → steward.

        Args:
            task_spec: Task specification
            start_from_step: Step index to start from (for resume)

        Returns:
            Result dict with outcome, steps_executed, commit_hash
        """
        from runtime.orchestration.missions.base import MissionContext, MissionType, MissionEscalationRequired
        from runtime.orchestration.missions import get_mission_class
        import subprocess
        import uuid

        # Define chain steps
        chain_steps = [
            ("hydrate", None),  # Metadata step, no mission
            ("policy", None),   # Metadata step, no mission
            ("design", MissionType.DESIGN),
            ("build", MissionType.BUILD),
            ("review", MissionType.REVIEW),
            ("steward", MissionType.STEWARD),
        ]

        steps_executed = []
        chain_state = {}  # Accumulate outputs from each mission

        # Get baseline commit
        try:
            cmd_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=self.repo_root
            )
            baseline_commit = cmd_result.stdout.strip() if cmd_result.returncode == 0 else "unknown"
        except Exception:
            baseline_commit = "unknown"

        # Execute chain from start_from_step
        for step_idx in range(start_from_step, len(chain_steps)):
            step_name, mission_type = chain_steps[step_idx]

            if mission_type is None:
                # Metadata step (hydrate, policy) - just record
                steps_executed.append(step_name)
                continue

            # Create mission context
            context = MissionContext(
                repo_root=self.repo_root,
                baseline_commit=baseline_commit,
                run_id=self.run_id,
                operation_executor=None,
                journal=None,
                metadata={"spine_execution": True},
            )

            # Get mission class and instantiate
            try:
                mission_class = get_mission_class(mission_type)
                mission = mission_class()

                # Prepare inputs based on step position in chain
                if step_name == "design":
                    # Design: raw task spec
                    inputs = {
                        "task_spec": task_spec.get("task", ""),
                        "context_refs": task_spec.get("context_refs", []),
                    }
                elif step_name == "build":
                    # Build: needs build_packet from design + auto-approval
                    build_packet = chain_state.get("build_packet", {})
                    inputs = {
                        "build_packet": build_packet,
                        "approval": {"verdict": "approved"},
                    }
                elif step_name == "review":
                    # Review: needs review_packet from build as subject_packet
                    review_packet = chain_state.get("review_packet", {})
                    inputs = {
                        "subject_packet": review_packet,
                        "review_type": "code_review",
                    }
                elif step_name == "steward":
                    # Steward: needs review_packet + approval from review
                    review_packet = chain_state.get("review_packet", {})
                    verdict = chain_state.get("verdict", {})
                    council_decision = chain_state.get("council_decision", {})
                    inputs = {
                        "review_packet": review_packet,
                        "approval": verdict.get("approved", True),  # Default approve in trusted mode
                        "council_decision": council_decision,
                    }
                else:
                    # Fallback for unknown steps
                    inputs = {
                        "task_spec": task_spec.get("task", ""),
                        "context_refs": task_spec.get("context_refs", []),
                    }

                # Execute mission
                result = mission.run(context, inputs)

                # Accumulate outputs for next step
                if hasattr(result, 'outputs') and result.outputs:
                    chain_state.update(result.outputs)

                # Check for escalation
                if hasattr(result, 'success') and not result.success:
                    # Mission failed - check if escalation or termination
                    if hasattr(result, 'outputs') and result.outputs.get('escalation_required'):
                        # Trigger checkpoint for escalation
                        self._trigger_checkpoint(
                            trigger="ESCALATION_REQUESTED",
                            step_index=step_idx,
                            context={"task_spec": task_spec, "current_step": step_name},
                        )
                    else:
                        # Terminal failure
                        return {
                            "outcome": "BLOCKED",
                            "reason": "mission_failed",
                            "steps_executed": steps_executed + [step_name],
                        }

                steps_executed.append(step_name)

            except MissionEscalationRequired as e:
                # Escalation raised - trigger checkpoint
                self._trigger_checkpoint(
                    trigger="ESCALATION_REQUESTED",
                    step_index=step_idx,
                    context={
                        "task_spec": task_spec,
                        "current_step": step_name,
                        "escalation_reason": e.reason,
                    },
                )
            except Exception as e:
                # Unexpected error - fail closed
                return {
                    "outcome": "BLOCKED",
                    "reason": f"execution_error: {type(e).__name__}",
                    "steps_executed": steps_executed + [step_name],
                }

        # Get final commit if steward succeeded
        try:
            cmd_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=self.repo_root
            )
            commit_hash = cmd_result.stdout.strip() if cmd_result.returncode == 0 else None
        except Exception:
            commit_hash = None

        return {
            "outcome": "PASS",
            "steps_executed": steps_executed,
            "commit_hash": commit_hash,
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

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
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
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            return CheckpointPacket(**data)

        except (yaml.YAMLError, TypeError) as e:
            raise SpineError(f"Failed to load checkpoint {checkpoint_id}: {e}")

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

    def _emit_terminal(self, packet: TerminalPacket) -> Path:
        """
        Emit terminal packet to artifacts/terminal/.

        Args:
            packet: TerminalPacket to emit

        Returns:
            Path to emitted terminal packet file
        """
        terminal_file = self.terminal_dir / f"TP_{packet.run_id}.yaml"

        # Convert to dict and sort keys for determinism
        packet_dict = asdict(packet)

        with open(terminal_file, 'w', encoding='utf-8') as f:
            yaml.dump(packet_dict, f, sort_keys=True, default_flow_style=False)

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

        with open(step_file, 'w', encoding='utf-8') as f:
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
                f"Policy directory not found: {policy_config_dir}. "
                "Cannot compute policy hash."
            )

        try:
            # Load effective policy config (with includes resolved)
            loader = PolicyLoader(config_dir=policy_config_dir, authoritative=True)
            config = loader.load()

            # Compute deterministic hash using governance hash function
            return hash_json(config)

        except Exception as e:
            raise SpineError(f"Failed to compute policy hash: {e}")

    def _compute_hash(self, obj: Any) -> str:
        """
        Compute deterministic hash of an object.

        Args:
            obj: Object to hash (must be JSON-serializable)

        Returns:
            SHA256 hex digest
        """
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def _generate_run_id(self) -> str:
        """
        Generate unique run ID.

        Returns:
            Run ID string (format: run_<timestamp>_<random>)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"

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
                with open(terminal_file, 'rb') as f:
                    evidence_hashes[terminal_packet_path] = self._compute_hash(f.read().decode('utf-8'))
        if checkpoint_path:
            checkpoint_file = self.repo_root / checkpoint_path
            if checkpoint_file.exists():
                with open(checkpoint_file, 'rb') as f:
                    evidence_hashes[checkpoint_path] = self._compute_hash(f.read().decode('utf-8'))

        # Determine failure class
        failure_class = None if success else FailureClass.UNKNOWN.value

        # Determine next action
        from runtime.orchestration.loop.taxonomy import LoopAction
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
