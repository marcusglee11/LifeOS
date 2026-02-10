# Review Packet — Validator Suite v2.1a P0 v1.0

## Mission

AGENT INSTRUCTION BLOCK — Start Validator Suite v2.1a P0 in a NEW git worktree

## Outcome

PASS (P0 implementation completed in isolated worktree branch `validator-suite-v2.1a-p0`).

## Scope Delivered

- P0.1 Validation surface inventory and chokepoint map (`Validation_Surface_Map.md`).
- P0.2 Validation core types, stable code taxonomy, deterministic atomic report/token writers.
- P0.3 Evidence tier enforcement + strict manifest compute/verify with orphan failure policy.
- P0.4 Preflight/Postflight cleanliness checks and evidence-root ignore proof (`git check-ignore -v`).
- P0.5 Gate Runner + Acceptance Token + Acceptor hash-at-read acceptance flow.
- P0.6 Trusted Orchestrator + worktree-scoped workspace lock + retry loop with terminal preflight policy.
- P0.7 Unit tests + failure/success fixtures + sample artifacts.

## Evidence

- Worktree evidence log: `artifacts/validation_samples/v2.1a-p0/WORKTREE_EVIDENCE.md`
- Test output log: `artifacts/validation_samples/v2.1a-p0/pytest_output.txt`
- Sample failure report: `artifacts/validation_samples/v2.1a-p0/validator_report.json`
- Sample success token: `artifacts/validation_samples/v2.1a-p0/acceptance_token.json`

## Changed Paths

- `Validation_Surface_Map.md`
- `artifacts/validation_samples/v2.1a-p0/WORKTREE_EVIDENCE.md`
- `artifacts/validation_samples/v2.1a-p0/acceptance_token.json`
- `artifacts/validation_samples/v2.1a-p0/pytest_output.txt`
- `artifacts/validation_samples/v2.1a-p0/validator_report.json`
- `runtime/orchestration/orchestrator.py`
- `runtime/orchestration/workspace_lock.py`
- `runtime/tests/fixtures/validation/acceptance_token_success_fixture.json`
- `runtime/tests/fixtures/validation/validator_report_failure_fixture.json`
- `runtime/tests/orchestration/test_validation_orchestrator.py`
- `runtime/tests/orchestration/test_workspace_lock.py`
- `runtime/tests/validation/test_cleanliness.py`
- `runtime/tests/validation/test_evidence.py`
- `runtime/tests/validation/test_gate_runner_and_acceptor.py`
- `runtime/validation/__init__.py`
- `runtime/validation/acceptor.py`
- `runtime/validation/attempts.py`
- `runtime/validation/cleanliness.py`
- `runtime/validation/codes.py`
- `runtime/validation/core.py`
- `runtime/validation/evidence.py`
- `runtime/validation/gate_runner.py`
- `runtime/validation/reporting.py`

## Appendix A — Flattened Code for All Changed Files

### `Validation_Surface_Map.md`

````markdown
# Validation Surface Map — v2.1a P0

## Mission / Build Entrypoints

- `runtime/cli.py`: `cmd_mission_run()`
  - CLI mission entrypoint (`lifeos mission run ...`), currently dispatches into registry/engine and direct mission fallback.
- `runtime/orchestration/registry.py`: `run_mission()`
  - Canonical mission dispatch API for orchestration callers.
- `runtime/orchestration/engine.py`: `Orchestrator._execute_mission()`
  - Runtime mission execution boundary where mission types are resolved and executed.
- `runtime/orchestration/missions/build_with_validation.py`: `BuildWithValidationMission.run()`
  - Existing mission-local validation/evidence writer path.

## Acceptance / Gate-Like Paths (Existing)

- `runtime/orchestration/run_controller.py`: `mission_startup_sequence()`
  - Existing startup checks (kill switch, lock, repo clean, canon spine), but not token-based acceptance.
- `scripts/steward_runner.py`: `run_preflight()`, `run_validators()`, `run_postflight()`
  - Existing script-level pre/post runner with validator stage.
- `scripts/claude_session_complete.py`: `main()`
  - Existing multi-gate script orchestrator (review packet/doc gates), not autonomous build acceptance token flow.

## Validator / Capsule-Adjacent Clones

- `runtime/orchestration/validation.py`
  - Schema gate helper (`gate_check`) for payload/schema checks.
- `runtime/validator/anti_failure_validator.py`
  - Workflow validator package path (separate concern; potential naming collision risk with new validation suite).
- `runtime/workflows/validator.py`
  - Another workflow validation surface, not gate-token acceptance flow.
- `scripts/packaging/validate_return_packet_preflight.py`
  - Packet validation script with manifest checks (`08_evidence_manifest.sha256`).

## Recommended Integration Chokepoint (P0)

- Primary chokepoint: `runtime/orchestration/orchestrator.py:ValidationOrchestrator.run`
  - Trusted owner of retries, workspace lock, and job spec generation.
  - Calls trusted gate runner and acceptor; agent runner remains untrusted and single-shot.
- Gate boundary: `runtime/validation/gate_runner.py:GateRunner.run_preflight` and `runtime/validation/gate_runner.py:GateRunner.run_postflight`
  - Single emission boundary for deterministic `validator_report.json` failures and `acceptance_token.json` success.
- Acceptance boundary: `runtime/validation/acceptor.py:accept`
  - Non-bypassable token verification path; computes `acceptance_token_sha256` at read time.

## Notes

- Existing mission stack remains intact; v2.1a P0 adds a trusted validation pipeline adjacent to it.
- Worktree cleanliness and evidence root ignore proof are enforced against the active worktree root, not main tree state.
````

### `artifacts/validation_samples/v2.1a-p0/WORKTREE_EVIDENCE.md`

````markdown
# Worktree Evidence — Validator Suite v2.1a P0

## Main Tree (Read-Only Discovery)

Command:
```bash
git rev-parse --show-toplevel && echo '---' && git status --porcelain=v1 && echo '---' && git rev-parse HEAD
```

Output:
```text
/mnt/c/Users/cabra/Projects/LifeOS
---
---
5452fcce3d91aedd68dead9925f449780313fb70
```

## Worktree Creation / Recreation Output

Command executed:
```bash
git -C /mnt/c/Users/cabra/Projects/LifeOS worktree add -b validator-suite-v2.1a-p0 /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0 2eaade7a65a8c341d2486689b023327bc03bfc55
```

Observed output (key lines):
```text
Deleted branch validator-suite-v2.1a-p0 (was dd2ccea).
Preparing worktree (new branch 'validator-suite-v2.1a-p0')
HEAD is now at 2eaade7 chore(eol): normalize policy tests for clean worktree bootstrap
/mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
validator-suite-v2.1a-p0
2eaade7a65a8c341d2486689b023327bc03bfc55
```

