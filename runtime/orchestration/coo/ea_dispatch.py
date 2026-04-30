"""COO to Codex EA GitHub dispatch helpers for v0 control-plane verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.orchestration.coo.review_gate import build_review_packet, evaluate_review_gate
from runtime.receipts.ea_receipt import validate_ea_receipt

DISPATCH_REQUEST_SCHEMA_VERSION = "coo_ea_dispatch_request.v0"
DISPATCH_RESULT_SCHEMA_VERSION = "coo_ea_result.v0"
CODEX_EXECUTOR = "codex"
CODEX_LAUNCH_PLAN_SCHEMA_VERSION = "codex_ea_launch_plan.v0"
RECOVERY_DATA_SCHEMA_VERSION = "coo_ea_recovery_data.v0"

TASK_TYPES = {"build", "fix", "hotfix", "spike", "stewardship"}
RESULT_STATUSES = {"succeeded", "failed", "blocked", "needs_decision"}
CI_STATUSES = {"success", "failure", "cancelled", "skipped", None}
ACTIVE_ISSUE_STATES = {"dispatched", "running"}
TERMINAL_ISSUE_STATES = {"succeeded", "failed", "blocked", "needs_decision", "timed_out"}

REQUIRED_EVIDENCE = ("ea_receipt.v0", "pull_request", "ci_latest_head")
GITHUB_COMPLETION_TRUTH = ("github_issue", "github_pull_request", "github_ci", "ea_receipt.v0")
EXCLUDED_COMPLETION_TRUTH = ("openclaw", "telegram", "local_tui")

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ISSUE_URL_RE = re.compile(
    r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(?P<issue>\d+)$"
)
_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/(?P<pr>\d+)$"
)
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")

_DISPATCH_REQUIRED_FIELDS = (
    "schema_version",
    "repo",
    "issue_number",
    "issue_url",
    "command_id",
    "attempt_id",
    "task_ref",
    "task_type",
    "executor",
    "base_ref",
    "branch_name",
    "scope_paths",
    "acceptance_criteria",
    "verification_commands",
    "required_evidence",
    "approval_ref",
    "auto_dispatch_basis",
    "timeout_seconds",
    "created_at",
)

_RESULT_REQUIRED_FIELDS = (
    "schema_version",
    "repo",
    "issue_number",
    "attempt_id",
    "executor",
    "status",
    "summary",
    "receipt",
    "pr_url",
    "head_sha",
    "ci_url",
    "ci_status",
    "evidence_urls",
    "blockers",
    "created_at",
)

_PERMISSION_MARKERS = (
    "permission",
    "credential",
    "credentials",
    "token",
    "github 403",
    "http 403",
    "branch protection",
    "protected branch",
)


class COOEADispatchValidationError(ValueError):
    """Raised when a COO EA dispatch payload fails v0 validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("Invalid COO EA dispatch payload:\n" + "\n".join(errors))


@dataclass(frozen=True)
class CodexLaunchStep:
    """One deterministic command in the Codex EA launch plan."""

    name: str
    argv: tuple[str, ...]
    cwd: str | None = None
    writes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "writes": list(self.writes),
        }


@dataclass(frozen=True)
class CodexLaunchPlan:
    """Writable clone/worktree branch command plan. It is never executed here."""

    schema_version: str
    executor: str
    repo: str
    issue_number: int
    attempt_id: str
    base_ref: str
    branch_name: str
    clone_dir: str
    worktree_dir: str
    writable: bool
    dry_run_only: bool
    commands: tuple[CodexLaunchStep, ...]
    completion_truth: tuple[str, ...] = GITHUB_COMPLETION_TRUTH
    excluded_completion_truth: tuple[str, ...] = EXCLUDED_COMPLETION_TRUTH

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "executor": self.executor,
            "repo": self.repo,
            "issue_number": self.issue_number,
            "attempt_id": self.attempt_id,
            "base_ref": self.base_ref,
            "branch_name": self.branch_name,
            "clone_dir": self.clone_dir,
            "worktree_dir": self.worktree_dir,
            "writable": self.writable,
            "dry_run_only": self.dry_run_only,
            "commands": [command.to_dict() for command in self.commands],
            "completion_truth": list(self.completion_truth),
            "excluded_completion_truth": list(self.excluded_completion_truth),
        }


