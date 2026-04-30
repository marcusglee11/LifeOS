"""Fresh-context review/fix closure gate for COO-managed EA work."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

REVIEW_PACKET_SCHEMA_VERSION = "fresh_context_review_packet.v0"
REVIEW_RESULT_SCHEMA_VERSION = "fresh_context_review_result.v0"
REVIEW_GATE_DECISION_SCHEMA_VERSION = "fresh_context_review_gate_decision.v0"
REVIEW_NOT_REQUIRED_SCHEMA_VERSION = "fresh_context_review_not_required.v0"

REVIEW_RESULT_STATUSES = {"passed", "fixes_requested", "blocked"}
REVIEW_REQUIRED_PREFIXES = (
    ".github/",
    "config/",
    "runtime/",
    "scripts/",
    "tests/",
    "docs/00_foundations/",
    "docs/01_governance/",
    "docs/02_protocols/",
    "docs/03_runtime/",
    "docs/11_admin/",
)
REVIEW_REQUIRED_MARKERS = (
    "auth",
    "closure",
    "credential",
    "cron",
    "dispatch",
    "receipt",
    "review",
    "secret",
    "security",
    "service",
    "token",
)

_REVIEW_PACKET_REQUIRED_FIELDS = (
    "schema_version",
    "original_objective",
    "issue",
    "work_item",
    "diff",
    "tests_and_evidence",
    "constraints",
    "review_instruction",
)
_REVIEW_RESULT_REQUIRED_FIELDS = (
    "schema_version",
    "status",
    "reviewer_identity",
    "reviewer_session",
    "issues_found",
    "fixes_applied",
    "verification",
    "remaining_risks",
    "risk_disposition",
    "created_at",
)


def normalize_review_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def classify_review_requirement(changed_paths: Sequence[str]) -> dict[str, Any]:
    """Classify whether a changed-path set requires fresh-context review."""
    normalized = []
    seen: set[str] = set()
    for raw_path in changed_paths:
        path = normalize_review_path(str(raw_path))
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(path)

    for path in normalized:
        if path.startswith(REVIEW_REQUIRED_PREFIXES):
            return {
                "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
                "review_required": True,
                "reason": f"review_required_path:{path}",
                "changed_paths": normalized,
            }
        lowered = path.lower()
        if any(marker in lowered for marker in REVIEW_REQUIRED_MARKERS):
            return {
                "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
                "review_required": True,
                "reason": f"review_required_marker:{path}",
                "changed_paths": normalized,
            }

    if normalized:
        return {
            "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
            "review_required": False,
            "reason": "trivial_or_artifact_only",
            "changed_paths": normalized,
        }
    return {
        "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
        "review_required": True,
        "reason": "unknown_changed_files",
        "changed_paths": normalized,
    }


def build_review_packet(
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    constraints: Sequence[str] | None = None,
    review_instruction: str = (
        "Fresh-context review: blockers only; verify acceptance and evidence; "
        "request fixes when needed."
    ),
) -> dict[str, Any]:
    """Build the deterministic review packet shape required before closure."""
    receipt = result.get("receipt") if isinstance(result.get("receipt"), dict) else {}
    packet_constraints = (
        list(constraints) if constraints is not None else _review_constraints_from_request(request)
    )
    packet = {
        "schema_version": REVIEW_PACKET_SCHEMA_VERSION,
        "original_objective": {
            "task_ref": request.get("task_ref"),
            "acceptance_criteria": list(request.get("acceptance_criteria") or []),
            "verification_commands": list(request.get("verification_commands") or []),
        },
        "issue": {
            "repo": request.get("repo"),
            "issue_number": request.get("issue_number"),
            "issue_url": request.get("issue_url"),
        },
        "work_item": {
            "command_id": request.get("command_id"),
            "attempt_id": request.get("attempt_id"),
            "executor": request.get("executor"),
        },
        "diff": {
            "scope_paths": list(request.get("scope_paths") or []),
            "files_touched": list(receipt.get("files_changed") or []),
            "pr_url": result.get("pr_url"),
            "head_sha": result.get("head_sha"),
        },
        "tests_and_evidence": {
            "commands_run": list(receipt.get("commands_run") or []),
            "tests_run": list(receipt.get("tests_run") or []),
            "ci_url": result.get("ci_url"),
            "ci_status": result.get("ci_status"),
            "evidence_urls": list(result.get("evidence_urls") or []),
        },
        "constraints": packet_constraints,
        "review_instruction": review_instruction,
    }
    errors = validate_review_packet(packet)
    if errors:
        raise ValueError("Invalid review packet: " + "; ".join(errors))
    return packet


def validate_review_packet(packet: Any) -> list[str]:
    if not isinstance(packet, dict):
        return ["review packet must be a JSON object"]
    errors: list[str] = []
    _require_fields(packet, _REVIEW_PACKET_REQUIRED_FIELDS, errors)
    if errors:
        return errors
    if packet["schema_version"] != REVIEW_PACKET_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REVIEW_PACKET_SCHEMA_VERSION}")
    if not isinstance(packet["original_objective"], dict):
        errors.append("original_objective must be an object")
    else:
        _non_empty_string(
            packet["original_objective"].get("task_ref"), "original_objective.task_ref", errors
        )
        _string_list(
            packet["original_objective"].get("acceptance_criteria"),
            "original_objective.acceptance_criteria",
            errors,
        )
        _string_list(
            packet["original_objective"].get("verification_commands"),
            "original_objective.verification_commands",
            errors,
        )
    if not isinstance(packet["issue"], dict):
        errors.append("issue must be an object")
    else:
        _non_empty_string(packet["issue"].get("repo"), "issue.repo", errors)
        issue_number = packet["issue"].get("issue_number")
        if not isinstance(issue_number, int) or isinstance(issue_number, bool):
            errors.append("issue.issue_number must be an integer")
        _non_empty_string(packet["issue"].get("issue_url"), "issue.issue_url", errors)
    if not isinstance(packet["work_item"], dict):
        errors.append("work_item must be an object")
    else:
        _non_empty_string(packet["work_item"].get("command_id"), "work_item.command_id", errors)
        _non_empty_string(packet["work_item"].get("attempt_id"), "work_item.attempt_id", errors)
        _non_empty_string(packet["work_item"].get("executor"), "work_item.executor", errors)
    if not isinstance(packet["diff"], dict):
        errors.append("diff must be an object")
    else:
        _string_list(packet["diff"].get("scope_paths"), "diff.scope_paths", errors)
        _string_list(packet["diff"].get("files_touched"), "diff.files_touched", errors)
        _optional_string(packet["diff"].get("pr_url"), "diff.pr_url", errors)
        _optional_string(packet["diff"].get("head_sha"), "diff.head_sha", errors)
    if not isinstance(packet["tests_and_evidence"], dict):
        errors.append("tests_and_evidence must be an object")
    else:
        _string_list(
            packet["tests_and_evidence"].get("commands_run"),
            "tests_and_evidence.commands_run",
            errors,
        )
        _string_list(
            packet["tests_and_evidence"].get("tests_run"),
            "tests_and_evidence.tests_run",
            errors,
        )
        _optional_string(
            packet["tests_and_evidence"].get("ci_url"), "tests_and_evidence.ci_url", errors
        )
        _optional_string(
            packet["tests_and_evidence"].get("ci_status"),
            "tests_and_evidence.ci_status",
            errors,
        )
        _string_list(
            packet["tests_and_evidence"].get("evidence_urls"),
            "tests_and_evidence.evidence_urls",
            errors,
        )
    _string_list(packet["constraints"], "constraints", errors)
    _non_empty_string(packet["review_instruction"], "review_instruction", errors)
    return errors


def validate_review_result(review_result: Any) -> list[str]:
    if not isinstance(review_result, dict):
        return ["review_result must be a JSON object"]
    errors: list[str] = []
    _require_fields(review_result, _REVIEW_RESULT_REQUIRED_FIELDS, errors)
    if errors:
        return errors
    if review_result["schema_version"] != REVIEW_RESULT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REVIEW_RESULT_SCHEMA_VERSION}")
    if review_result["status"] not in REVIEW_RESULT_STATUSES:
        errors.append("status must be one of: blocked, fixes_requested, passed")
    _non_empty_string(review_result["reviewer_identity"], "reviewer_identity", errors)
    _non_empty_string(review_result["reviewer_session"], "reviewer_session", errors)
    _string_list(review_result["issues_found"], "issues_found", errors)
    _string_list(review_result["fixes_applied"], "fixes_applied", errors)
    _string_list(review_result["verification"], "verification", errors, require_non_empty=True)
    _string_list(review_result["remaining_risks"], "remaining_risks", errors)
    _non_empty_string(review_result["risk_disposition"], "risk_disposition", errors)
    _utc_timestamp(review_result["created_at"], "created_at", errors)

    if review_result.get("status") == "fixes_requested" and not review_result.get("issues_found"):
        errors.append("fixes_requested status requires at least one issue_found")
    if review_result.get("status") == "blocked" and not (
        review_result.get("issues_found") or review_result.get("remaining_risks")
    ):
        errors.append("blocked status requires issues_found or remaining_risks")
    if (
        review_result.get("status") == "passed"
        and review_result.get("remaining_risks")
        and not str(review_result.get("risk_disposition", "")).strip()
    ):
        errors.append("passed review with remaining_risks requires risk_disposition")
    return errors


def validate_review_not_required(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["review_not_required must be a JSON object"]
    errors: list[str] = []
    if value.get("schema_version") != REVIEW_NOT_REQUIRED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REVIEW_NOT_REQUIRED_SCHEMA_VERSION}")
    if value.get("classification") != "trivial":
        errors.append("review_not_required classification must be trivial")
    _non_empty_string(value.get("reason"), "review_not_required.reason", errors)
    return errors


def evaluate_review_gate(
    result: dict[str, Any],
    *,
    request: dict[str, Any] | None = None,
    constraints: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Evaluate the fresh-review closure gate for a validated COO EA result."""
    receipt = result.get("receipt") if isinstance(result.get("receipt"), dict) else {}
    changed_files = receipt.get("files_changed") if isinstance(receipt, dict) else []
    if not isinstance(changed_files, list):
        changed_files = []
    scope_paths = request.get("scope_paths") if isinstance(request, dict) else []
    if not isinstance(scope_paths, list):
        scope_paths = []
    classification = classify_review_requirement(
        [str(path) for path in changed_files] + [str(path) for path in scope_paths]
    )
    review_result = result.get("review_result")
    review_not_required = result.get("review_not_required")
    review_packet: dict[str, Any] | None = None
    if request is not None and (
        classification["review_required"]
        or review_result is not None
        or review_not_required is not None
    ):
        try:
            review_packet = build_review_packet(request, result, constraints=constraints)
        except ValueError as exc:
            return _gate_block(
                state="needs_decision",
                reason="malformed_review_packet",
                blockers=(str(exc),),
                classification=classification,
            )

    if not changed_files:
        return _gate_block(
            state="needs_decision",
            reason="unknown_changed_files",
            blockers=(
                "closure needs receipt.files_changed evidence before review or "
                "review-not-required disposition can authorize closure",
            ),
            classification=classification,
        )

    if classification["review_required"]:
        if review_result is None:
            if review_not_required is not None:
                return _gate_block(
                    state="needs_decision",
                    reason="fresh_review_required_not_skippable",
                    blockers=(
                        "review_not_required cannot override review-required EA work "
                        "touching code/tests/runtime/config/docs/security/closure surfaces",
                    ),
                    classification=classification,
                )
            return _gate_block(
                state="needs_decision",
                reason="missing_fresh_review",
                blockers=("fresh-context review is required but review_result is absent",),
                classification=classification,
            )

    if review_result is not None:
        errors = validate_review_result(review_result)
        if errors:
            return _gate_block(
                state="needs_decision",
                reason="malformed_review_result",
                blockers=tuple(errors),
                classification=classification,
            )
        status = review_result["status"]
        if status == "fixes_requested":
            return _gate_block(
                state="running",
                reason="fresh_review_fixes_requested",
                blockers=tuple(review_result["issues_found"]),
                classification=classification,
            )
        if status == "blocked":
            return _gate_block(
                state="blocked",
                reason="fresh_review_blocked",
                blockers=tuple(review_result["issues_found"] or review_result["remaining_risks"]),
                classification=classification,
            )
        return _gate_ok(classification, review_result=review_result, review_packet=review_packet)

    if review_not_required is None:
        return _gate_block(
            state="needs_decision",
            reason="missing_review_disposition",
            blockers=(
                "closure evidence must include review_result or policy-supported "
                "review_not_required reason",
            ),
            classification=classification,
        )

    skip_errors = validate_review_not_required(review_not_required)
    if skip_errors:
        return _gate_block(
            state="needs_decision",
            reason="malformed_review_not_required",
            blockers=tuple(skip_errors),
            classification=classification,
        )
    return _gate_ok(
        classification,
        review_not_required=review_not_required,
        review_packet=review_packet,
    )