## Worktree Clean-State Invariant

Pre-implementation check output (captured at setup time):
```text
0
```

Interpretation:
- `git status --porcelain=v1 | wc -l` returned `0` in the new worktree before any implementation edits.

## Worktree Authoritative Status (Post-Implementation)

Command:
```bash
git rev-parse --show-toplevel && git branch --show-current && echo '---' && git status --porcelain=v1 && echo '---' && git diff --name-only
```

Output:
```text
/mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
validator-suite-v2.1a-p0
---
?? Validation_Surface_Map.md
?? artifacts/validation_samples/
?? runtime/orchestration/orchestrator.py
?? runtime/orchestration/workspace_lock.py
?? runtime/tests/fixtures/validation/
?? runtime/tests/orchestration/test_validation_orchestrator.py
?? runtime/tests/orchestration/test_workspace_lock.py
?? runtime/tests/validation/
?? runtime/validation/
---
```

Untracked/changed paths list:
```text
Validation_Surface_Map.md
artifacts/validation_samples/v2.1a-p0/acceptance_token.json
artifacts/validation_samples/v2.1a-p0/pytest_output.txt
artifacts/validation_samples/v2.1a-p0/validator_report.json
runtime/orchestration/orchestrator.py
runtime/orchestration/workspace_lock.py
runtime/tests/fixtures/validation/acceptance_token_success_fixture.json
runtime/tests/fixtures/validation/validator_report_failure_fixture.json
runtime/tests/orchestration/test_validation_orchestrator.py
runtime/tests/orchestration/test_workspace_lock.py
runtime/tests/validation/test_cleanliness.py
runtime/tests/validation/test_evidence.py
runtime/tests/validation/test_gate_runner_and_acceptor.py
runtime/validation/__init__.py
runtime/validation/acceptor.py
runtime/validation/attempts.py
runtime/validation/cleanliness.py
runtime/validation/codes.py
runtime/validation/core.py
runtime/validation/evidence.py
runtime/validation/gate_runner.py
runtime/validation/reporting.py
```

## Test Command and Output

Command:
```bash
pytest -q runtime/tests/validation/test_evidence.py runtime/tests/validation/test_cleanliness.py runtime/tests/orchestration/test_workspace_lock.py runtime/tests/validation/test_gate_runner_and_acceptor.py runtime/tests/orchestration/test_validation_orchestrator.py
```

Output:
```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 15 items

runtime/tests/validation/test_evidence.py ...                            [ 20%]
runtime/tests/validation/test_cleanliness.py ...                         [ 40%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 60%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ...            [ 80%]
runtime/tests/orchestration/test_validation_orchestrator.py ...          [100%]

============================== 15 passed in 2.35s ==============================
```

## Sample Artifacts

- Failure sample: `artifacts/validation_samples/v2.1a-p0/validator_report.json`
- Success sample: `artifacts/validation_samples/v2.1a-p0/acceptance_token.json`
- Test output: `artifacts/validation_samples/v2.1a-p0/pytest_output.txt`
````

### `artifacts/validation_samples/v2.1a-p0/acceptance_token.json`

````json
{
  "schema_version": "acceptance_token_v1",
  "pass": true,
  "run_id": "run-fixture",
  "attempt_id": "attempt-0002",
  "attempt_index": 2,
  "gate_pipeline_version": "v2.1a-p0",
  "evidence_manifest_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "receipt_sha256": null,
  "created_at": "2026-02-09T00:00:00+00:00",
  "provenance": {
    "minted_by": "runtime.validation.gate_runner",
    "attempt_dir": "/tmp/attempt-0002",
    "evidence_root": "/tmp/attempt-0002/evidence",
    "manifest_path": "/tmp/attempt-0002/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0002/receipt.json"
  }
}
````

### `artifacts/validation_samples/v2.1a-p0/pytest_output.txt`

````text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 15 items

