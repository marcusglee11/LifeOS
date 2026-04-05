"""
Per-lens dispatch with retry, waiver, and mandatory blocking for Council Runtime v2.

Implements spec sections 5, 9.4, and 9.5:
- Per-lens retries (configurable, default max 2)
- Waiver on exhausted retries for non-mandatory waivable lenses
- CouncilBlockedError for mandatory lens failures
- Coverage degradation tracking
- Results sorted deterministically by lens_name
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from .models import CouncilBlockedError

if TYPE_CHECKING:
    pass


@dataclass
class LensResult:
    """Outcome of executing and validating a single lens."""

    lens_name: str
    status: str  # "success", "waived", "blocked"
    model: str
    raw_output: dict | None
    normalized_output: dict | None
    retries_used: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    waived: bool = False


@dataclass
class LensDispatchResult:
    """Aggregate outcome of dispatching all required lenses."""

    lens_results: list[LensResult]  # sorted by lens_name
    coverage_degraded: bool
    waived_lenses: list[str]
    all_passed: bool
    blocked: bool
    block_reason: str | None = None


def dispatch_lenses(
    plan: Any,
    executor: Callable[[str, str, dict], dict],
    validator: Callable[[dict, str, str, str], Any],
    context: dict | None = None,
    max_retries: int = 2,
) -> LensDispatchResult:
    """
    Dispatch all required lenses in the plan, applying per-lens retry logic,
    schema validation, waiver, and mandatory-failure blocking.

    Args:
        plan: A CouncilRunPlan-compatible object with a .core attribute exposing
              required_lenses, model_assignments, mandatory_lenses, waivable_lenses,
              run_type, and tier.
        executor: Callable(lens_name, model, context) -> raw dict output.
        validator: Callable(raw, lens_name, run_type, tier) -> SchemaGateResult-like.
        context: Optional execution context dict passed to every executor call.
        max_retries: Maximum number of retry attempts per lens (default 2).

    Returns:
        LensDispatchResult with sorted lens_results, coverage_degraded, waived_lenses,
        all_passed, and blocked flags.

    Raises:
        CouncilBlockedError: If any mandatory lens fails after exhausting retries.
    """
    ctx = context or {}
    core = plan.core

    results: list[LensResult] = []
    waived_lenses: list[str] = []
    coverage_degraded = False

    for lens_name in core.required_lenses:
        model = core.model_assignments.get(lens_name, "")
        retries_used = 0
        errors: list[str] = []
        warnings: list[str] = []
        raw_output: dict | None = None
        normalized_output: dict | None = None
        succeeded = False

        attempt = 0
        while attempt <= max_retries:
            # Try to execute; treat executor exceptions as failures
            try:
                raw_output = executor(lens_name, model, ctx)
                exec_error: str | None = None
            except Exception as exc:
                exec_error = f"{type(exc).__name__}: {exc}"
                errors.append(exec_error)
                raw_output = None

            if exec_error is not None:
                # Executor raised; count this attempt, retry or exhaust
                if attempt < max_retries:
                    attempt += 1
                    retries_used = attempt
                    continue
                # Exhausted
                break

            # Validate the raw output
            gate = validator(raw_output, lens_name, core.run_type, core.tier)
            errors = list(gate.errors)
            warnings = list(gate.warnings)

            if gate.valid:
                normalized_output = gate.normalized_output
                succeeded = True
                break

            # Validation failed; track attempt
            if attempt < max_retries:
                attempt += 1
                retries_used = attempt
                continue
            # Exhausted retries
            break

        if succeeded:
            results.append(
                LensResult(
                    lens_name=lens_name,
                    status="success",
                    model=model,
                    raw_output=raw_output,
                    normalized_output=normalized_output,
                    retries_used=retries_used,
                    errors=errors,
                    warnings=warnings,
                    waived=False,
                )
            )
            continue

        # Failure after exhausting retries
        is_mandatory = lens_name in core.mandatory_lenses
        is_waivable = lens_name in core.waivable_lenses

        if is_mandatory:
            raise CouncilBlockedError(
                "LENS_MANDATORY_FAILURE",
                f"Mandatory lens ''{lens_name}''  failed after {retries_used} retries: {errors}",
            )

        if is_waivable:
            waived_lenses.append(lens_name)
            coverage_degraded = True
            results.append(
                LensResult(
                    lens_name=lens_name,
                    status="waived",
                    model=model,
                    raw_output=raw_output,
                    normalized_output=None,
                    retries_used=retries_used,
                    errors=errors,
                    warnings=warnings,
                    waived=True,
                )
            )
            continue

        # Non-waivable, non-mandatory but still failed -> block
        raise CouncilBlockedError(
            "LENS_MANDATORY_FAILURE",
            f"Lens ''{lens_name}''  failed after {retries_used} retries and is not waivable: {errors}",  # noqa: E501
        )

    # Sort results deterministically by lens_name
    results.sort(key=lambda lr: lr.lens_name)

    all_passed = all(lr.status == "success" for lr in results)

    return LensDispatchResult(
        lens_results=results,
        coverage_degraded=coverage_degraded,
        waived_lenses=waived_lenses,
        all_passed=all_passed,
        blocked=False,
        block_reason=None,
    )
