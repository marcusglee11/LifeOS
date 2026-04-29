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
) -> dict[str, object]:
    return {
        "schema_version": "ea_receipt.v0",
        "status": status,
        "commands_run": ["pytest runtime/tests/orchestration/coo/test_ea_dispatch.py -q"],
        "inner_exit_codes": inner_exit_codes if inner_exit_codes is not None else [0],
        "files_changed": ["runtime/orchestration/coo/ea_dispatch.py"],
        "tests_run": ["runtime/tests/orchestration/coo/test_ea_dispatch.py"],
        "blockers": blockers if blockers is not None else [],
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
) -> dict[str, object]:
    if blockers is None:
        blockers = [] if status == "succeeded" else ["EA reported non-success"]
    return {
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