runtime/tests/validation/test_evidence.py ...                            [ 20%]
runtime/tests/validation/test_cleanliness.py ...                         [ 40%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 60%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ...            [ 80%]
runtime/tests/orchestration/test_validation_orchestrator.py ...          [100%]

============================== 15 passed in 2.35s ==============================
````

### `artifacts/validation_samples/v2.1a-p0/validator_report.json`

````json
{
  "schema_version": "validator_report_v1",
  "pass": false,
  "gate": "postflight",
  "summary_code": "EVIDENCE_ORPHAN_FILE",
  "exit_code": 33,
  "message": "Orphan evidence files detected: ['unexpected.log']",
  "classification": "RETRYABLE",
  "next_action": "RECAPTURE_EVIDENCE",
  "checks": [
    {
      "name": "evidence",
      "code": "EVIDENCE_ORPHAN_FILE",
      "ok": false,
      "message": "Orphan evidence files detected: ['unexpected.log']"
    }
  ],
  "attempt_context": {
    "run_id": "run-fixture",
    "attempt_id": "attempt-0001",
    "attempt_index": 1,
    "max_attempts_per_gate_per_run": 2,
    "max_total_attempts_per_run": 3,
    "max_consecutive_same_failure_code": 2,
    "distinct_failure_codes_count": 1,
    "consecutive_same_failure_code": 1
  },
  "pointers": {
    "attempt_dir": "/tmp/attempt-0001",
    "evidence_root": "/tmp/attempt-0001/evidence",
    "manifest_path": "/tmp/attempt-0001/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0001/receipt.json"
  }
}
````

### `runtime/orchestration/orchestrator.py`

````python
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
````

### `runtime/orchestration/workspace_lock.py`

````python
"""Trusted workspace lock with stale-lock handling for validator orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Dict


LOCK_RELATIVE_PATH = Path("artifacts/validation_runs/.validator_workspace.lock")


class WorkspaceLockError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class WorkspaceLockHandle:
    workspace_root: Path
    lock_path: Path
    run_id: str
    attempt_id: str


def lock_path_for_workspace(workspace_root: Path) -> Path:
    return workspace_root.resolve() / LOCK_RELATIVE_PATH


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_lock(lock_path: Path) -> Dict[str, Any]:
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def acquire_workspace_lock(
    workspace_root: Path,
    run_id: str,
    attempt_id: str,
    ttl_seconds: int = 900,
) -> WorkspaceLockHandle:
    workspace_root = workspace_root.resolve()
    lock_path = lock_path_for_workspace(workspace_root)
    now = int(time.time())

    payload = {
        "schema_version": "workspace_lock_v1",
        "pid": os.getpid(),
        "created_at_epoch": now,
        "run_id": run_id,
        "attempt_id": attempt_id,
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)

    for _ in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(payload, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                    handle.write("\n")
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            return WorkspaceLockHandle(workspace_root=workspace_root, lock_path=lock_path, run_id=run_id, attempt_id=attempt_id)
        except FileExistsError:
            existing = _load_lock(lock_path)
            existing_pid = int(existing.get("pid") or 0)
            created_at_epoch = int(existing.get("created_at_epoch") or 0)
            age_seconds = now - created_at_epoch if created_at_epoch else ttl_seconds + 1
            stale = (not existing_pid or not _is_pid_alive(existing_pid)) and age_seconds > ttl_seconds
            if stale:
                lock_path.unlink(missing_ok=True)
                continue
            holder_run_id = existing.get("run_id", "unknown")
            holder_attempt_id = existing.get("attempt_id", "unknown")
            raise WorkspaceLockError(
                "CONCURRENT_RUN_DETECTED",
                f"Workspace lock held by pid={existing_pid} run_id={holder_run_id} attempt_id={holder_attempt_id}",
            )

    raise WorkspaceLockError("CONCURRENT_RUN_DETECTED", "Unable to acquire workspace lock")


def release_workspace_lock(handle: WorkspaceLockHandle) -> bool:
    if not handle.lock_path.exists():
        return False

    payload = _load_lock(handle.lock_path)
    if payload.get("run_id") != handle.run_id:
        return False

    handle.lock_path.unlink(missing_ok=True)
    return True
````

### `runtime/tests/fixtures/validation/acceptance_token_success_fixture.json`

````json
{
  "schema_version": "acceptance_token_v1",
  "pass": true,
  "run_id": "run-fixture",
  "attempt_id": "attempt-0002",
  "attempt_index": 2,
  "gate_pipeline_version": "v2.1a-p0",
  "evidence_manifest_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "receipt_sha256": null,
  "created_at": "2026-02-09T00:00:00+00:00",
  "provenance": {
    "minted_by": "runtime.validation.gate_runner",
    "attempt_dir": "/tmp/attempt-0002",
    "evidence_root": "/tmp/attempt-0002/evidence",
    "manifest_path": "/tmp/attempt-0002/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0002/receipt.json"
  }
}
````

### `runtime/tests/fixtures/validation/validator_report_failure_fixture.json`

````json
{
  "schema_version": "validator_report_v1",
  "pass": false,
  "gate": "postflight",
  "summary_code": "EVIDENCE_ORPHAN_FILE",
  "exit_code": 33,
  "message": "Orphan evidence files detected: ['unexpected.log']",
  "classification": "RETRYABLE",
  "next_action": "RECAPTURE_EVIDENCE",
  "checks": [
    {
      "name": "evidence",
      "code": "EVIDENCE_ORPHAN_FILE",
      "ok": false,
      "message": "Orphan evidence files detected: ['unexpected.log']"
    }
  ],
  "attempt_context": {
    "run_id": "run-fixture",
    "attempt_id": "attempt-0001",
    "attempt_index": 1,
    "max_attempts_per_gate_per_run": 2,
    "max_total_attempts_per_run": 3,
    "max_consecutive_same_failure_code": 2,
    "distinct_failure_codes_count": 1,
    "consecutive_same_failure_code": 1
  },
  "pointers": {
    "attempt_dir": "/tmp/attempt-0001",
    "evidence_root": "/tmp/attempt-0001/evidence",
    "manifest_path": "/tmp/attempt-0001/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0001/receipt.json"
  }
}
````

### `runtime/tests/orchestration/test_validation_orchestrator.py`

````python
from __future__ import annotations

from pathlib import Path
import subprocess

from runtime.orchestration.orchestrator import ValidationOrchestrator
from runtime.validation.core import JobSpec, RetryCaps
from runtime.validation.evidence import compute_manifest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _light_agent_runner(attempt_dir: Path, _job_spec: JobSpec) -> None:
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
    (evidence_root / "exitcode.txt").write_text("0\n", encoding="utf-8")
    (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
    compute_manifest(evidence_root)


def test_orchestrator_success_path(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    orchestrator = ValidationOrchestrator(workspace_root=repo)

    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_light_agent_runner,
        run_id="run-success",
        retry_caps=RetryCaps(2, 3, 2),
    )

    assert result.success
    assert result.acceptance_token_path is not None
    assert result.acceptance_record_path is not None


def test_orchestrator_preflight_failure_is_terminal(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    calls = {"count": 0}

    def _agent_never_called(attempt_dir: Path, job_spec: JobSpec) -> None:
        _ = attempt_dir
        _ = job_spec
        calls["count"] += 1

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_agent_never_called,
        run_id="run-dirty-preflight",
        retry_caps=RetryCaps(2, 3, 2),
    )

    assert not result.success
    assert result.attempt_index == 1
    assert calls["count"] == 0
    assert result.validator_report_path is not None
    assert "validator_report.json" in result.validator_report_path


def test_orchestrator_owns_retry_loop(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    calls = {"count": 0}

    def _flaky_agent(attempt_dir: Path, _job_spec: JobSpec) -> None:
        calls["count"] += 1
        evidence_root = attempt_dir / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
        (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
        if calls["count"] >= 2:
            (evidence_root / "exitcode.txt").write_text("0\n", encoding="utf-8")
        compute_manifest(evidence_root)

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_flaky_agent,
        run_id="run-retry",
        retry_caps=RetryCaps(3, 3, 2),
    )

    assert result.success
    assert result.attempt_index == 2
    assert calls["count"] == 2
````

### `runtime/tests/orchestration/test_workspace_lock.py`

````python
from __future__ import annotations

from pathlib import Path
import json
import time

import pytest

from runtime.orchestration.workspace_lock import (
    WorkspaceLockError,
    acquire_workspace_lock,
    lock_path_for_workspace,
    release_workspace_lock,
)


def test_active_lock_detected(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    handle = acquire_workspace_lock(workspace, run_id="run-a", attempt_id="attempt-0001", ttl_seconds=60)

    try:
        with pytest.raises(WorkspaceLockError) as exc:
            acquire_workspace_lock(workspace, run_id="run-b", attempt_id="attempt-0001", ttl_seconds=60)
        assert exc.value.code == "CONCURRENT_RUN_DETECTED"
    finally:
        assert release_workspace_lock(handle)


def test_stale_lock_is_cleared(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    lock_path = lock_path_for_workspace(workspace)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    stale_payload = {
        "schema_version": "workspace_lock_v1",
        "pid": 999999,
        "created_at_epoch": int(time.time()) - 10_000,
        "run_id": "stale-run",
        "attempt_id": "attempt-0001",
    }
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    handle = acquire_workspace_lock(workspace, run_id="fresh-run", attempt_id="attempt-0001", ttl_seconds=10)
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        assert payload["run_id"] == "fresh-run"
    finally:
        assert release_workspace_lock(handle)


def test_dead_pid_within_ttl_still_blocks(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    lock_path = lock_path_for_workspace(workspace)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "workspace_lock_v1",
        "pid": 999999,
        "created_at_epoch": int(time.time()),
        "run_id": "other-run",
        "attempt_id": "attempt-0001",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(WorkspaceLockError) as exc:
        acquire_workspace_lock(workspace, run_id="run-new", attempt_id="attempt-0001", ttl_seconds=300)

    assert exc.value.code == "CONCURRENT_RUN_DETECTED"
````

### `runtime/tests/validation/test_cleanliness.py`

````python
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from runtime.validation.cleanliness import CleanlinessError, verify_evidence_root_ignored, verify_repo_clean


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def test_verify_repo_clean_detects_dirty_repo(git_repo: Path) -> None:
    (git_repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(CleanlinessError) as exc:
        verify_repo_clean(git_repo, code="DIRTY_REPO_PRE")

    assert exc.value.code == "DIRTY_REPO_PRE"


def test_verify_evidence_root_ignore_proof(git_repo: Path) -> None:
    evidence_root = git_repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    proof = verify_evidence_root_ignored(git_repo, evidence_root)
    assert ".gitignore" in proof


def test_verify_evidence_root_ignore_failure(git_repo: Path) -> None:
    evidence_root = git_repo / "non_ignored" / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(CleanlinessError) as exc:
        verify_evidence_root_ignored(git_repo, evidence_root)

    assert exc.value.code == "EVIDENCE_ROOT_NOT_IGNORED"
````

### `runtime/tests/validation/test_evidence.py`

````python
from __future__ import annotations

from pathlib import Path

import pytest

from runtime.validation.evidence import (
    EvidenceError,
    compute_manifest,
    enforce_evidence_tier,
    verify_manifest,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_light_evidence(evidence_root: Path) -> None:
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "exitcode.txt", "0\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"true\"}\n")


def test_enforce_tier_missing_required_file(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"true\"}\n")

    with pytest.raises(EvidenceError) as exc:
        enforce_evidence_tier(evidence_root, "light")

    assert exc.value.code == "EVIDENCE_MISSING_REQUIRED_FILE"


def test_manifest_compute_verify_and_orphan_detection(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    _build_light_evidence(evidence_root)

    compute_manifest(evidence_root)
    enforce_evidence_tier(evidence_root, "light")
    verify_manifest(evidence_root)

    _write(evidence_root / "unexpected.log", "orphan\n")

    with pytest.raises(EvidenceError) as exc:
        verify_manifest(evidence_root)

    assert exc.value.code == "EVIDENCE_ORPHAN_FILE"


def test_manifest_hash_mismatch_detected(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    _build_light_evidence(evidence_root)

    compute_manifest(evidence_root)
    _write(evidence_root / "meta.json", "{\"changed\":true}\n")

    with pytest.raises(EvidenceError) as exc:
        verify_manifest(evidence_root)

    assert exc.value.code == "EVIDENCE_HASH_MISMATCH"
````

### `runtime/tests/validation/test_gate_runner_and_acceptor.py`

````python
from __future__ import annotations

from pathlib import Path
import json
import subprocess

import pytest

from runtime.validation.acceptor import AcceptanceTokenError, accept
from runtime.validation.core import AttemptContext, JobSpec, RetryCaps
from runtime.validation.evidence import compute_manifest
from runtime.validation.gate_runner import GateRunner
from runtime.validation.reporting import write_json_atomic


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_light_evidence(evidence_root: Path) -> None:
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "exitcode.txt", "0\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"agent\"}\n")
    compute_manifest(evidence_root)


def _attempt_context() -> AttemptContext:
    return AttemptContext(
        run_id="run-1",
        attempt_id="attempt-0001",
        attempt_index=1,
        max_attempts_per_gate_per_run=2,
        max_total_attempts_per_run=3,
        max_consecutive_same_failure_code=2,
    )


def _job_spec(run_id: str = "run-1") -> JobSpec:
    return JobSpec(
        schema_version="job_spec_v1",
        run_id=run_id,
        mission_kind="build_with_validation",
        evidence_tier="light",
        gate_pipeline_version="v2.1a-p0",
        retry_caps=RetryCaps(2, 3, 2),
    )


def test_gate_runner_success_mints_token_and_acceptor_records_hash(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    _write_light_evidence(evidence_root)

    gate_runner = GateRunner()
    pre = gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    )
    assert pre.success

    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert post.success
    assert post.token_path is not None

    token_payload = json.loads(post.token_path.read_text(encoding="utf-8"))
    assert "token_sha256" not in token_payload

    record = accept(post.token_path)
    assert "acceptance_token_sha256" in record


def test_acceptor_rejects_invalid_token(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    _write_light_evidence(evidence_root)

    gate_runner = GateRunner()
    assert gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    ).success
    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert post.success
    assert post.token_path is not None

    payload = json.loads(post.token_path.read_text(encoding="utf-8"))
    payload["token_sha256"] = "illegal"
    write_json_atomic(post.token_path, payload)

    with pytest.raises(AcceptanceTokenError) as exc:
        accept(post.token_path)

    assert exc.value.code == "ACCEPTANCE_TOKEN_INVALID"


def test_validator_report_is_deterministic_for_same_failure(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    # Missing exitcode.txt intentionally; manifest includes only files present.
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"agent\"}\n")
    compute_manifest(evidence_root)

    gate_runner = GateRunner()
    assert gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    ).success

    first = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not first.success
    assert first.report_path is not None
    first_bytes = first.report_path.read_bytes()

    second = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not second.success
    assert second.report_path is not None
    second_bytes = second.report_path.read_bytes()

    assert first_bytes == second_bytes
````

### `runtime/validation/__init__.py`

````python
"""Validator suite v2.1a core package."""

from runtime.validation.core import (
    AttemptContext,
    CheckResult,
    JobSpec,
    RetryCaps,
    ValidationReport,
)
from runtime.validation.codes import CODE_SPECS, CodeSpec, get_code_spec

__all__ = [
    "AttemptContext",
    "CheckResult",
    "JobSpec",
    "RetryCaps",
    "ValidationReport",
    "CODE_SPECS",
    "CodeSpec",
    "get_code_spec",
]
````

### `runtime/validation/acceptor.py`

````python
"""Trusted acceptance token verifier and recorder."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict

from runtime.validation.reporting import sha256_file, write_json_atomic


class AcceptanceTokenError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


REQUIRED_TOKEN_FIELDS = {
    "schema_version",
    "pass",
    "run_id",
    "attempt_id",
    "attempt_index",
    "gate_pipeline_version",
    "evidence_manifest_sha256",
    "receipt_sha256",
    "created_at",
    "provenance",
}


def _load_token(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        token = json.load(handle)
    if not isinstance(token, dict):
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token payload must be an object")
    return token


def _verify_token_shape(token: Dict[str, Any]) -> None:
    if "token_sha256" in token:
        raise AcceptanceTokenError(
            "ACCEPTANCE_TOKEN_INVALID",
            "acceptance_token.json must not include token_sha256",
        )

    missing = sorted(REQUIRED_TOKEN_FIELDS - set(token.keys()))
    if missing:
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", f"Token missing required fields: {missing}")

    if token.get("schema_version") != "acceptance_token_v1":
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Unsupported token schema")

    if token.get("pass") is not True:
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token pass must be true")

    provenance = token.get("provenance")
    if not isinstance(provenance, dict):
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Token provenance must be an object")

    for key in ("manifest_path", "receipt_path", "attempt_dir"):
        if key not in provenance:
            raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", f"Token provenance missing {key}")


def accept(
    acceptance_token_path: Path,
    acceptance_record_path: Path | None = None,
) -> Dict[str, Any]:
    token = _load_token(acceptance_token_path)
    _verify_token_shape(token)

    provenance = token["provenance"]
    manifest_path = Path(provenance["manifest_path"])
    receipt_path = Path(provenance["receipt_path"])

    if not manifest_path.exists():
        raise AcceptanceTokenError("ACCEPTANCE_TOKEN_INVALID", "Referenced manifest_path does not exist")

    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != token["evidence_manifest_sha256"]:
        raise AcceptanceTokenError(
            "ACCEPTANCE_TOKEN_INVALID",
            "Manifest hash mismatch between token and disk",
        )

    receipt_sha = token.get("receipt_sha256")
    if receipt_sha is not None:
        if not receipt_path.exists():
            raise AcceptanceTokenError(
                "ACCEPTANCE_TOKEN_INVALID",
                "receipt_sha256 provided but receipt_path is missing",
            )
        disk_receipt_sha = sha256_file(receipt_path)
        if disk_receipt_sha != receipt_sha:
            raise AcceptanceTokenError(
                "ACCEPTANCE_TOKEN_INVALID",
                "Receipt hash mismatch between token and disk",
            )

    acceptance_token_sha256 = sha256_file(acceptance_token_path)

    record = {
        "schema_version": "acceptance_record_v1",
        "accepted": True,
        "run_id": token["run_id"],
        "attempt_id": token["attempt_id"],
        "attempt_index": token["attempt_index"],
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "token_path": str(acceptance_token_path),
        "manifest_path": str(manifest_path),
        "receipt_path": str(receipt_path),
        "evidence_manifest_sha256": token["evidence_manifest_sha256"],
        "receipt_sha256": receipt_sha,
        "acceptance_token_sha256": acceptance_token_sha256,
    }

    if acceptance_record_path is None:
        acceptance_record_path = acceptance_token_path.parent / "acceptance_record.json"
    write_json_atomic(acceptance_record_path, record)
    return record
````

### `runtime/validation/attempts.py`

````python
"""Retry-state helpers for trusted orchestrator decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from runtime.validation.core import RetryCaps


IMMEDIATE_TERMINAL_CODES = {
    "DIRTY_REPO_PRE",
    "EVIDENCE_ROOT_NOT_IGNORED",
    "CONCURRENT_RUN_DETECTED",
}


@dataclass
class RetryState:
    attempts_total: int = 0
    attempts_by_gate: Dict[str, int] = field(default_factory=dict)
    failure_codes: List[str] = field(default_factory=list)

    def record_failure(self, gate: str, code: str) -> None:
        self.attempts_total += 1
        self.attempts_by_gate[gate] = self.attempts_by_gate.get(gate, 0) + 1
        self.failure_codes.append(code)

    def distinct_failure_codes(self) -> int:
        return len(set(self.failure_codes))

    def consecutive_same_failure_code(self) -> int:
        if not self.failure_codes:
            return 0
        tail = self.failure_codes[-1]
        count = 0
        for code in reversed(self.failure_codes):
            if code != tail:
                break
            count += 1
        return count


def evaluate_retry(
    *,
    caps: RetryCaps,
    state: RetryState,
    gate: str,
    code: str,
    classification: str,
) -> Optional[str]:
    """Return terminal reason if retries must stop; otherwise None."""

    if classification == "TERMINAL":
        return f"terminal_classification:{code}"

    if code in IMMEDIATE_TERMINAL_CODES:
        return f"immediate_terminal_code:{code}"

    if state.attempts_total > caps.max_total_attempts_per_run:
        return "max_total_attempts_exceeded"

    if state.attempts_by_gate.get(gate, 0) > caps.max_attempts_per_gate_per_run:
        return f"max_attempts_per_gate_exceeded:{gate}"

    if state.consecutive_same_failure_code() > caps.max_consecutive_same_failure_code:
        return "max_consecutive_same_failure_code_exceeded"

    if state.distinct_failure_codes() >= 3:
        return "distinct_failure_codes_threshold_reached"

    return None
````

### `runtime/validation/cleanliness.py`

````python
"""Git cleanliness and evidence ignore proof checks."""

from __future__ import annotations

from pathlib import Path
import subprocess


class CleanlinessError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def verify_repo_clean(repo_root: Path, code: str) -> None:
    result = _run_git(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode != 0:
        raise CleanlinessError(code, f"git status failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if output:
        raise CleanlinessError(code, f"Repository is dirty:\n{output}")


def verify_evidence_root_ignored(repo_root: Path, evidence_root: Path) -> str:
    try:
        target = evidence_root.relative_to(repo_root).as_posix()
    except ValueError:
        target = str(evidence_root)

    result = _run_git(repo_root, ["check-ignore", "-v", target])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    message = result.stderr.strip() if result.stderr.strip() else f"No ignore rule matched: {target}"
    raise CleanlinessError("EVIDENCE_ROOT_NOT_IGNORED", message)
````

### `runtime/validation/codes.py`

````python
"""Stable validation/acceptance codes and exit mappings for v2.1a."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

Classification = Literal["RETRYABLE", "TERMINAL"]


@dataclass(frozen=True)
class CodeSpec:
    code: str
    exit_code: int
    classification: Classification
    default_next_action: str
    gate: str


CODE_SPECS: Dict[str, CodeSpec] = {
    # Preflight 10-19
    "DIRTY_REPO_PRE": CodeSpec(
        code="DIRTY_REPO_PRE",
        exit_code=10,
        classification="TERMINAL",
        default_next_action="HALT_DIRTY_REPO",
        gate="preflight",
    ),
    "CONCURRENT_RUN_DETECTED": CodeSpec(
        code="CONCURRENT_RUN_DETECTED",
        exit_code=11,
        classification="TERMINAL",
        default_next_action="ESCALATE_TO_CEO",
        gate="preflight",
    ),
    "EVIDENCE_ROOT_NOT_IGNORED": CodeSpec(
        code="EVIDENCE_ROOT_NOT_IGNORED",
        exit_code=12,
        classification="TERMINAL",
        default_next_action="HALT_SCHEMA_DRIFT",
        gate="preflight",
    ),
    # Postflight / evidence 30-39
    "DIRTY_REPO_POST": CodeSpec(
        code="DIRTY_REPO_POST",
        exit_code=30,
        classification="TERMINAL",
        default_next_action="HALT_DIRTY_REPO",
        gate="postflight",
    ),
    "EVIDENCE_MISSING_REQUIRED_FILE": CodeSpec(
        code="EVIDENCE_MISSING_REQUIRED_FILE",
        exit_code=31,
        classification="RETRYABLE",
        default_next_action="RECAPTURE_EVIDENCE",
        gate="postflight",
    ),
    "EVIDENCE_HASH_MISMATCH": CodeSpec(
        code="EVIDENCE_HASH_MISMATCH",
        exit_code=32,
        classification="RETRYABLE",
        default_next_action="RECAPTURE_EVIDENCE",
        gate="postflight",
    ),
    "EVIDENCE_ORPHAN_FILE": CodeSpec(
        code="EVIDENCE_ORPHAN_FILE",
        exit_code=33,
        classification="RETRYABLE",
        default_next_action="RECAPTURE_EVIDENCE",
        gate="postflight",
    ),
    # Internal 90-99
    "JOB_SPEC_INVALID": CodeSpec(
        code="JOB_SPEC_INVALID",
        exit_code=90,
        classification="TERMINAL",
        default_next_action="HALT_SCHEMA_DRIFT",
        gate="internal",
    ),
    "VALIDATOR_CRASH": CodeSpec(
        code="VALIDATOR_CRASH",
        exit_code=91,
        classification="TERMINAL",
        default_next_action="HALT_VALIDATOR_BUG",
        gate="internal",
    ),
    "ACCEPTANCE_TOKEN_INVALID": CodeSpec(
        code="ACCEPTANCE_TOKEN_INVALID",
        exit_code=92,
        classification="TERMINAL",
        default_next_action="HALT_VALIDATOR_BUG",
        gate="internal",
    ),
}


def get_code_spec(code: str) -> CodeSpec:
    """Return the stable code spec, raising if unknown."""
    try:
        return CODE_SPECS[code]
    except KeyError as exc:
        raise KeyError(f"Unknown validation code: {code}") from exc
````

### `runtime/validation/core.py`

````python
"""Core runtime types for validation suite v2.1a."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Literal


EvidenceTier = Literal["light", "standard", "full"]


class JobSpecError(ValueError):
    """Raised when trusted job spec validation fails."""


@dataclass(frozen=True)
class RetryCaps:
    max_attempts_per_gate_per_run: int
    max_total_attempts_per_run: int
    max_consecutive_same_failure_code: int


@dataclass(frozen=True)
class JobSpec:
    schema_version: str
    run_id: str
    mission_kind: str
    evidence_tier: EvidenceTier
    gate_pipeline_version: str
    retry_caps: RetryCaps

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "JobSpec":
        required = {
            "schema_version",
            "run_id",
            "mission_kind",
            "evidence_tier",
            "gate_pipeline_version",
            "max_attempts_per_gate_per_run",
            "max_total_attempts_per_run",
            "max_consecutive_same_failure_code",
        }
        actual = set(data.keys())
        missing = sorted(required - actual)
        extras = sorted(actual - required)
        if missing:
            raise JobSpecError(f"Missing required job_spec keys: {missing}")
        if extras:
            raise JobSpecError(f"Unexpected job_spec keys: {extras}")

        if data["schema_version"] != "job_spec_v1":
            raise JobSpecError("schema_version must be 'job_spec_v1'")

        tier = data["evidence_tier"]
        if tier not in {"light", "standard", "full"}:
            raise JobSpecError("evidence_tier must be one of: light, standard, full")

        for key in ("run_id", "mission_kind", "gate_pipeline_version"):
            if not isinstance(data[key], str) or not data[key].strip():
                raise JobSpecError(f"{key} must be a non-empty string")

        caps_raw = {
            "max_attempts_per_gate_per_run": data["max_attempts_per_gate_per_run"],
            "max_total_attempts_per_run": data["max_total_attempts_per_run"],
            "max_consecutive_same_failure_code": data["max_consecutive_same_failure_code"],
        }
        for key, value in caps_raw.items():
            if not isinstance(value, int) or value <= 0:
                raise JobSpecError(f"{key} must be a positive integer")

        return JobSpec(
            schema_version=data["schema_version"],
            run_id=data["run_id"],
            mission_kind=data["mission_kind"],
            evidence_tier=tier,
            gate_pipeline_version=data["gate_pipeline_version"],
            retry_caps=RetryCaps(**caps_raw),
        )

    @staticmethod
    def load(path: Path) -> "JobSpec":
        with open(path, "r", encoding="utf-8") as handle:
            return JobSpec.from_dict(json.load(handle))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "mission_kind": self.mission_kind,
            "evidence_tier": self.evidence_tier,
            "gate_pipeline_version": self.gate_pipeline_version,
            "max_attempts_per_gate_per_run": self.retry_caps.max_attempts_per_gate_per_run,
            "max_total_attempts_per_run": self.retry_caps.max_total_attempts_per_run,
            "max_consecutive_same_failure_code": self.retry_caps.max_consecutive_same_failure_code,
        }


@dataclass(frozen=True)
class AttemptContext:
    run_id: str
    attempt_id: str
    attempt_index: int
    max_attempts_per_gate_per_run: int
    max_total_attempts_per_run: int
    max_consecutive_same_failure_code: int
    distinct_failure_codes_count: int = 0
    consecutive_same_failure_code: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "attempt_index": self.attempt_index,
            "max_attempts_per_gate_per_run": self.max_attempts_per_gate_per_run,
            "max_total_attempts_per_run": self.max_total_attempts_per_run,
            "max_consecutive_same_failure_code": self.max_consecutive_same_failure_code,
            "distinct_failure_codes_count": self.distinct_failure_codes_count,
            "consecutive_same_failure_code": self.consecutive_same_failure_code,
        }


@dataclass(frozen=True)
class CheckResult:
    name: str
    code: str
    ok: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "code": self.code,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass(frozen=True)
class ValidationReport:
    schema_version: str
    passed: bool
    gate: str
    summary_code: str
    exit_code: int
    message: str
    classification: str
    next_action: str
    checks: List[CheckResult]
    attempt_context: AttemptContext
    pointers: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        checks_sorted = sorted(
            (c.to_dict() for c in self.checks),
            key=lambda c: (c["name"], c["code"], c["message"]),
        )
        return {
            "schema_version": self.schema_version,
            "pass": self.passed,
            "gate": self.gate,
            "summary_code": self.summary_code,
            "exit_code": self.exit_code,
            "message": self.message,
            "classification": self.classification,
            "next_action": self.next_action,
            "checks": checks_sorted,
            "attempt_context": self.attempt_context.to_dict(),
            "pointers": dict(sorted(self.pointers.items())),
        }
````

### `runtime/validation/evidence.py`

````python
"""Evidence tier enforcement and manifest compute/verify."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from runtime.validation.reporting import sha256_file, write_json_atomic


REQUIRED_FILES_BY_TIER: Dict[str, Set[str]] = {
    "light": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
    },
    "standard": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
        "stdout.txt",
        "stderr.txt",
        "git_head.txt",
        "git_status.txt",
    },
    "full": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
        "stdout.txt",
        "stderr.txt",
        "git_head.txt",
        "git_status.txt",
        "git_diff_name_only.txt",
    },
}


