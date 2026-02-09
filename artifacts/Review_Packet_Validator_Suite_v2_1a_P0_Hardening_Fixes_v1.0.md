---
artifact_id: "68582951-e53b-4ddb-8900-50ed6f2484a1"
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-02-09T23:14:22.908067Z"
author: "OpenCode"
version: "1.0"
status: "PENDING_REVIEW"
chain_id: "validator-suite-v2.1a-p0"
mission_ref: "Validator Suite v2.1a P0 Hardening Fixes (Trust + Caps + Ignore Proof)"
tags: ["validator", "hardening", "trust", "retry-caps", "ignore-proof"]
terminal_outcome: "PASS"
closure_evidence: {"pytest":"artifacts/validation_samples/v2.1a-p0/pytest_output_p0_8.txt","tamper_fixture":"artifacts/validation_samples/v2.1a-p0/validator_report_job_spec_tampered.json"}
---

# Review_Packet_Validator_Suite_v2_1a_P0_Hardening_Fixes_v1.0

# Scope Envelope

- **Allowed Paths**: `runtime/validation/**`, `runtime/orchestration/orchestrator.py`, `runtime/tests/**`, `artifacts/validation_samples/**`
- **Forbidden Paths**: `docs/00_foundations/**`, `docs/01_governance/**`, main repo working tree
- **Authority**: AGENT INSTRUCTION BLOCK — Validator Suite v2.1a P0 Hardening Fixes

# Summary

Implemented P0.8 hardening fixes in the existing worktree: postflight now uses trusted in-memory JobSpec, orchestrator detects on-disk job_spec tampering and emits terminal `JOB_SPEC_TAMPERED`, retry cap checks now trip at cap boundary (`>=`), and ignore proof now validates run_root + attempt_dir + evidence_root. Added tests and tamper fixture; all targeted tests pass.

# Issue Catalogue

| Issue ID | Description | Resolution | Status |
|----------|-------------|------------|--------|
| P0.8.1 | JobSpec trust bypass via mutable on-disk reload in postflight | Pass trusted `JobSpec` object into pre/postflight; add orchestrator hash-based tamper detection + terminal `JOB_SPEC_TAMPERED` | FIXED |
| P0.8.2 | Retry cap off-by-one (`>` instead of `>=`) | Updated retry evaluation semantics to cap-boundary termination; added boundary test | FIXED |
| P0.8.3 | Ignore proof too narrow (evidence_root only) | Added output-root ignore verification for `run_root`, `attempt_dir`, `evidence_root`; added partial-ignore failure tests | FIXED |

# Acceptance Criteria

| ID | Criterion | Status | Evidence Pointer | SHA-256 |
|----|-----------|--------|------------------|---------|
| AC1 | Postflight does not trust on-disk job_spec | PASS | runtime/validation/gate_runner.py | 6d126f3069b60354def9924afb9fd9bb44f06fcdcc3ea41540d6633a7e5d8296 |
| AC2 | Tamper detection emits terminal JOB_SPEC_TAMPERED | PASS | runtime/orchestration/orchestrator.py | 19c4fc8db564cc3d5b371a14eea0ed2a180298dd7705a701e4e13dd255bf75da |
| AC3 | Retry caps enforce at cap boundary (>=) | PASS | runtime/validation/attempts.py | a477b3d2c06f7491ae7a4914dfedba16f520fe5adcf8928273f7fde2788d5267 |
| AC4 | Ignore proof covers run_root/attempt_dir/evidence_root | PASS | runtime/validation/cleanliness.py | a55ac149aacb867e48399b9bbe3c78698d940951f10532d4384de6b0ffce9e2c |
| AC5 | Updated test suite passes | PASS | artifacts/validation_samples/v2.1a-p0/pytest_output_p0_8.txt | 969d18191fa66ef3d5eb7361d8590b73d9110ca7de2fab43b029f303a2b53df8 |

# Closure Evidence Checklist

| Category | Requirement | Verified |
|----------|-------------|----------|
| Provenance | Changed file list and branch-local scope | `git status --porcelain=v1` in worktree shows only hardening files |
| Artifacts | JOB_SPEC_TAMPERED sample report provided | `artifacts/validation_samples/v2.1a-p0/validator_report_job_spec_tampered.json` |
| Repro | Updated pytest command and output captured | `artifacts/validation_samples/v2.1a-p0/pytest_output_p0_8.txt` |
| Governance | Packet and flattened appendix produced | `artifacts/Review_Packet_Validator_Suite_v2_1a_P0_Hardening_Fixes_v1.0.md` |
| Outcome | All requested hardening fixes implemented and tested | `PASS` |

