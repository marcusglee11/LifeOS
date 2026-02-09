"""Trusted validator orchestrator (v2.1a P0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Dict, Any, Optional
import uuid

from runtime.orchestration.workspace_lock import (
    WorkspaceLockError,
    acquire_workspace_lock,
    release_workspace_lock,
)
from runtime.validation.acceptor import AcceptanceTokenError, accept
from runtime.validation.attempts import RetryState, evaluate_retry
from runtime.validation.codes import get_code_spec
from runtime.validation.core import AttemptContext, CheckResult, JobSpec, RetryCaps, ValidationReport
from runtime.validation.gate_runner import GateRunner
from runtime.validation.reporting import write_json_atomic, write_validator_report


AgentRunner = Callable[[Path, JobSpec], None]


@dataclass(frozen=True)
class OrchestrationResult:
    success: bool
    run_id: str
    attempt_id: str
    attempt_index: int
    message: str
    validator_report_path: Optional[str] = None
    acceptance_token_path: Optional[str] = None
    acceptance_record_path: Optional[str] = None


class ValidationOrchestrator:
    """Trusted top-level orchestrator that owns retries and lock lifecycle."""

    def __init__(
        self,
        workspace_root: Path,
        gate_runner: GateRunner | None = None,
        lock_ttl_seconds: int = 900,
    ):
        self.workspace_root = workspace_root.resolve()
        self.gate_runner = gate_runner or GateRunner()
        self.lock_ttl_seconds = lock_ttl_seconds

    def _recovery_log_path(self, run_root: Path) -> Path:
        return run_root / "recovery_log.jsonl"

    def _append_recovery_event(self, run_root: Path, event: Dict[str, Any]) -> None:
        path = self._recovery_log_path(run_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")

    def _build_attempt_context(self, job_spec: JobSpec, attempt_id: str, attempt_index: int, retry_state: RetryState) -> AttemptContext:
        return AttemptContext(
            run_id=job_spec.run_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            max_attempts_per_gate_per_run=job_spec.retry_caps.max_attempts_per_gate_per_run,
            max_total_attempts_per_run=job_spec.retry_caps.max_total_attempts_per_run,
            max_consecutive_same_failure_code=job_spec.retry_caps.max_consecutive_same_failure_code,
            distinct_failure_codes_count=retry_state.distinct_failure_codes(),
            consecutive_same_failure_code=retry_state.consecutive_same_failure_code(),
        )

    def _emit_lock_failure_report(
        self,
        *,
        attempt_dir: Path,
        attempt_context: AttemptContext,
        message: str,
    ) -> Path:
        code = "CONCURRENT_RUN_DETECTED"
        spec = get_code_spec(code)
        report = ValidationReport(
            schema_version="validator_report_v1",
            passed=False,
            gate="preflight",
            summary_code=code,
            exit_code=spec.exit_code,
            message=message,
            classification=spec.classification,
            next_action=spec.default_next_action,
            checks=[CheckResult(name="workspace_lock", code=code, ok=False, message=message)],
            attempt_context=attempt_context,
            pointers={
                "attempt_dir": str(attempt_dir),
                "evidence_root": str(attempt_dir / "evidence"),
                "manifest_path": str(attempt_dir / "evidence" / "evidence_manifest.json"),
                "receipt_path": str(attempt_dir / "receipt.json"),
            },
        )
        report_path = attempt_dir / "validator_report.json"
        write_validator_report(report_path, report.to_dict())
        return report_path

    def run(
        self,
        *,
        mission_kind: str,
        evidence_tier: str,
        agent_runner: AgentRunner,
        run_id: Optional[str] = None,
        gate_pipeline_version: str = "v2.1a-p0",
        retry_caps: Optional[RetryCaps] = None,
        receipt_required: bool = False,
    ) -> OrchestrationResult:
        run_id = run_id or uuid.uuid4().hex
        caps = retry_caps or RetryCaps(
            max_attempts_per_gate_per_run=2,
            max_total_attempts_per_run=3,
            max_consecutive_same_failure_code=2,
        )

        run_root = self.workspace_root / "artifacts" / "validation_runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        retry_state = RetryState()
        lock_handle = None

        try:
            # Lock scope is the worktree workspace root, never the caller's main tree.
            lock_handle = acquire_workspace_lock(
                workspace_root=self.workspace_root,
                run_id=run_id,
                attempt_id="attempt-0000",
                ttl_seconds=self.lock_ttl_seconds,
            )
        except WorkspaceLockError as exc:
            attempt_id = "attempt-0000"
            attempt_dir = run_root / attempt_id
            attempt_dir.mkdir(parents=True, exist_ok=True)
            (attempt_dir / "evidence").mkdir(parents=True, exist_ok=True)

            bootstrap_job_spec = JobSpec(
                schema_version="job_spec_v1",
                run_id=run_id,
                mission_kind=mission_kind,
                evidence_tier=evidence_tier,  # type: ignore[arg-type]
                gate_pipeline_version=gate_pipeline_version,
                retry_caps=caps,
            )
            write_json_atomic(attempt_dir / "job_spec.json", bootstrap_job_spec.to_dict())
            attempt_context = self._build_attempt_context(bootstrap_job_spec, attempt_id, 0, retry_state)
            report_path = self._emit_lock_failure_report(
                attempt_dir=attempt_dir,
                attempt_context=attempt_context,
                message=str(exc),
            )
            self._append_recovery_event(
                run_root,
                {
                    "attempt_id": attempt_id,
                    "attempt_index": 0,
                    "gate": "preflight",
                    "code": "CONCURRENT_RUN_DETECTED",
                    "classification": "TERMINAL",
                    "next_action": "ESCALATE_TO_CEO",
                    "terminal": True,
                },
            )
            return OrchestrationResult(
                success=False,
                run_id=run_id,
                attempt_id=attempt_id,
                attempt_index=0,
                message=str(exc),
                validator_report_path=str(report_path),
            )

        try:
            for attempt_index in range(1, caps.max_total_attempts_per_run + 1):
                attempt_id = f"attempt-{attempt_index:04d}"
                attempt_dir = run_root / attempt_id
                evidence_root = attempt_dir / "evidence"
                attempt_dir.mkdir(parents=True, exist_ok=True)
                evidence_root.mkdir(parents=True, exist_ok=True)

                job_spec = JobSpec(
                    schema_version="job_spec_v1",
                    run_id=run_id,
                    mission_kind=mission_kind,
                    evidence_tier=evidence_tier,  # type: ignore[arg-type]
                    gate_pipeline_version=gate_pipeline_version,
                    retry_caps=caps,
                )
                write_json_atomic(attempt_dir / "job_spec.json", job_spec.to_dict())

                attempt_context = self._build_attempt_context(job_spec, attempt_id, attempt_index, retry_state)

                preflight = self.gate_runner.run_preflight(
                    workspace_root=self.workspace_root,
                    attempt_dir=attempt_dir,
                    attempt_context=attempt_context,
                )
                if not preflight.success:
                    retry_state.record_failure("preflight", preflight.code)
                    self._append_recovery_event(
                        run_root,
                        {
                            "attempt_id": attempt_id,
                            "attempt_index": attempt_index,
                            "gate": "preflight",
                            "code": preflight.code,
                            "classification": preflight.classification,
                            "next_action": preflight.next_action,
                            "terminal": True,
                            "policy": "all_preflight_failures_terminal_v2.1a",
                        },
                    )
                    return OrchestrationResult(
                        success=False,
                        run_id=run_id,
                        attempt_id=attempt_id,
                        attempt_index=attempt_index,
                        message=f"Preflight failed: {preflight.code}",
                        validator_report_path=str(preflight.report_path) if preflight.report_path else None,
                    )

                # Untrusted boundary: agent executes exactly once per attempt.
                agent_runner(attempt_dir, job_spec)

                postflight = self.gate_runner.run_postflight(
                    workspace_root=self.workspace_root,
                    attempt_dir=attempt_dir,
                    attempt_context=attempt_context,
                    receipt_required=receipt_required,
                )

                if postflight.success:
                    assert postflight.token_path is not None
                    try:
                        acceptance_record = accept(postflight.token_path)
                    except AcceptanceTokenError as exc:
                        retry_state.record_failure("postflight", exc.code)
                        self._append_recovery_event(
                            run_root,
                            {
                                "attempt_id": attempt_id,
                                "attempt_index": attempt_index,
                                "gate": "acceptor",
                                "code": exc.code,
                                "classification": "TERMINAL",
                                "next_action": "HALT_VALIDATOR_BUG",
                                "terminal": True,
                            },
                        )
                        return OrchestrationResult(
                            success=False,
                            run_id=run_id,
                            attempt_id=attempt_id,
                            attempt_index=attempt_index,
                            message=f"Acceptor rejected token: {exc}",
                            acceptance_token_path=str(postflight.token_path),
                        )

                    acceptance_record_path = postflight.token_path.parent / "acceptance_record.json"
                    self._append_recovery_event(
                        run_root,
                        {
                            "attempt_id": attempt_id,
                            "attempt_index": attempt_index,
                            "gate": "postflight",
                            "code": "SUCCESS",
                            "classification": "TERMINAL",
                            "next_action": "NONE",
                            "terminal": True,
                        },
                    )
                    return OrchestrationResult(
                        success=True,
                        run_id=run_id,
                        attempt_id=attempt_id,
                        attempt_index=attempt_index,
                        message="Accepted",
                        acceptance_token_path=str(postflight.token_path),
                        acceptance_record_path=str(acceptance_record_path),
                    )

                retry_state.record_failure("postflight", postflight.code)
                terminal_reason = evaluate_retry(
                    caps=caps,
                    state=retry_state,
                    gate="postflight",
                    code=postflight.code,
                    classification=postflight.classification,
                )
                terminal = terminal_reason is not None
                self._append_recovery_event(
                    run_root,
                    {
                        "attempt_id": attempt_id,
                        "attempt_index": attempt_index,
                        "gate": "postflight",
                        "code": postflight.code,
                        "classification": postflight.classification,
                        "next_action": postflight.next_action,
                        "terminal": terminal,
                        "terminal_reason": terminal_reason,
                    },
                )

                if terminal:
                    return OrchestrationResult(
                        success=False,
                        run_id=run_id,
                        attempt_id=attempt_id,
                        attempt_index=attempt_index,
                        message=f"Terminal failure: {terminal_reason}",
                        validator_report_path=str(postflight.report_path) if postflight.report_path else None,
                    )

            # Defensive fallback: should not be reachable due cap checks.
            return OrchestrationResult(
                success=False,
                run_id=run_id,
                attempt_id=f"attempt-{caps.max_total_attempts_per_run:04d}",
                attempt_index=caps.max_total_attempts_per_run,
                message="Retry loop exhausted",
            )
        finally:
            if lock_handle is not None:
                release_workspace_lock(lock_handle)
