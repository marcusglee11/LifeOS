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
