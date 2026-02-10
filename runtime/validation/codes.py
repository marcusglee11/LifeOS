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
