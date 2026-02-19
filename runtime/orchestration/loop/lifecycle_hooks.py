"""Lifecycle hooks for Loop Spine governance gates.

Pre-run hooks: All must pass or execution is BLOCKED (fail-closed).
Post-run hooks: Failures downgrade PASS to BLOCKED.

Each hook is a callable returning HookResult. Hooks are composed into
sequences that run all hooks and collect results (no short-circuit).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class HookResult:
    """Result of a single lifecycle hook."""

    name: str
    passed: bool
    reason: str


@dataclass
class HookSequenceResult:
    """Aggregated result of running a hook sequence."""

    phase: str  # "pre_run" | "post_run"
    results: List[HookResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failed_hooks(self) -> List[HookResult]:
        return [r for r in self.results if not r.passed]


# ---------------------------------------------------------------------------
# Hook type alias
# ---------------------------------------------------------------------------
HookFn = Callable[..., HookResult]


# ---------------------------------------------------------------------------
# Pre-run hook implementations
# ---------------------------------------------------------------------------


def check_policy_hash_present(*, policy_hash: Optional[str], **_: Any) -> HookResult:
    """Fail-closed on missing policy hash."""
    if policy_hash:
        return HookResult(name="policy_hash_present", passed=True, reason="ok")
    return HookResult(
        name="policy_hash_present",
        passed=False,
        reason="policy_hash is missing or empty",
    )


def check_envelope_constraints(
    *,
    scope_paths: List[str],
    repo_root: Path,
    allowed_paths: List[str],
    denied_paths: List[str],
    **_: Any,
) -> HookResult:
    """Validate scope paths against EnvelopeEnforcer."""
    from runtime.api.governance_api import EnvelopeEnforcer

    if not scope_paths:
        return HookResult(name="envelope_constraints", passed=True, reason="no scope paths to validate")

    enforcer = EnvelopeEnforcer(repo_root)
    violations: List[str] = []
    for path_str in scope_paths:
        result = enforcer.validate_path_access(
            requested_path=path_str,
            operation="spine_scope_check",
            allowed_paths=allowed_paths,
            denied_paths=denied_paths,
        )
        if not result.allowed:
            violations.append(f"{path_str}: {result.reason}")

    if violations:
        return HookResult(
            name="envelope_constraints",
            passed=False,
            reason=f"envelope violations: {violations}",
        )
    return HookResult(name="envelope_constraints", passed=True, reason="ok")


def check_protected_paths(*, scope_paths: List[str], **_: Any) -> HookResult:
    """Check scope paths against protected paths registry."""
    from runtime.api.governance_api import is_path_protected

    if not scope_paths:
        return HookResult(name="protected_paths", passed=True, reason="no scope paths to validate")

    blocked: List[str] = []
    for path_str in scope_paths:
        is_protected, reason = is_path_protected(path_str)
        if is_protected:
            blocked.append(f"{path_str}: {reason}")

    if blocked:
        return HookResult(
            name="protected_paths",
            passed=False,
            reason=f"protected path violations: {blocked}",
        )
    return HookResult(name="protected_paths", passed=True, reason="ok")


# ---------------------------------------------------------------------------
# Post-run hook implementations
# ---------------------------------------------------------------------------


def check_terminal_packet_present(*, terminal_packet_path: Optional[Path], **_: Any) -> HookResult:
    """Terminal packet file must exist."""
    if terminal_packet_path is None:
        return HookResult(
            name="terminal_packet_present",
            passed=False,
            reason="terminal_packet_path not provided",
        )
    if Path(terminal_packet_path).exists():
        return HookResult(name="terminal_packet_present", passed=True, reason="ok")
    return HookResult(
        name="terminal_packet_present",
        passed=False,
        reason=f"terminal packet not found: {terminal_packet_path}",
    )


def check_ledger_append_success(*, ledger_write_ok: bool, **_: Any) -> HookResult:
    """Ledger write must have succeeded."""
    if ledger_write_ok:
        return HookResult(name="ledger_append_success", passed=True, reason="ok")
    return HookResult(
        name="ledger_append_success",
        passed=False,
        reason="ledger append failed",
    )


def check_evidence_completeness(
    *,
    evidence_dir: Optional[Path],
    evidence_tier: str = "light",
    **_: Any,
) -> HookResult:
    """Tier enforcement via enforce_evidence_tier (when evidence_dir provided)."""
    if evidence_dir is None:
        return HookResult(name="evidence_completeness", passed=True, reason="no evidence_dir, skipped")

    evidence_path = Path(evidence_dir)
    if not evidence_path.exists():
        return HookResult(
            name="evidence_completeness",
            passed=False,
            reason=f"evidence_dir does not exist: {evidence_dir}",
        )

    from runtime.validation.evidence import enforce_evidence_tier, EvidenceError

    try:
        enforce_evidence_tier(evidence_path, evidence_tier)
    except EvidenceError as exc:
        return HookResult(
            name="evidence_completeness",
            passed=False,
            reason=f"{exc.code}: {exc}",
        )
    return HookResult(name="evidence_completeness", passed=True, reason="ok")


# ---------------------------------------------------------------------------
# Sequence runners
# ---------------------------------------------------------------------------

# Default hook lists — callers can override for testing or customisation.
DEFAULT_PRE_RUN_HOOKS: List[HookFn] = [
    check_policy_hash_present,
    check_envelope_constraints,
    check_protected_paths,
]

DEFAULT_POST_RUN_HOOKS: List[HookFn] = [
    check_terminal_packet_present,
    check_ledger_append_success,
    check_evidence_completeness,
]


def run_hook_sequence(
    hooks: List[HookFn],
    phase: str,
    kwargs: Dict[str, Any],
) -> HookSequenceResult:
    """Run all hooks in *hooks*, collect results (no short-circuit)."""
    seq = HookSequenceResult(phase=phase)
    for hook_fn in hooks:
        try:
            result = hook_fn(**kwargs)
        except Exception as exc:
            result = HookResult(
                name=getattr(hook_fn, "__name__", "unknown"),
                passed=False,
                reason=f"hook raised: {type(exc).__name__}: {exc}",
            )
        seq.results.append(result)
    return seq


def run_pre_hooks(kwargs: Dict[str, Any], *, hooks: Optional[List[HookFn]] = None) -> HookSequenceResult:
    """Run pre-run governance hooks. Returns aggregated result."""
    return run_hook_sequence(hooks or DEFAULT_PRE_RUN_HOOKS, "pre_run", kwargs)


def run_post_hooks(kwargs: Dict[str, Any], *, hooks: Optional[List[HookFn]] = None) -> HookSequenceResult:
    """Run post-run governance hooks. Returns aggregated result."""
    return run_hook_sequence(hooks or DEFAULT_POST_RUN_HOOKS, "post_run", kwargs)