# Non-Goals

- P1 receipt enforcement.
- P2 mid-run checkpoints/worktree parallelism.
- Keyed/HMAC trust model changes.

# Appendix

## File Manifest

- `artifacts/validation_samples/v2.1a-p0/pytest_output_p0_8.txt`
- `artifacts/validation_samples/v2.1a-p0/validator_report_job_spec_tampered.json`
- `runtime/orchestration/orchestrator.py`
- `runtime/tests/fixtures/validation/validator_report_job_spec_tampered_fixture.json`
- `runtime/tests/orchestration/test_validation_orchestrator.py`
- `runtime/tests/validation/test_cleanliness.py`
- `runtime/tests/validation/test_gate_runner_and_acceptor.py`
- `runtime/validation/attempts.py`
- `runtime/validation/cleanliness.py`
- `runtime/validation/codes.py`
- `runtime/validation/gate_runner.py`

## Flattened Code

### File: `artifacts/validation_samples/v2.1a-p0/pytest_output_p0_8.txt`

````text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /mnt/c/Users/cabra/Projects/lifeos-worktrees/validator-suite-v2.1a-p0
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 19 items

runtime/tests/validation/test_evidence.py ...                            [ 15%]
runtime/tests/validation/test_cleanliness.py ....                        [ 36%]
runtime/tests/orchestration/test_workspace_lock.py ...                   [ 52%]
runtime/tests/validation/test_gate_runner_and_acceptor.py ....           [ 73%]
runtime/tests/orchestration/test_validation_orchestrator.py .....        [100%]

============================== 19 passed in 2.58s ==============================
````

### File: `artifacts/validation_samples/v2.1a-p0/validator_report_job_spec_tampered.json`

````json
{
  "schema_version": "validator_report_v1",
  "pass": false,
  "gate": "postflight",
  "summary_code": "JOB_SPEC_TAMPERED",
  "exit_code": 93,
  "message": "job_spec.json tampered after preflight: expected_sha256=1111111111111111111111111111111111111111111111111111111111111111 actual_sha256=2222222222222222222222222222222222222222222222222222222222222222",
  "classification": "TERMINAL",
  "next_action": "HALT_SCHEMA_DRIFT",
  "checks": [
    {
      "name": "job_spec_integrity",
      "code": "JOB_SPEC_TAMPERED",
      "ok": false,
      "message": "job_spec.json tampered after preflight: expected_sha256=1111111111111111111111111111111111111111111111111111111111111111 actual_sha256=2222222222222222222222222222222222222222222222222222222222222222"
    }
  ],
  "attempt_context": {
    "run_id": "run-job-spec-tamper",
    "attempt_id": "attempt-0001",
    "attempt_index": 1,
    "max_attempts_per_gate_per_run": 2,
    "max_total_attempts_per_run": 3,
    "max_consecutive_same_failure_code": 2,
    "distinct_failure_codes_count": 0,
    "consecutive_same_failure_code": 0
  },
  "pointers": {
    "attempt_dir": "/tmp/attempt-0001",
    "run_root": "/tmp/run-job-spec-tamper",
    "job_spec_path": "/tmp/attempt-0001/job_spec.json",
    "job_spec_expected_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
    "job_spec_actual_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
    "evidence_root": "/tmp/attempt-0001/evidence",
    "manifest_path": "/tmp/attempt-0001/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0001/receipt.json"
  }
}
````

