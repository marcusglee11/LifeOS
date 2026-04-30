"""Tests for COO to Codex EA GitHub dispatch v0 helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.orchestration.coo.ea_dispatch import (
    EXCLUDED_COMPLETION_TRUTH,
    GitHubDispatchEvidence,
    build_codex_launch_plan,
    build_dispatch_request,
    evaluate_attempt_result,
    utc_now_iso,
    validate_dispatch_request,
)
from runtime.orchestration.coo.review_gate import (
    REVIEW_NOT_REQUIRED_SCHEMA_VERSION,
    REVIEW_RESULT_SCHEMA_VERSION,
    build_review_packet,
    classify_review_requirement,
    evaluate_review_gate,
    validate_review_packet,
)

_REPO = "marcusglee11/LifeOS"
_ISSUE_NUMBER = 79
_ATTEMPT_ID = "ATT-issue-79-001"
_HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"
_PR_URL = "https://github.com/marcusglee11/LifeOS/pull/123"
_CI_URL = "https://github.com/marcusglee11/LifeOS/actions/runs/123456789"


def _auto_dispatch_basis() -> dict[str, object]:
    return {
        "requires_approval": False,
        "risk": "low",
        "protected_paths": "excluded",
        "scope_overlap": "none",
        "decision_support_required": False,
    }


def _request() -> dict[str, object]:
    return build_dispatch_request(
        repo=_REPO,
        issue_number=_ISSUE_NUMBER,
        command_id="CMD-issue-79-001",
        attempt_id=_ATTEMPT_ID,
        task_ref="WI-2026-079",
        task_type="build",
        base_ref="main",
        branch_name="build/coo-ea-dispatch-first-slice-79",
        scope_paths=["runtime/orchestration/coo/", "runtime/tests/orchestration/coo/"],
        acceptance_criteria=[
            "coo_ea_result.v0 embeds valid ea_receipt.v0",
            "success requires PR URL, head SHA, and CI success",
        ],
        verification_commands=[
            "pytest runtime/tests/orchestration/coo/test_ea_dispatch.py -q",
            "pytest runtime/tests/receipts/test_ea_receipt.py -q",
        ],
        auto_dispatch_basis=_auto_dispatch_basis(),
        timeout_seconds=3600,
        created_at=utc_now_iso(),
    )


def _receipt(
    *,
    status: str = "success",
    inner_exit_codes: list[int] | None = None,
    blockers: list[str] | None = None,
    files_changed: list[str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "ea_receipt.v0",
        "status": status,
        "commands_run": ["pytest runtime/tests/orchestration/coo/test_ea_dispatch.py -q"],
        "inner_exit_codes": inner_exit_codes if inner_exit_codes is not None else [0],
        "files_changed": files_changed
        if files_changed is not None
        else ["runtime/orchestration/coo/ea_dispatch.py"],
        "tests_run": ["runtime/tests/orchestration/coo/test_ea_dispatch.py"],
        "blockers": blockers if blockers is not None else [],
    }


def _review_result(
    *,
    status: str = "passed",
    issues_found: list[str] | None = None,
    fixes_applied: list[str] | None = None,
    verification: list[str] | None = None,
    remaining_risks: list[str] | None = None,
    risk_disposition: str = "none",
) -> dict[str, object]:
    return {
        "schema_version": REVIEW_RESULT_SCHEMA_VERSION,
        "status": status,
        "reviewer_identity": "fresh-context-reviewer",
        "reviewer_session": "review-session-001",
        "issues_found": issues_found if issues_found is not None else [],
        "fixes_applied": fixes_applied if fixes_applied is not None else [],
        "verification": verification
        if verification is not None
        else ["pytest runtime/tests/orchestration/coo/test_ea_dispatch.py -q"],
        "remaining_risks": remaining_risks if remaining_risks is not None else [],
        "risk_disposition": risk_disposition,
        "created_at": utc_now_iso(),
    }


def _review_not_required(
    reason: str = "artifact-only typo fix; no code or governance surface touched",
) -> dict[str, object]:
    return {
        "schema_version": REVIEW_NOT_REQUIRED_SCHEMA_VERSION,
        "classification": "trivial",
        "reason": reason,
    }


def _result(
    *,
    status: str = "succeeded",
    receipt: dict[str, object] | None = None,
    blockers: list[str] | None = None,
    pr_url: str | None = _PR_URL,
    head_sha: str | None = _HEAD_SHA,
    ci_url: str | None = _CI_URL,
    ci_status: str | None = "success",
    attempt_id: str = _ATTEMPT_ID,
    executor: str = "codex",
    review_result: dict[str, object] | None = None,
    review_not_required: dict[str, object] | None = None,
    include_review: bool = True,
) -> dict[str, object]:
    if blockers is None:
        blockers = [] if status == "succeeded" else ["EA reported non-success"]
    payload: dict[str, object] = {
        "schema_version": "coo_ea_result.v0",
        "repo": _REPO,
        "issue_number": _ISSUE_NUMBER,
        "attempt_id": attempt_id,
        "executor": executor,
        "status": status,
        "summary": "Codex EA posted structured result.",
        "receipt": receipt if receipt is not None else _receipt(),
        "pr_url": pr_url,
        "head_sha": head_sha,
        "ci_url": ci_url,
        "ci_status": ci_status,
        "evidence_urls": [_PR_URL, _CI_URL],
        "blockers": blockers,
        "created_at": utc_now_iso(),
    }
    if include_review:
        payload["review_result"] = review_result if review_result is not None else _review_result()
    if review_not_required is not None:
        payload["review_not_required"] = review_not_required
    return payload


def _success_evidence(**overrides: object) -> GitHubDispatchEvidence:
    defaults: dict[str, object] = {
        "issue_state": "running",
        "pr_url": _PR_URL,
        "pr_base_ref": "main",
        "pr_head_sha": _HEAD_SHA,
        "ci_url": _CI_URL,
        "ci_status": "success",
        "worktree_clean": True,
        "issue_artifact_urls": ("https://github.com/marcusglee11/LifeOS/issues/79",),
        "pr_artifact_urls": (_PR_URL,),
        "receipt_artifact_urls": (_CI_URL,),
    }
    defaults.update(overrides)
    return GitHubDispatchEvidence(**defaults)


def test_success_requires_receipt_pr_ci() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(),
        evidence=_success_evidence(),
    )

    assert evaluation.success is True
    assert evaluation.state == "succeeded"
    assert evaluation.blockers == ()
    assert evaluation.recovery_data["control_plane"] == "github"
    assert set(evaluation.recovery_data["excluded_completion_truth"]) == set(
        EXCLUDED_COMPLETION_TRUTH
    )


def test_inner_failure_blocks_success() -> None:
    result = _result(
        status="failed",
        receipt=_receipt(
            status="failure",
            inner_exit_codes=[0, 2],
            blockers=["targeted test failed"],
        ),
        blockers=["targeted test failed"],
    )

    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "failed"
    assert evaluation.reason == "inner_failure"


def test_missing_receipt_fails_closed() -> None:
    result = _result()
    del result["receipt"]

    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "missing_receipt"


def test_malformed_receipt_fails_closed() -> None:
    result = _result(receipt={"schema_version": "ea_receipt.v0"})

    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "malformed_receipt"
    assert any("receipt:" in blocker for blocker in evaluation.blockers)


def test_worker_timeout_moves_to_timed_out() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        None,
        evidence=GitHubDispatchEvidence(issue_state="running", timed_out=True),
    )

    assert evaluation.success is False
    assert evaluation.state == "timed_out"
    assert evaluation.reason == "worker_timeout"


def test_permission_denial_blocks_retry() -> None:
    result = _result(
        status="blocked",
        receipt=_receipt(
            status="failure",
            inner_exit_codes=[1],
            blockers=["GitHub 403 token denied branch write"],
        ),
        blockers=["permission denied"],
    )

    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "blocked"
    assert evaluation.reason == "permission_denial"


def test_ci_failure_rejects_success() -> None:
    result = _result(ci_status="failure")

    evaluation = evaluate_attempt_result(
        _request(),
        result,
        evidence=_success_evidence(ci_status="failure"),
    )

    assert evaluation.success is False
    assert evaluation.state == "failed"
    assert evaluation.reason == "success_predicate_failed"


def test_dirty_worktree_rejects_success() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(),
        evidence=_success_evidence(worktree_clean=False),
    )

    assert evaluation.success is False
    assert evaluation.state == "failed"
    assert evaluation.reason == "dirty_worktree"


def test_partial_commit_state_needs_decision() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(),
        evidence=_success_evidence(partial_commit_markers=("branch advanced without PR",)),
    )

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "partial_commit_state"


def test_wrapper_exit_zero_is_transport_only() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        None,
        evidence=GitHubDispatchEvidence(issue_state="running", wrapper_exit_code=0),
    )

    assert evaluation.success is False
    assert evaluation.state == "running"
    assert evaluation.reason == "wrapper_exit_zero_transport_only"


def test_ambiguous_result_fails_closed() -> None:
    result = _result(
        status="succeeded",
        receipt=_receipt(
            status="failure",
            inner_exit_codes=[1],
            blockers=["receipt says failure"],
        ),
    )

    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "ambiguous_result"


def test_late_result_not_applied() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(),
        evidence=_success_evidence(terminal_state="timed_out"),
    )

    assert evaluation.success is False
    assert evaluation.state == "late_result"
    assert evaluation.reason == "late_result"


@pytest.mark.parametrize(
    "result",
    [
        _result(attempt_id="ATT-wrong"),
        _result(executor="openclaw"),
    ],
)
def test_wrong_executor_or_attempt_fails_closed(result: dict[str, object]) -> None:
    evaluation = evaluate_attempt_result(_request(), result, evidence=_success_evidence())

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"


def test_dispatch_request_validation_and_launch_plan(tmp_path: Path) -> None:
    request = _request()
    assert validate_dispatch_request(request) == []

    missing_evidence = dict(request)
    missing_evidence["required_evidence"] = ["ea_receipt.v0"]
    assert "required_evidence missing: pull_request, ci_latest_head" in validate_dispatch_request(
        missing_evidence
    )

    wrong_executor = dict(request)
    wrong_executor["executor"] = "openclaw"
    assert "executor must be codex" in validate_dispatch_request(wrong_executor)

    plan = build_codex_launch_plan(request, workspace_root=tmp_path).to_dict()
    assert plan["dry_run_only"] is True
    assert plan["writable"] is True
    assert plan["executor"] == "codex"
    assert plan["excluded_completion_truth"] == list(EXCLUDED_COMPLETION_TRUTH)
    assert any(command["argv"][:3] == ["git", "worktree", "add"] for command in plan["commands"])
    assert any(command["argv"][:2] == ["codex", "exec"] for command in plan["commands"])


def test_review_required_classifier_flags_runtime_and_governance_paths() -> None:
    runtime_decision = classify_review_requirement(["runtime/orchestration/coo/ea_dispatch.py"])
    docs_decision = classify_review_requirement(["docs/02_protocols/example.md"])

    assert runtime_decision["review_required"] is True
    assert docs_decision["review_required"] is True


def test_review_required_classifier_allows_artifacts_but_fails_unknown_scope() -> None:
    artifact_decision = classify_review_requirement(["artifacts/evidence/typo-fix.json"])
    unknown_decision = classify_review_requirement([])

    assert artifact_decision["review_required"] is False
    assert artifact_decision["reason"] == "trivial_or_artifact_only"
    assert unknown_decision["review_required"] is True
    assert unknown_decision["reason"] == "unknown_changed_files"


def test_review_required_work_cannot_close_without_review_result() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(include_review=False),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "missing_fresh_review"


def test_review_requirement_uses_request_scope_when_receipt_underreports_files() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(receipt=_receipt(files_changed=[]), include_review=False),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "unknown_changed_files"


def test_passed_review_cannot_close_when_receipt_underreports_files() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(receipt=_receipt(files_changed=[]), review_result=_review_result(status="passed")),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.state == "needs_decision"
    assert evaluation.reason == "unknown_changed_files"


def test_artifact_scope_passed_review_cannot_close_without_changed_file_evidence() -> None:
    request = _request()
    request["scope_paths"] = ["artifacts/evidence/"]
    decision = evaluate_review_gate(
        _result(receipt=_receipt(files_changed=[]), review_result=_review_result(status="passed")),
        request=request,
    )

    assert decision["ok"] is False
    assert decision["state"] == "needs_decision"
    assert decision["reason"] == "unknown_changed_files"


def test_unknown_change_evidence_cannot_be_marked_trivial_to_skip_review() -> None:
    decision = evaluate_review_gate(
        _result(
            receipt=_receipt(files_changed=[]),
            include_review=False,
            review_not_required=_review_not_required(),
        )
    )

    assert decision["ok"] is False
    assert decision["state"] == "needs_decision"
    assert decision["reason"] == "unknown_changed_files"


def test_review_required_work_cannot_be_marked_trivial_to_skip_review() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(include_review=False, review_not_required=_review_not_required()),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.reason == "fresh_review_required_not_skippable"


def test_valid_passed_review_allows_closure_and_records_review_packet() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(review_result=_review_result(status="passed")),
        evidence=_success_evidence(),
    )

    assert evaluation.success is True
    assert evaluation.reason == "all_success_predicates_satisfied"
    assert evaluation.recovery_data["review"]["review_result"]["status"] == "passed"
    assert (
        evaluation.recovery_data["review"]["review_packet"]["schema_version"]
        == "fresh_context_review_packet.v0"
    )
    assert evaluation.recovery_data["review"]["review_packet"]["diff"]["files_touched"] == [
        "runtime/orchestration/coo/ea_dispatch.py"
    ]
    assert (
        "scope_path:runtime/orchestration/coo/"
        in evaluation.recovery_data["review"]["review_packet"]["constraints"]
    )


def test_fixes_requested_returns_to_review_instead_of_closing() -> None:
    evaluation = evaluate_attempt_result(
        _request(),
        _result(
            review_result=_review_result(
                status="fixes_requested",
                issues_found=["closure evidence omits changed-file proof"],
            )
        ),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.state == "running"
    assert evaluation.reason == "fresh_review_fixes_requested"


def test_blocked_or_malformed_review_blocks_closure() -> None:
    blocked = evaluate_attempt_result(
        _request(),
        _result(
            review_result=_review_result(
                status="blocked",
                remaining_risks=["reviewer could not verify CI evidence"],
            )
        ),
        evidence=_success_evidence(),
    )
    malformed = evaluate_attempt_result(
        _request(),
        _result(review_result={"schema_version": REVIEW_RESULT_SCHEMA_VERSION}),
        evidence=_success_evidence(),
    )

    assert blocked.success is False
    assert blocked.state == "blocked"
    assert blocked.reason == "fresh_review_blocked"
    assert malformed.success is False
    assert malformed.reason == "malformed_review_result"


def test_trivial_review_skip_requires_explicit_reason() -> None:
    request = _request()
    request["scope_paths"] = ["artifacts/evidence/"]
    trivial_receipt = _receipt(files_changed=["artifacts/evidence/typo-fix.json"])
    evaluation = evaluate_attempt_result(
        request,
        _result(
            receipt=trivial_receipt,
            include_review=False,
            review_not_required=_review_not_required(),
        ),
        evidence=_success_evidence(),
    )

    assert evaluation.success is True
    assert evaluation.recovery_data["review"]["review_not_required"]["reason"]


def test_malformed_review_not_required_blocks_trivial_skip() -> None:
    request = _request()
    request["scope_paths"] = ["artifacts/evidence/"]
    trivial_receipt = _receipt(files_changed=["artifacts/evidence/typo-fix.json"])
    evaluation = evaluate_attempt_result(
        request,
        _result(
            receipt=trivial_receipt,
            include_review=False,
            review_not_required={
                "schema_version": REVIEW_NOT_REQUIRED_SCHEMA_VERSION,
                "classification": "trivial",
            },
        ),
        evidence=_success_evidence(),
    )

    assert evaluation.success is False
    assert evaluation.reason == "malformed_review_not_required"


def test_review_packet_validator_rejects_malformed_nested_shape() -> None:
    packet = build_review_packet(
        _request(),
        _result(),
        constraints=["blockers only"],
    )
    packet["diff"] = {"files_touched": "runtime/orchestration/coo/ea_dispatch.py"}

    assert "diff.scope_paths must be a list of strings" in validate_review_packet(packet)
    assert "diff.files_touched must be a list of strings" in validate_review_packet(packet)

    packet = build_review_packet(_request(), _result())
    packet["issue"]["issue_number"] = True
    assert "issue.issue_number must be an integer" in validate_review_packet(packet)


def test_review_packet_shape_includes_objective_diff_tests_and_constraints() -> None:
    packet = build_review_packet(
        _request(),
        _result(),
        constraints=["blockers only", "do not redesign"],
    )

    assert packet["original_objective"]["task_ref"] == "WI-2026-079"
    assert packet["issue"]["issue_url"] == "https://github.com/marcusglee11/LifeOS/issues/79"
    assert packet["diff"]["files_touched"] == ["runtime/orchestration/coo/ea_dispatch.py"]
    assert packet["tests_and_evidence"]["ci_status"] == "success"
    assert packet["constraints"] == ["blockers only", "do not redesign"]
