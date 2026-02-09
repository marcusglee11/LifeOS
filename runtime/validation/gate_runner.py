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