def _gate_ok(
    classification: dict[str, Any],
    *,
    review_result: dict[str, Any] | None = None,
    review_not_required: dict[str, Any] | None = None,
    review_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
        "ok": True,
        "state": "succeeded",
        "reason": "fresh_review_gate_satisfied",
        "blockers": [],
        "classification": classification,
        "review_result": review_result,
        "review_not_required": review_not_required,
        "review_packet": review_packet,
    }


def _gate_block(
    *,
    state: str,
    reason: str,
    blockers: Sequence[str],
    classification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_GATE_DECISION_SCHEMA_VERSION,
        "ok": False,
        "state": state,
        "reason": reason,
        "blockers": list(blockers),
        "classification": classification,
    }


def _review_constraints_from_request(request: dict[str, Any]) -> list[str]:
    constraints: list[str] = []
    executor = request.get("executor")
    if isinstance(executor, str) and executor.strip():
        constraints.append(f"executor:{executor}")
    base_ref = request.get("base_ref")
    if isinstance(base_ref, str) and base_ref.strip():
        constraints.append(f"base_ref:{base_ref}")
    branch_name = request.get("branch_name")
    if isinstance(branch_name, str) and branch_name.strip():
        constraints.append(f"branch_name:{branch_name}")
    scope_paths = request.get("scope_paths")
    if isinstance(scope_paths, list):
        constraints.extend(
            f"scope_path:{path}" for path in scope_paths if isinstance(path, str) and path
        )
    required_evidence = request.get("required_evidence")
    if isinstance(required_evidence, list):
        constraints.extend(
            f"required_evidence:{item}"
            for item in required_evidence
            if isinstance(item, str) and item
        )
    return constraints


def _require_fields(payload: dict[str, Any], fields: Sequence[str], errors: list[str]) -> None:
    for field in fields:
        if field not in payload:
            errors.append(f"missing required field: {field}")


def _non_empty_string(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")


def _optional_string(value: Any, field: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        errors.append(f"{field} must be a string when present")


def _string_list(
    value: Any,
    field: str,
    errors: list[str],
    *,
    require_non_empty: bool = False,
) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} must be a list of strings")
        return
    if require_non_empty and not value:
        errors.append(f"{field} must not be empty")


def _utc_timestamp(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{field} must be an ISO-8601 UTC timestamp ending in Z")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be a valid ISO-8601 UTC timestamp")