### File: `runtime/orchestration/orchestrator.py`

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
from runtime.validation.reporting import sha256_file, write_json_atomic, write_validator_report


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

    def _emit_terminal_report(
        self,
        *,
        attempt_dir: Path,
        attempt_context: AttemptContext,
        gate: str,
        code: str,
        check_name: str,
        message: str,
        pointers: Dict[str, Any] | None = None,
    ) -> Path:
        spec = get_code_spec(code)
        pointer_payload = pointers or {
            "attempt_dir": str(attempt_dir),
            "run_root": str(attempt_dir.parent),
            "evidence_root": str(attempt_dir / "evidence"),
            "manifest_path": str(attempt_dir / "evidence" / "evidence_manifest.json"),
            "receipt_path": str(attempt_dir / "receipt.json"),
        }
        report = ValidationReport(
            schema_version="validator_report_v1",
            passed=False,
            gate=gate,
            summary_code=code,
            exit_code=spec.exit_code,
            message=message,
            classification=spec.classification,
            next_action=spec.default_next_action,
            checks=[CheckResult(name=check_name, code=code, ok=False, message=message)],
            attempt_context=attempt_context,
            pointers=pointer_payload,
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
            report_path = self._emit_terminal_report(
                attempt_dir=attempt_dir,
                attempt_context=attempt_context,
                gate="preflight",
                code="CONCURRENT_RUN_DETECTED",
                check_name="workspace_lock",
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
                job_spec_path = attempt_dir / "job_spec.json"
                write_json_atomic(job_spec_path, job_spec.to_dict())
                expected_job_spec_sha = sha256_file(job_spec_path)

                attempt_context = self._build_attempt_context(job_spec, attempt_id, attempt_index, retry_state)

                preflight = self.gate_runner.run_preflight(
                    workspace_root=self.workspace_root,
                    attempt_dir=attempt_dir,
                    job_spec=job_spec,
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

                try:
                    actual_job_spec_sha = sha256_file(job_spec_path)
                except FileNotFoundError:
                    actual_job_spec_sha = "<missing>"
                if actual_job_spec_sha != expected_job_spec_sha:
                    tamper_message = (
                        "job_spec.json tampered after preflight: "
                        f"expected_sha256={expected_job_spec_sha} actual_sha256={actual_job_spec_sha}"
                    )
                    report_path = self._emit_terminal_report(
                        attempt_dir=attempt_dir,
                        attempt_context=attempt_context,
                        gate="postflight",
                        code="JOB_SPEC_TAMPERED",
                        check_name="job_spec_integrity",
                        message=tamper_message,
                        pointers={
                            "attempt_dir": str(attempt_dir),
                            "run_root": str(run_root),
                            "job_spec_path": str(job_spec_path),
                            "job_spec_expected_sha256": expected_job_spec_sha,
                            "job_spec_actual_sha256": actual_job_spec_sha,
                            "evidence_root": str(evidence_root),
                            "manifest_path": str(evidence_root / "evidence_manifest.json"),
                            "receipt_path": str(attempt_dir / "receipt.json"),
                        },
                    )
                    self._append_recovery_event(
                        run_root,
                        {
                            "attempt_id": attempt_id,
                            "attempt_index": attempt_index,
                            "gate": "postflight",
                            "code": "JOB_SPEC_TAMPERED",
                            "classification": "TERMINAL",
                            "next_action": "HALT_SCHEMA_DRIFT",
                            "terminal": True,
                        },
                    )
                    return OrchestrationResult(
                        success=False,
                        run_id=run_id,
                        attempt_id=attempt_id,
                        attempt_index=attempt_index,
                        message="Terminal failure: job_spec tampered",
                        validator_report_path=str(report_path),
                    )

                postflight = self.gate_runner.run_postflight(
                    workspace_root=self.workspace_root,
                    attempt_dir=attempt_dir,
                    job_spec=job_spec,
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

### File: `runtime/tests/fixtures/validation/validator_report_job_spec_tampered_fixture.json`

````json
{
  "schema_version": "validator_report_v1",
  "pass": false,
  "gate": "postflight",
  "summary_code": "JOB_SPEC_TAMPERED",
  "exit_code": 93,
  "message": "job_spec.json tampered after preflight: expected_sha256=1111111111111111111111111111111111111111111111111111111111111111 actual_sha256=2222222222222222222222222222222222222222222222222222222222222222",
  "classification": "TERMINAL",
  "next_action": "HALT_SCHEMA_DRIFT",
  "checks": [
    {
      "name": "job_spec_integrity",
      "code": "JOB_SPEC_TAMPERED",
      "ok": false,
      "message": "job_spec.json tampered after preflight: expected_sha256=1111111111111111111111111111111111111111111111111111111111111111 actual_sha256=2222222222222222222222222222222222222222222222222222222222222222"
    }
  ],
  "attempt_context": {
    "run_id": "run-job-spec-tamper",
    "attempt_id": "attempt-0001",
    "attempt_index": 1,
    "max_attempts_per_gate_per_run": 2,
    "max_total_attempts_per_run": 3,
    "max_consecutive_same_failure_code": 2,
    "distinct_failure_codes_count": 0,
    "consecutive_same_failure_code": 0
  },
  "pointers": {
    "attempt_dir": "/tmp/attempt-0001",
    "run_root": "/tmp/run-job-spec-tamper",
    "job_spec_path": "/tmp/attempt-0001/job_spec.json",
    "job_spec_expected_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
    "job_spec_actual_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
    "evidence_root": "/tmp/attempt-0001/evidence",
    "manifest_path": "/tmp/attempt-0001/evidence/evidence_manifest.json",
    "receipt_path": "/tmp/attempt-0001/receipt.json"
  }
}
````

### File: `runtime/tests/orchestration/test_validation_orchestrator.py`

````python
from __future__ import annotations

from pathlib import Path
import json
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


def test_orchestrator_detects_job_spec_tamper_as_terminal(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)

    def _tampering_agent(attempt_dir: Path, _job_spec: JobSpec) -> None:
        # Agent tries to downgrade tier by rewriting on-disk job_spec.
        job_spec_path = attempt_dir / "job_spec.json"
        payload = json.loads(job_spec_path.read_text(encoding="utf-8"))
        payload["evidence_tier"] = "light"
        job_spec_path.write_text(json.dumps(payload), encoding="utf-8")

        # Only light evidence emitted (would be insufficient for full).
        evidence_root = attempt_dir / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
        (evidence_root / "exitcode.txt").write_text("0\n", encoding="utf-8")
        (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
        compute_manifest(evidence_root)

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="full",
        agent_runner=_tampering_agent,
        run_id="run-job-spec-tamper",
        retry_caps=RetryCaps(2, 3, 2),
    )

    assert not result.success
    assert result.validator_report_path is not None

    report_payload = json.loads(Path(result.validator_report_path).read_text(encoding="utf-8"))
    assert report_payload["summary_code"] == "JOB_SPEC_TAMPERED"
    assert report_payload["classification"] == "TERMINAL"
    assert report_payload["pass"] is False


def test_retry_cap_boundary_stops_at_second_failure(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    calls = {"count": 0}

    def _always_failing_agent(attempt_dir: Path, _job_spec: JobSpec) -> None:
        calls["count"] += 1
        evidence_root = attempt_dir / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
        # Intentionally omit exitcode.txt so light tier fails every attempt.
        (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
        compute_manifest(evidence_root)

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_always_failing_agent,
        run_id="run-cap-boundary",
        retry_caps=RetryCaps(
            max_attempts_per_gate_per_run=2,
            max_total_attempts_per_run=5,
            max_consecutive_same_failure_code=5,
        ),
    )

    assert not result.success
    assert result.attempt_index == 2
    assert calls["count"] == 2
````

### File: `runtime/tests/validation/test_cleanliness.py`

````python
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from runtime.validation.cleanliness import (
    CleanlinessError,
    verify_evidence_root_ignored,
    verify_output_roots_ignored,
    verify_repo_clean,
)


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


def test_verify_output_roots_ignore_failure_when_only_evidence_is_ignored(tmp_path: Path) -> None:
    repo = tmp_path / "repo-partial-ignore"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    # Partial ignore: only the deepest evidence dir is ignored; run root remains unignored.
    (repo / ".gitignore").write_text("artifacts/validation_runs/*/*/evidence/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")

    run_root = repo / "artifacts" / "validation_runs" / "run-1"
    attempt_dir = run_root / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(CleanlinessError) as exc:
        verify_output_roots_ignored(repo, run_root, attempt_dir, evidence_root)

    assert exc.value.code == "EVIDENCE_ROOT_NOT_IGNORED"
````

### File: `runtime/tests/validation/test_gate_runner_and_acceptor.py`

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


def _setup_repo_with_ignore(tmp_path: Path, ignore_rule: str) -> Path:
    repo = tmp_path / "repo-custom-ignore"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".gitignore").write_text(ignore_rule, encoding="utf-8")
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
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
    )
    assert pre.success

    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        job_spec=_job_spec(),
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
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
    ).success
    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        job_spec=_job_spec(),
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
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
    ).success

    first = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not first.success
    assert first.report_path is not None
    first_bytes = first.report_path.read_bytes()

    second = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not second.success
    assert second.report_path is not None
    second_bytes = second.report_path.read_bytes()

    assert first_bytes == second_bytes


def test_preflight_fails_when_only_evidence_root_is_ignored(tmp_path: Path) -> None:
    repo = _setup_repo_with_ignore(tmp_path, "artifacts/validation_runs/*/*/evidence/\n")
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    (attempt_dir / "evidence").mkdir(parents=True, exist_ok=True)

    gate_runner = GateRunner()
    outcome = gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        job_spec=_job_spec(),
        attempt_context=_attempt_context(),
    )

    assert not outcome.success
    assert outcome.code == "EVIDENCE_ROOT_NOT_IGNORED"
    assert outcome.report_path is not None
