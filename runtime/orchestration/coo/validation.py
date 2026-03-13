"""Behavioral validation helpers for COO outputs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_BANNED_PROMISE_PATTERNS = (
    re.compile(r"\bi(?: am|'m)\s+on it\b", re.IGNORECASE),
    re.compile(r"\bworking on it\b", re.IGNORECASE),
    re.compile(r"\bi(?: will|'ll)\s+report back\b", re.IGNORECASE),
    re.compile(r"\bi(?: will|'ll)\s+check back\b", re.IGNORECASE),
    re.compile(r"\bi(?: will|'ll)\s+monitor\b", re.IGNORECASE),
    re.compile(r"\bi(?: will|'ll)\s+update you\b", re.IGNORECASE),
    re.compile(r"\bi(?: will|'ll)\s+follow up\b", re.IGNORECASE),
)
_DEFLECTION_PATTERNS = (
    re.compile(r"\bwhere would you like me to look\b", re.IGNORECASE),
    re.compile(r"\bwhere should i look\b", re.IGNORECASE),
    re.compile(r"\bwhat would you like me to check\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class BehavioralViolation:
    code: str
    message: str
    severity: str = "error"


@dataclass
class BehavioralValidationResult:
    mode: str
    violations: list[BehavioralViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.violations


def _context_blockers(context: dict[str, Any]) -> list[dict[str, Any]]:
    execution_truth = context.get("execution_truth")
    if not isinstance(execution_truth, dict):
        return []
    blockers = execution_truth.get("blockers")
    if isinstance(blockers, list):
        return [item for item in blockers if isinstance(item, dict)]
    return []


def _mentions_blocker(text: str, blockers: list[dict[str, Any]]) -> bool:
    lowered = text.lower()
    if "blocked" in lowered or "escalat" in lowered or "defer" in lowered:
        return True

    for blocker in blockers:
        reason = str(blocker.get("reason", "")).strip().lower()
        run_id = str(blocker.get("run_id", "")).strip().lower()
        if reason and reason in lowered:
            return True
        if run_id and run_id in lowered:
            return True
    return False


def validate_coo_response(
    text: str,
    *,
    mode: str,
    context: dict[str, Any],
) -> BehavioralValidationResult:
    """Validate COO raw output against the narrowed behavioral contract."""
    violations: list[BehavioralViolation] = []

    for pattern in _BANNED_PROMISE_PATTERNS:
        if pattern.search(text):
            violations.append(
                BehavioralViolation(
                    code="false_callback_promise",
                    message="response promises unsupported future follow-up behavior",
                )
            )
            break

    if context.get("canonical_state_present"):
        for pattern in _DEFLECTION_PATTERNS:
            if pattern.search(text):
                violations.append(
                    BehavioralViolation(
                        code="governed_query_deflection",
                        message="response deflects a governed query despite canonical state being available",
                    )
                )
                break

    blockers = _context_blockers(context)
    if blockers and mode in {"propose", "direct"} and not _mentions_blocker(text, blockers):
        violations.append(
            BehavioralViolation(
                code="ignored_blocker_truth",
                message="response does not surface available execution blockers",
            )
        )

    return BehavioralValidationResult(mode=mode, violations=violations)