class EvidenceError(RuntimeError):
    def __init__(self, code: str, message: str, next_action: str = "RECAPTURE_EVIDENCE"):
        self.code = code
        self.next_action = next_action
        super().__init__(message)


def _iter_files(root: Path, exclude_relpaths: Iterable[str]) -> Iterable[Path]:
    excluded = set(exclude_relpaths)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        yield path


def required_files_for_tier(tier: str, extras: List[str] | None = None) -> Set[str]:
    if tier not in REQUIRED_FILES_BY_TIER:
        raise EvidenceError("JOB_SPEC_INVALID", f"Unsupported evidence tier: {tier}", "HALT_SCHEMA_DRIFT")
    required = set(REQUIRED_FILES_BY_TIER[tier])
    if extras:
        required.update(extras)
    return required


def enforce_evidence_tier(evidence_root: Path, tier: str, extras: List[str] | None = None) -> None:
    missing = []
    for rel in sorted(required_files_for_tier(tier, extras)):
        if not (evidence_root / rel).exists():
            missing.append(rel)
    if missing:
        raise EvidenceError(
            "EVIDENCE_MISSING_REQUIRED_FILE",
            f"Missing required evidence files for tier '{tier}': {missing}",
        )


def compute_manifest(evidence_root: Path, manifest_path: Path | None = None) -> Dict[str, Any]:
    if manifest_path is None:
        manifest_path = evidence_root / "evidence_manifest.json"

    manifest_rel = manifest_path.relative_to(evidence_root).as_posix()
    files = []
    for path in _iter_files(evidence_root, exclude_relpaths=[manifest_rel]):
        rel = path.relative_to(evidence_root).as_posix()
        files.append(
            {
                "relpath": rel,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    files_sorted = sorted(files, key=lambda entry: entry["relpath"])
    payload: Dict[str, Any] = {
        "schema_version": "evidence_manifest_v1",
        "files": files_sorted,
    }
    write_json_atomic(manifest_path, payload)
    return payload


def verify_manifest(evidence_root: Path, manifest_path: Path | None = None) -> Dict[str, Any]:
    if manifest_path is None:
        manifest_path = evidence_root / "evidence_manifest.json"

    if not manifest_path.exists():
        raise EvidenceError("EVIDENCE_MISSING_REQUIRED_FILE", "evidence_manifest.json is missing")

    with open(manifest_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("schema_version") != "evidence_manifest_v1":
        raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Unsupported evidence manifest schema")

    entries = payload.get("files")
    if not isinstance(entries, list):
        raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Manifest files must be a list")

    seen_relpaths: Set[str] = set()
    manifest_relpaths: Set[str] = set()
    for entry in entries:
        rel = entry.get("relpath")
        expected_sha = entry.get("sha256")
        if not isinstance(rel, str) or not isinstance(expected_sha, str):
            raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Manifest entry is malformed")
        if rel in seen_relpaths:
            raise EvidenceError("EVIDENCE_HASH_MISMATCH", f"Duplicate relpath in manifest: {rel}")
        seen_relpaths.add(rel)
        manifest_relpaths.add(rel)

        file_path = evidence_root / rel
        if not file_path.exists():
            raise EvidenceError("EVIDENCE_MISSING_REQUIRED_FILE", f"Missing evidence file: {rel}")

        actual_sha = sha256_file(file_path)
        if actual_sha != expected_sha:
            raise EvidenceError(
                "EVIDENCE_HASH_MISMATCH",
                f"Hash mismatch for {rel}: expected {expected_sha}, got {actual_sha}",
            )

    manifest_rel = manifest_path.relative_to(evidence_root).as_posix()
    actual_relpaths = {
        path.relative_to(evidence_root).as_posix()
        for path in _iter_files(evidence_root, exclude_relpaths=[manifest_rel])
    }
    orphan_relpaths = sorted(actual_relpaths - manifest_relpaths)
    if orphan_relpaths:
        raise EvidenceError(
            "EVIDENCE_ORPHAN_FILE",
            f"Orphan evidence files detected: {orphan_relpaths}",
            next_action="RECAPTURE_EVIDENCE",
        )

    return payload
````

### `runtime/validation/gate_runner.py`

````python
"""Trusted Gate Runner for validator suite v2.1a."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.validation.cleanliness import CleanlinessError, verify_evidence_root_ignored, verify_repo_clean
from runtime.validation.codes import get_code_spec
from runtime.validation.core import AttemptContext, CheckResult, JobSpec, JobSpecError, ValidationReport
from runtime.validation.evidence import EvidenceError, enforce_evidence_tier, verify_manifest
from runtime.validation.reporting import sha256_file, write_acceptance_token, write_validator_report


@dataclass(frozen=True)
class GateRunnerOutcome:
    success: bool
    gate: str
    code: str
    classification: str
    next_action: str
    report_path: Optional[Path] = None
    token_path: Optional[Path] = None


class GateRunner:
    """Trusted gate execution surface."""

    def __init__(self, gate_pipeline_version: str = "v2.1a-p0"):
        self.gate_pipeline_version = gate_pipeline_version

    def _report_failure(
        self,
        *,
        attempt_dir: Path,
        gate: str,
        code: str,
        message: str,
        attempt_context: AttemptContext,
        checks: List[CheckResult],
        pointers: Dict[str, Any],
        next_action: str | None = None,
    ) -> GateRunnerOutcome:
        code_spec = get_code_spec(code)
        report = ValidationReport(
            schema_version="validator_report_v1",
            passed=False,
            gate=gate,
            summary_code=code,
            exit_code=code_spec.exit_code,
            message=message,
            classification=code_spec.classification,
            next_action=next_action or code_spec.default_next_action,
            checks=checks,
            attempt_context=attempt_context,
            pointers=pointers,
        )
        report_path = attempt_dir / "validator_report.json"
        write_validator_report(report_path, report.to_dict())
        return GateRunnerOutcome(
            success=False,
            gate=gate,
            code=code,
            classification=code_spec.classification,
            next_action=next_action or code_spec.default_next_action,
            report_path=report_path,
        )

    def _load_job_spec(self, attempt_dir: Path) -> JobSpec:
        job_spec_path = attempt_dir / "job_spec.json"
        try:
            return JobSpec.load(job_spec_path)
        except (FileNotFoundError, JobSpecError, ValueError) as exc:
            raise JobSpecError(f"Invalid job_spec.json: {exc}") from exc

    def run_preflight(
        self,
        *,
        workspace_root: Path,
        attempt_dir: Path,
        attempt_context: AttemptContext,
    ) -> GateRunnerOutcome:
        evidence_root = attempt_dir / "evidence"
        pointers = {
            "attempt_dir": str(attempt_dir),
            "evidence_root": str(evidence_root),
            "manifest_path": str(evidence_root / "evidence_manifest.json"),
            "receipt_path": str(attempt_dir / "receipt.json"),
        }

        try:
            self._load_job_spec(attempt_dir)
        except JobSpecError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="preflight",
                code="JOB_SPEC_INVALID",
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="job_spec", code="JOB_SPEC_INVALID", ok=False, message=str(exc))],
                pointers=pointers,
            )

        try:
            verify_repo_clean(workspace_root, code="DIRTY_REPO_PRE")
            check_message = "repository clean"
        except CleanlinessError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="preflight",
                code=exc.code,
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="repo_clean_pre", code=exc.code, ok=False, message=str(exc))],
                pointers=pointers,
            )

        try:
            ignore_proof = verify_evidence_root_ignored(workspace_root, evidence_root)
        except CleanlinessError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="preflight",
                code=exc.code,
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="evidence_root_ignore", code=exc.code, ok=False, message=str(exc))],
                pointers=pointers,
            )

        return GateRunnerOutcome(
            success=True,
            gate="preflight",
            code="OK",
            classification="TERMINAL",
            next_action="NONE",
            report_path=None,
            token_path=None,
        )

    def run_postflight(
        self,
        *,
        workspace_root: Path,
        attempt_dir: Path,
        attempt_context: AttemptContext,
        receipt_required: bool = False,
    ) -> GateRunnerOutcome:
        evidence_root = attempt_dir / "evidence"
        manifest_path = evidence_root / "evidence_manifest.json"
        receipt_path = attempt_dir / "receipt.json"

        pointers = {
            "attempt_dir": str(attempt_dir),
            "evidence_root": str(evidence_root),
            "manifest_path": str(manifest_path),
            "receipt_path": str(receipt_path),
        }

        try:
            job_spec = self._load_job_spec(attempt_dir)
        except JobSpecError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="postflight",
                code="JOB_SPEC_INVALID",
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="job_spec", code="JOB_SPEC_INVALID", ok=False, message=str(exc))],
                pointers=pointers,
            )

        try:
            enforce_evidence_tier(evidence_root, job_spec.evidence_tier)
            verify_manifest(evidence_root, manifest_path=manifest_path)
            verify_repo_clean(workspace_root, code="DIRTY_REPO_POST")
        except EvidenceError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="postflight",
                code=exc.code,
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="evidence", code=exc.code, ok=False, message=str(exc))],
                pointers=pointers,
                next_action=exc.next_action,
            )
        except CleanlinessError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="postflight",
                code=exc.code,
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="repo_clean_post", code=exc.code, ok=False, message=str(exc))],
                pointers=pointers,
            )

        manifest_sha = sha256_file(manifest_path)
        receipt_sha: Optional[str] = None
        if receipt_required:
            if not receipt_path.exists():
                return self._report_failure(
                    attempt_dir=attempt_dir,
                    gate="postflight",
                    code="EVIDENCE_MISSING_REQUIRED_FILE",
                    message="receipt.json is required but missing",
                    attempt_context=attempt_context,
                    checks=[
                        CheckResult(
                            name="receipt_required",
                            code="EVIDENCE_MISSING_REQUIRED_FILE",
                            ok=False,
                            message="receipt.json missing",
                        )
                    ],
                    pointers=pointers,
                    next_action="REGENERATE_RECEIPT",
                )
            receipt_sha = sha256_file(receipt_path)

        token_payload: Dict[str, Any] = {
            "schema_version": "acceptance_token_v1",
            "pass": True,
            "run_id": attempt_context.run_id,
            "attempt_id": attempt_context.attempt_id,
            "attempt_index": attempt_context.attempt_index,
            "gate_pipeline_version": job_spec.gate_pipeline_version,
            "evidence_manifest_sha256": manifest_sha,
            "receipt_sha256": receipt_sha,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "provenance": {
                "minted_by": "runtime.validation.gate_runner",
                "attempt_dir": str(attempt_dir),
                "evidence_root": str(evidence_root),
                "manifest_path": str(manifest_path),
                "receipt_path": str(receipt_path),
            },
        }

        token_path = attempt_dir / "acceptance_token.json"
        write_acceptance_token(token_path, token_payload)
        return GateRunnerOutcome(
            success=True,
            gate="postflight",
            code="OK",
            classification="TERMINAL",
            next_action="NONE",
            token_path=token_path,
        )
````

### `runtime/validation/reporting.py`

````python
"""Deterministic reporting and atomic JSON writes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Mapping


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = canonical_json(payload)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def write_validator_report(report_path: Path, report_payload: Dict[str, Any]) -> None:
    if report_payload.get("pass") is not False:
        raise ValueError("validator_report.json must have pass=false")
    write_json_atomic(report_path, report_payload)


def write_acceptance_token(token_path: Path, token_payload: Dict[str, Any]) -> None:
    if token_payload.get("pass") is not True:
        raise ValueError("acceptance_token.json must have pass=true")
    if "token_sha256" in token_payload:
        raise ValueError("acceptance_token.json must not contain token_sha256")
    write_json_atomic(token_path, token_payload)
````

