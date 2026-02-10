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