````

### File: `runtime/validation/attempts.py`

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

    if state.attempts_total >= caps.max_total_attempts_per_run:
        return "max_total_attempts_exceeded"

    if state.attempts_by_gate.get(gate, 0) >= caps.max_attempts_per_gate_per_run:
        return f"max_attempts_per_gate_exceeded:{gate}"

    if state.consecutive_same_failure_code() >= caps.max_consecutive_same_failure_code:
        return "max_consecutive_same_failure_code_exceeded"

    if state.distinct_failure_codes() >= 3:
        return "distinct_failure_codes_threshold_reached"

    return None
````

### File: `runtime/validation/cleanliness.py`

````python
"""Git cleanliness and evidence ignore proof checks."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Dict


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


def _to_git_target(repo_root: Path, target_path: Path) -> str:
    try:
        return target_path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(target_path)


def _check_ignored(repo_root: Path, target_path: Path, code: str) -> str:
    target = _to_git_target(repo_root, target_path)
    result = _run_git(repo_root, ["check-ignore", "-v", target])
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    message = result.stderr.strip() if result.stderr.strip() else f"No ignore rule matched: {target}"
    raise CleanlinessError(code, message)


def verify_repo_clean(repo_root: Path, code: str) -> None:
    result = _run_git(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if result.returncode != 0:
        raise CleanlinessError(code, f"git status failed: {result.stderr.strip()}")
    output = result.stdout.strip()
    if output:
        raise CleanlinessError(code, f"Repository is dirty:\n{output}")


def verify_evidence_root_ignored(repo_root: Path, evidence_root: Path) -> str:
    return _check_ignored(repo_root, evidence_root, code="EVIDENCE_ROOT_NOT_IGNORED")


def verify_output_roots_ignored(
    repo_root: Path,
    run_root: Path,
    attempt_dir: Path,
    evidence_root: Path,
) -> Dict[str, str]:
    """
    Verify ignore coverage for all output roots.

    P0.8 hardening: proving ignore only for evidence_root is insufficient, because
    unignored attempt/run roots can still dirty the workspace.
    """
    return {
        "run_root": _check_ignored(repo_root, run_root, code="EVIDENCE_ROOT_NOT_IGNORED"),
        "attempt_dir": _check_ignored(repo_root, attempt_dir, code="EVIDENCE_ROOT_NOT_IGNORED"),
        "evidence_root": _check_ignored(repo_root, evidence_root, code="EVIDENCE_ROOT_NOT_IGNORED"),
    }
````

### File: `runtime/validation/codes.py`

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
    "JOB_SPEC_TAMPERED": CodeSpec(
        code="JOB_SPEC_TAMPERED",
        exit_code=93,
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

### File: `runtime/validation/gate_runner.py`

````python
"""Trusted Gate Runner for validator suite v2.1a."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.validation.cleanliness import CleanlinessError, verify_output_roots_ignored, verify_repo_clean
from runtime.validation.codes import get_code_spec
from runtime.validation.core import AttemptContext, CheckResult, JobSpec, ValidationReport
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

    def run_preflight(
        self,
        *,
        workspace_root: Path,
        attempt_dir: Path,
        job_spec: JobSpec,
        attempt_context: AttemptContext,
    ) -> GateRunnerOutcome:
        _ = job_spec  # Trusted in-memory source of policy; reserved for future checks.
        run_root = attempt_dir.parent
        evidence_root = attempt_dir / "evidence"
        pointers = {
            "attempt_dir": str(attempt_dir),
            "run_root": str(run_root),
            "evidence_root": str(evidence_root),
            "manifest_path": str(evidence_root / "evidence_manifest.json"),
            "receipt_path": str(attempt_dir / "receipt.json"),
        }

        try:
            verify_repo_clean(workspace_root, code="DIRTY_REPO_PRE")
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
            proofs = verify_output_roots_ignored(workspace_root, run_root, attempt_dir, evidence_root)
            pointers["ignore_proof"] = proofs
        except CleanlinessError as exc:
            return self._report_failure(
                attempt_dir=attempt_dir,
                gate="preflight",
                code=exc.code,
                message=str(exc),
                attempt_context=attempt_context,
                checks=[CheckResult(name="output_roots_ignore", code=exc.code, ok=False, message=str(exc))],
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
        job_spec: JobSpec,
        attempt_context: AttemptContext,
        receipt_required: bool = False,
    ) -> GateRunnerOutcome:
        evidence_root = attempt_dir / "evidence"
        manifest_path = evidence_root / "evidence_manifest.json"
        receipt_path = attempt_dir / "receipt.json"

        pointers = {
            "attempt_dir": str(attempt_dir),
            "run_root": str(attempt_dir.parent),
            "evidence_root": str(evidence_root),
            "manifest_path": str(manifest_path),
            "receipt_path": str(receipt_path),
        }

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