@dataclass(frozen=True)
class GitHubDispatchEvidence:
    """GitHub issue/PR/CI and branch facts observed by the COO verifier."""

    issue_state: str = "running"
    pr_url: str | None = None
    pr_base_ref: str | None = None
    pr_head_sha: str | None = None
    ci_url: str | None = None
    ci_status: str | None = None
    worktree_clean: bool | None = None
    partial_commit_markers: tuple[str, ...] = ()
    wrapper_exit_code: int | None = None
    timed_out: bool = False
    terminal_state: str | None = None
    issue_artifact_urls: tuple[str, ...] = ()
    pr_artifact_urls: tuple[str, ...] = ()
    receipt_artifact_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptEvaluation:
    """Fail-closed COO verifier decision for one dispatch attempt."""

    state: str
    success: bool
    reason: str
    blockers: tuple[str, ...]
    result_valid: bool
    recovery_data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "success": self.success,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "result_valid": self.result_valid,
            "recovery_data": self.recovery_data,
        }


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp for dispatch payload creation."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_dispatch_request(
    *,
    repo: str,
    issue_number: int,
    command_id: str,
    attempt_id: str,
    task_ref: str,
    task_type: str,
    base_ref: str,
    branch_name: str,
    scope_paths: list[str],
    acceptance_criteria: list[str],
    verification_commands: list[str],
    approval_ref: str | None = None,
    auto_dispatch_basis: dict[str, Any] | None = None,
    timeout_seconds: int = 3600,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build and validate a minimal Codex-only dispatch request."""
    request = {
        "schema_version": DISPATCH_REQUEST_SCHEMA_VERSION,
        "repo": repo,
        "issue_number": issue_number,
        "issue_url": f"https://github.com/{repo}/issues/{issue_number}",
        "command_id": command_id,
        "attempt_id": attempt_id,
        "task_ref": task_ref,
        "task_type": task_type,
        "executor": CODEX_EXECUTOR,
        "base_ref": base_ref,
        "branch_name": branch_name,
        "scope_paths": list(scope_paths),
        "acceptance_criteria": list(acceptance_criteria),
        "verification_commands": list(verification_commands),
        "required_evidence": list(REQUIRED_EVIDENCE),
        "approval_ref": approval_ref,
        "auto_dispatch_basis": (
            dict(auto_dispatch_basis) if auto_dispatch_basis is not None else None
        ),
        "timeout_seconds": timeout_seconds,
        "created_at": created_at or utc_now_iso(),
    }
    assert_valid_dispatch_request(request)
    return request


def validate_dispatch_request(request: Any) -> list[str]:
    """Return validation errors for coo_ea_dispatch_request.v0."""
    if not isinstance(request, dict):
        return ["dispatch request must be a JSON object"]

    errors: list[str] = []
    _validate_required_fields(request, _DISPATCH_REQUIRED_FIELDS, errors)
    if errors:
        return errors

    if request["schema_version"] != DISPATCH_REQUEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {DISPATCH_REQUEST_SCHEMA_VERSION}")

    repo = request["repo"]
    if not _is_non_empty_string(repo) or not _REPO_RE.match(repo):
        errors.append("repo must be owner/name")

    issue_number = request["issue_number"]
    if not _is_positive_int(issue_number):
        errors.append("issue_number must be a positive integer")

    issue_url = request["issue_url"]
    if not isinstance(issue_url, str):
        errors.append("issue_url must be a string")
    else:
        match = _ISSUE_URL_RE.match(issue_url)
        if not match:
            errors.append("issue_url must be a GitHub issue URL")
        else:
            if repo == match.group("repo") and issue_number == int(match.group("issue")):
                pass
            elif _REPO_RE.match(str(repo)) and _is_positive_int(issue_number):
                errors.append("issue_url must match repo and issue_number")

    for field in ("command_id", "attempt_id", "task_ref", "base_ref", "branch_name"):
        if not _is_non_empty_string(request[field]):
            errors.append(f"{field} must be a non-empty string")

    for field in ("base_ref", "branch_name"):
        value = request[field]
        if isinstance(value, str) and not _SAFE_REF_RE.match(value):
            errors.append(f"{field} must contain only git ref-safe characters")

    if request["task_type"] not in TASK_TYPES:
        errors.append("task_type must be one of: build, fix, hotfix, spike, stewardship")

    if request["executor"] != CODEX_EXECUTOR:
        errors.append("executor must be codex")

    for field in (
        "scope_paths",
        "acceptance_criteria",
        "verification_commands",
        "required_evidence",
    ):
        _validate_string_list(request[field], field, errors, require_non_empty=True)

    required_evidence = request["required_evidence"]
    if isinstance(required_evidence, list):
        missing = [item for item in REQUIRED_EVIDENCE if item not in required_evidence]
        if missing:
            errors.append(f"required_evidence missing: {', '.join(missing)}")

    approval_ref = request["approval_ref"]
    if approval_ref is not None and not _is_non_empty_string(approval_ref):
        errors.append("approval_ref must be a non-empty string or null")

    auto_dispatch_basis = request["auto_dispatch_basis"]
    if auto_dispatch_basis is not None and not isinstance(auto_dispatch_basis, dict):
        errors.append("auto_dispatch_basis must be an object or null")
    if approval_ref is None and auto_dispatch_basis is None:
        errors.append("auto_dispatch_basis is required when approval_ref is null")

    if not _is_positive_int(request["timeout_seconds"]):
        errors.append("timeout_seconds must be a positive integer")

    _validate_utc_timestamp(request["created_at"], "created_at", errors)
    return errors


def assert_valid_dispatch_request(request: Any) -> None:
    """Raise when dispatch request validation fails."""
    errors = validate_dispatch_request(request)
    if errors:
        raise COOEADispatchValidationError(errors)


def validate_result_payload(result: Any) -> list[str]:
    """Return validation errors for coo_ea_result.v0 and embedded ea_receipt.v0."""
    if not isinstance(result, dict):
        return ["result must be a JSON object"]

    errors: list[str] = []
    _validate_required_fields(result, _RESULT_REQUIRED_FIELDS, errors)
    if errors:
        return errors

    if result["schema_version"] != DISPATCH_RESULT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {DISPATCH_RESULT_SCHEMA_VERSION}")

    repo = result["repo"]
    if not _is_non_empty_string(repo) or not _REPO_RE.match(repo):
        errors.append("repo must be owner/name")

    if not _is_positive_int(result["issue_number"]):
        errors.append("issue_number must be a positive integer")

    if not _is_non_empty_string(result["attempt_id"]):
        errors.append("attempt_id must be a non-empty string")

    if result["executor"] != CODEX_EXECUTOR:
        errors.append("executor must be codex")

    if result["status"] not in RESULT_STATUSES:
        errors.append("status must be one of: blocked, failed, needs_decision, succeeded")

    if not _is_non_empty_string(result["summary"]):
        errors.append("summary must be a non-empty string")

    receipt = result["receipt"]
    if not isinstance(receipt, dict):
        errors.append("receipt must be an ea_receipt.v0 object")
    else:
        for receipt_error in validate_ea_receipt(receipt):
            errors.append(f"receipt: {receipt_error}")

    _validate_nullable_string(result["pr_url"], "pr_url", errors)
    if isinstance(result["pr_url"], str) and result["pr_url"]:
        match = _PR_URL_RE.match(result["pr_url"])
        if not match:
            errors.append("pr_url must be a GitHub pull request URL or null")
        elif _REPO_RE.match(str(repo)) and match.group("repo") != repo:
            errors.append("pr_url must match repo")

    _validate_nullable_string(result["head_sha"], "head_sha", errors)
    if (
        isinstance(result["head_sha"], str)
        and result["head_sha"]
        and not _SHA_RE.match(result["head_sha"])
    ):
        errors.append("head_sha must be a 40-character git SHA or null")

    _validate_nullable_string(result["ci_url"], "ci_url", errors)
    if result["ci_status"] not in CI_STATUSES:
        errors.append("ci_status must be one of: success, failure, cancelled, skipped, null")

    _validate_string_list(result["evidence_urls"], "evidence_urls", errors)
    _validate_string_list(result["blockers"], "blockers", errors)
    if (
        result["status"] == "succeeded"
        and isinstance(result["blockers"], list)
        and result["blockers"]
    ):
        errors.append("succeeded status requires empty blockers")
    if (
        result["status"] != "succeeded"
        and isinstance(result["blockers"], list)
        and not result["blockers"]
    ):
        errors.append("non-succeeded status requires non-empty blockers")

    _validate_utc_timestamp(result["created_at"], "created_at", errors)
    return errors


def assert_valid_result_payload(result: Any) -> None:
    """Raise when result payload validation fails."""
    errors = validate_result_payload(result)
    if errors:
        raise COOEADispatchValidationError(errors)


def build_codex_launch_plan(
    request: dict[str, Any],
    *,
    workspace_root: str | Path,
) -> CodexLaunchPlan:
    """Represent, but do not execute, the Codex clone/worktree launch plan."""
    assert_valid_dispatch_request(request)
    root = Path(workspace_root)
    repo_slug = _safe_slug(str(request["repo"]))
    branch_slug = _safe_slug(str(request["branch_name"]))
    clone_dir = root / "clones" / repo_slug
    worktree_dir = root / "worktrees" / f"{branch_slug}-{request['attempt_id']}"
    prompt = (
        f"Execute GitHub issue {request['issue_url']} for attempt {request['attempt_id']}; "
        "post coo_ea_result.v0 with embedded ea_receipt.v0 to GitHub issue."
    )

    commands = (
        CodexLaunchStep(
            name="clone_repo",
            argv=(
                "git",
                "clone",
                f"https://github.com/{request['repo']}.git",
                str(clone_dir),
            ),
            writes=(str(clone_dir),),
        ),
        CodexLaunchStep(
            name="fetch_base_ref",
            argv=("git", "fetch", "origin", str(request["base_ref"])),
            cwd=str(clone_dir),
        ),
        CodexLaunchStep(
            name="create_writable_worktree",
            argv=(
                "git",
                "worktree",
                "add",
                "-B",
                str(request["branch_name"]),
                str(worktree_dir),
                f"origin/{request['base_ref']}",
            ),
            cwd=str(clone_dir),
            writes=(str(worktree_dir),),
        ),
        CodexLaunchStep(
            name="run_codex_ea",
            argv=("codex", "exec", "--cd", str(worktree_dir), prompt),
            cwd=str(worktree_dir),
            writes=tuple(str(path) for path in request["scope_paths"]),
        ),
    )
    return CodexLaunchPlan(
        schema_version=CODEX_LAUNCH_PLAN_SCHEMA_VERSION,
        executor=CODEX_EXECUTOR,
        repo=str(request["repo"]),
        issue_number=int(request["issue_number"]),
        attempt_id=str(request["attempt_id"]),
        base_ref=str(request["base_ref"]),
        branch_name=str(request["branch_name"]),
        clone_dir=str(clone_dir),
        worktree_dir=str(worktree_dir),
        writable=True,
        dry_run_only=True,
        commands=commands,
    )


def evaluate_attempt_result(
    request: dict[str, Any],
    result: dict[str, Any] | None,
    *,
    evidence: GitHubDispatchEvidence | None = None,
) -> AttemptEvaluation:
    """Evaluate one dispatch attempt and fail closed unless all success predicates pass."""
    evidence = evidence or GitHubDispatchEvidence()
    request_errors = validate_dispatch_request(request)
    if request_errors:
        return _evaluation(
            state="needs_decision",
            success=False,
            reason="invalid_dispatch_request",
            blockers=tuple(request_errors),
            result_valid=False,
            request=request,
            result=result,
            evidence=evidence,
        )

    if result is not None and (
        evidence.terminal_state in TERMINAL_ISSUE_STATES
        or evidence.issue_state in TERMINAL_ISSUE_STATES
    ):
        return _evaluation(
            state="late_result",
            success=False,
            reason="late_result",
            blockers=("result arrived after terminal state",),
            result_valid=False,
            request=request,
            result=result,
            evidence=evidence,
        )

    if result is None:
        return _evaluate_missing_result(request, evidence)

    result_errors = validate_result_payload(result)
    if result_errors:
        reason = _malformed_result_reason(result_errors)
        return _evaluation(
            state="needs_decision",
            success=False,
            reason=reason,
            blockers=tuple(result_errors),
            result_valid=False,
            request=request,
            result=result,
            evidence=evidence,
        )

    correlation_errors = _correlation_errors(request, result)
    if correlation_errors:
        return _evaluation(
            state="needs_decision",
            success=False,
            reason="result_correlation_mismatch",
            blockers=tuple(correlation_errors),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    receipt = result["receipt"]
    result_blockers = tuple(result["blockers"])
    receipt_blockers = tuple(receipt["blockers"])
    all_blockers = result_blockers + receipt_blockers

    if _has_permission_blocker(result, receipt):
        return _evaluation(
            state="blocked",
            success=False,
            reason="permission_denial",
            blockers=all_blockers or ("permission denied",),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if _is_ambiguous(result, receipt):
        return _evaluation(
            state="needs_decision",
            success=False,
            reason="ambiguous_result",
            blockers=all_blockers or ("result status conflicts with receipt",),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if evidence.partial_commit_markers:
        return _evaluation(
            state="needs_decision",
            success=False,
            reason="partial_commit_state",
            blockers=evidence.partial_commit_markers,
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if evidence.worktree_clean is False:
        return _evaluation(
            state="failed",
            success=False,
            reason="dirty_worktree",
            blockers=("worktree is dirty after EA run",),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if result["status"] == "blocked":
        return _evaluation(
            state="blocked",
            success=False,
            reason="ea_blocked",
            blockers=all_blockers,
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if result["status"] == "needs_decision":
        return _evaluation(
            state="needs_decision",
            success=False,
            reason="ea_needs_decision",
            blockers=all_blockers,
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if receipt["status"] == "failure" or any(code != 0 for code in receipt["inner_exit_codes"]):
        return _evaluation(
            state="failed",
            success=False,
            reason="inner_failure",
            blockers=all_blockers or ("receipt reports inner command failure",),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    if result["status"] == "failed":
        return _evaluation(
            state="failed",
            success=False,
            reason="ea_failed",
            blockers=all_blockers,
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    success_errors = _success_predicate_errors(request, result, evidence)
    if success_errors:
        state = "failed" if _has_hard_failure(success_errors) else "needs_decision"
        reason = "success_predicate_failed" if state == "failed" else "success_evidence_incomplete"
        return _evaluation(
            state=state,
            success=False,
            reason=reason,
            blockers=tuple(success_errors),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    review_gate = evaluate_review_gate(result, request=request)
    if not review_gate["ok"]:
        return _evaluation(
            state=str(review_gate["state"]),
            success=False,
            reason=str(review_gate["reason"]),
            blockers=tuple(str(blocker) for blocker in review_gate["blockers"]),
            result_valid=True,
            request=request,
            result=result,
            evidence=evidence,
        )

    return _evaluation(
        state="succeeded",
        success=True,
        reason="all_success_predicates_satisfied",
        blockers=(),
        result_valid=True,
        request=request,
        result=result,
        evidence=evidence,
    )


def build_github_recovery_data(
    request: dict[str, Any],
    result: dict[str, Any] | None,
    evidence: GitHubDispatchEvidence,
) -> dict[str, Any]:
    """Build recovery data from GitHub issue/PR/CI and receipt fields only."""
    result = result if isinstance(result, dict) else {}
    receipt = result.get("receipt") if isinstance(result.get("receipt"), dict) else {}
    evidence_urls = tuple(result.get("evidence_urls") or ())
    review_packet: dict[str, Any] | None = None
    if result.get("review_result") is not None or result.get("review_not_required") is not None:
        try:
            review_packet = build_review_packet(request, result)
        except ValueError as exc:
            review_packet = {"error": str(exc)}
    return {
        "schema_version": RECOVERY_DATA_SCHEMA_VERSION,
        "control_plane": "github",
        "completion_truth": list(GITHUB_COMPLETION_TRUTH),
        "excluded_completion_truth": list(EXCLUDED_COMPLETION_TRUTH),
        "issue": {
            "repo": request.get("repo"),
            "issue_number": request.get("issue_number"),
            "issue_url": request.get("issue_url"),
            "issue_state": evidence.issue_state,
            "artifact_urls": list(evidence.issue_artifact_urls),
        },
        "dispatch": {
            "attempt_id": request.get("attempt_id"),
            "command_id": request.get("command_id"),
            "executor": request.get("executor"),
            "base_ref": request.get("base_ref"),
            "branch_name": request.get("branch_name"),
            "timeout_seconds": request.get("timeout_seconds"),
        },
        "pull_request": {
            "pr_url": result.get("pr_url") or evidence.pr_url,
            "base_ref": evidence.pr_base_ref,
            "head_sha": result.get("head_sha") or evidence.pr_head_sha,
            "ci_url": result.get("ci_url") or evidence.ci_url,
            "ci_status": result.get("ci_status") or evidence.ci_status,
            "artifact_urls": list(evidence.pr_artifact_urls),
        },
        "receipt": {
            "status": receipt.get("status"),
            "inner_exit_codes": list(receipt.get("inner_exit_codes") or []),
            "files_changed": list(receipt.get("files_changed") or []),
            "tests_run": list(receipt.get("tests_run") or []),
            "blockers": list(receipt.get("blockers") or []),
            "artifact_urls": list(evidence.receipt_artifact_urls),
        },
        "result": {
            "schema_version": result.get("schema_version"),
            "status": result.get("status"),
            "created_at": result.get("created_at"),
            "summary": result.get("summary"),
            "evidence_urls": list(evidence_urls),
        },
        "review": {
            "review_packet": review_packet,
            "review_result": result.get("review_result"),
            "review_not_required": result.get("review_not_required"),
        },
        "recovery_policy": {
            "retry_requires_ceo_approval_v0": True,
            "completion_truth_excludes_openclaw_telegram_tui": True,
        },
    }


def _evaluate_missing_result(
    request: dict[str, Any],
    evidence: GitHubDispatchEvidence,
) -> AttemptEvaluation:
    if evidence.timed_out:
        return _evaluation(
            state="timed_out",
            success=False,
            reason="worker_timeout",
            blockers=("no valid coo_ea_result.v0 before timeout",),
            result_valid=False,
            request=request,
            result=None,
            evidence=evidence,
        )
    if evidence.wrapper_exit_code == 0:
        active_state = (
            evidence.issue_state if evidence.issue_state in ACTIVE_ISSUE_STATES else "running"
        )
        return _evaluation(
            state=active_state,
            success=False,
            reason="wrapper_exit_zero_transport_only",
            blockers=("wrapper exit 0 is transport-only; no valid result observed",),
            result_valid=False,
            request=request,
            result=None,
            evidence=evidence,
        )
    if evidence.wrapper_exit_code is not None and evidence.wrapper_exit_code != 0:
        return _evaluation(
            state="failed",
            success=False,
            reason="wrapper_transport_failure",
            blockers=(f"wrapper exited {evidence.wrapper_exit_code}",),
            result_valid=False,
            request=request,
            result=None,
            evidence=evidence,
        )
    return _evaluation(
        state=evidence.issue_state if evidence.issue_state in ACTIVE_ISSUE_STATES else "running",
        success=False,
        reason="awaiting_result",
        blockers=("no coo_ea_result.v0 observed",),
        result_valid=False,
        request=request,
        result=None,
        evidence=evidence,
    )


def _evaluation(
    *,
    state: str,
    success: bool,
    reason: str,
    blockers: tuple[str, ...],
    result_valid: bool,
    request: dict[str, Any],
    result: dict[str, Any] | None,
    evidence: GitHubDispatchEvidence,
) -> AttemptEvaluation:
    return AttemptEvaluation(
        state=state,
        success=success,
        reason=reason,
        blockers=blockers,
        result_valid=result_valid,
        recovery_data=build_github_recovery_data(request, result, evidence),
    )


def _validate_required_fields(
    payload: dict[str, Any],
    fields: tuple[str, ...],
    errors: list[str],
) -> None:
    for field in fields:
        if field not in payload:
            errors.append(f"missing required field: {field}")


def _validate_string_list(
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


def _validate_nullable_string(value: Any, field: str, errors: list[str]) -> None:
    if value is not None and not isinstance(value, str):
        errors.append(f"{field} must be a string or null")


def _validate_utc_timestamp(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field} must be an ISO-8601 UTC timestamp")
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 UTC timestamp")
        return
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        errors.append(f"{field} must include UTC timezone")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "dispatch"


def _malformed_result_reason(errors: list[str]) -> str:
    if any(error == "missing required field: receipt" for error in errors):
        return "missing_receipt"
    if any(error.startswith("receipt") for error in errors):
        return "malformed_receipt"
    return "malformed_result_payload"


def _correlation_errors(request: dict[str, Any], result: dict[str, Any]) -> list[str]:
    checks = (
        ("repo", request["repo"], result["repo"]),
        ("issue_number", request["issue_number"], result["issue_number"]),
        ("attempt_id", request["attempt_id"], result["attempt_id"]),
        ("executor", request["executor"], result["executor"]),
    )
    return [
        f"{field} mismatch: expected {expected!r}, got {actual!r}"
        for field, expected, actual in checks
        if expected != actual
    ]


def _has_permission_blocker(result: dict[str, Any], receipt: dict[str, Any]) -> bool:
    text = " ".join(
        str(item)
        for item in (
            [result.get("summary", "")]
            + list(result.get("blockers") or [])
            + list(receipt.get("blockers") or [])
        )
    ).lower()
    return any(marker in text for marker in _PERMISSION_MARKERS)


def _is_ambiguous(result: dict[str, Any], receipt: dict[str, Any]) -> bool:
    if result["status"] == "succeeded" and receipt["status"] != "success":
        return True
    if result["status"] == "succeeded" and (result["blockers"] or receipt["blockers"]):
        return True
    if (
        result["status"] != "succeeded"
        and receipt["status"] == "success"
        and not result["blockers"]
    ):
        return True
    return False


def _success_predicate_errors(
    request: dict[str, Any],
    result: dict[str, Any],
    evidence: GitHubDispatchEvidence,
) -> list[str]:
    errors: list[str] = []
    if evidence.issue_state not in ACTIVE_ISSUE_STATES:
        errors.append("github issue state must be dispatched or running")

    if not result["pr_url"]:
        errors.append("missing PR URL")
    elif evidence.pr_url is not None and evidence.pr_url != result["pr_url"]:
        errors.append("PR URL does not match GitHub evidence")

    if not result["head_sha"]:
        errors.append("missing PR head SHA")
    elif evidence.pr_head_sha is not None and evidence.pr_head_sha != result["head_sha"]:
        errors.append("PR head SHA does not match GitHub evidence")

    if evidence.pr_base_ref is None:
        errors.append("missing PR base ref evidence")
    elif evidence.pr_base_ref != request["base_ref"]:
        errors.append("PR base ref does not match dispatch base_ref")

    if not result["ci_url"]:
        errors.append("missing CI URL")
    elif evidence.ci_url is not None and evidence.ci_url != result["ci_url"]:
        errors.append("CI URL does not match GitHub evidence")

    result_ci = result["ci_status"]
    evidence_ci = evidence.ci_status if evidence.ci_status is not None else result_ci
    if result_ci != "success":
        errors.append(f"CI status is not success: {result_ci}")
    if evidence_ci != "success":
        errors.append(f"GitHub latest-head CI status is not success: {evidence_ci}")

    if evidence.worktree_clean is None:
        errors.append("missing clean worktree evidence")
    elif evidence.worktree_clean is False:
        errors.append("dirty worktree evidence")

    return errors


def _has_hard_failure(errors: list[str]) -> bool:
    return any(
        "CI status is not success" in error
        or "latest-head CI status is not success" in error
        or "dirty worktree" in error
        for error in errors
    )
