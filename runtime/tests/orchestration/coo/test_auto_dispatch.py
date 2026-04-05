"""Tests for COO auto-dispatch eligibility predicates."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from runtime.orchestration.coo.auto_dispatch import (
    check_scope_overlap_with_in_progress,
    is_auto_dispatchable,
    is_fully_auto_dispatchable,
)
from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION, TaskEntry
from runtime.orchestration.coo.commands import cmd_coo_propose

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_task(
    task_id: str,
    *,
    status: str = "pending",
    risk: str = "low",
    requires_approval: bool = False,
    decision_support_required: bool = False,
    task_type: str = "build",
    scope_paths: list[str] | None = None,
) -> TaskEntry:
    return TaskEntry(
        id=task_id,
        title=f"Task {task_id}",
        description="",
        dod="",
        priority="P1",
        risk=risk,
        scope_paths=scope_paths or ["runtime/orchestration/coo/"],
        status=status,
        requires_approval=requires_approval,
        owner="codex",
        evidence="",
        task_type=task_type,
        tags=[],
        objective_ref="bootstrap",
        created_at="2026-03-05T00:00:00Z",
        completed_at=None,
        decision_support_required=decision_support_required,
    )


_ENVELOPE = {
    "schema_version": "delegation_envelope.v1",
    "trust_tier": "burn-in",
    "protected_paths": ["docs/00_foundations/", "docs/01_governance/"],
    "autonomy": {
        "L0": {
            "actions": [
                "update_tracking_state",
                "auto_dispatch_eligible",
            ]
        }
    },
}


# ── is_auto_dispatchable ────────────────────────────────────────────────────


class TestIsAutoDispatchable:
    def test_eligible_low_risk_no_approval(self) -> None:
        task = _make_task("T-010", requires_approval=False, risk="low", status="pending")
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is True
        assert "all predicates pass" in reason

    def test_ineligible_requires_approval(self) -> None:
        task = _make_task("T-010", requires_approval=True)
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "requires_approval" in reason

    def test_ineligible_risk_med(self) -> None:
        task = _make_task("T-010", risk="med")
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "med" in reason

    def test_ineligible_risk_high(self) -> None:
        task = _make_task("T-010", risk="high")
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "high" in reason

    def test_ineligible_not_pending(self) -> None:
        task = _make_task("T-010", status="in_progress")
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "pending" in reason

    def test_ineligible_protected_path(self) -> None:
        task = _make_task(
            "T-010",
            scope_paths=["docs/00_foundations/architecture.md"],
        )
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "protected" in reason.lower()

    def test_eligible_no_protected_path_overlap(self) -> None:
        task = _make_task(
            "T-010",
            scope_paths=["runtime/orchestration/coo/"],
        )
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is True

    def test_ineligible_protected_path_trailing_slash_mismatch(self) -> None:
        """scope_path without trailing slash must still be caught if it matches protected."""
        # Protected path has trailing slash; scope_path does not
        task = _make_task(
            "T-010",
            scope_paths=["docs/00_foundations"],  # no trailing slash
        )
        eligible, reason = is_auto_dispatchable(task, _ENVELOPE)
        assert eligible is False
        assert "protected" in reason.lower()

    def test_ineligible_scope_overlap_trailing_slash_mismatch(self) -> None:
        """Scope overlap detection must not be bypassed by trailing-slash differences."""
        candidate = _make_task(
            "T-010",
            scope_paths=["runtime/orchestration/coo"],  # no trailing slash
        )
        in_progress = _make_task(
            "T-011",
            status="in_progress",
            scope_paths=["runtime/orchestration/"],  # with trailing slash
        )
        eligible, reason = check_scope_overlap_with_in_progress(candidate, [candidate, in_progress])
        assert eligible is False


# ── check_scope_overlap_with_in_progress ─────────────────────────────────────


class TestScopeOverlap:
    def test_ineligible_scope_overlap_in_progress(self) -> None:
        candidate = _make_task(
            "T-010",
            scope_paths=["runtime/orchestration/coo/"],
        )
        in_progress = _make_task(
            "T-011",
            status="in_progress",
            scope_paths=["runtime/orchestration/"],
        )
        all_tasks = [candidate, in_progress]
        eligible, reason = check_scope_overlap_with_in_progress(candidate, all_tasks)
        assert eligible is False
        assert "T-011" in reason
        assert "overlap" in reason

    def test_eligible_no_scope_overlap(self) -> None:
        candidate = _make_task(
            "T-010",
            scope_paths=["runtime/orchestration/coo/"],
        )
        in_progress = _make_task(
            "T-011",
            status="in_progress",
            scope_paths=["config/tasks/"],
        )
        all_tasks = [candidate, in_progress]
        eligible, reason = check_scope_overlap_with_in_progress(candidate, all_tasks)
        assert eligible is True

    def test_eligible_no_in_progress_tasks(self) -> None:
        candidate = _make_task("T-010")
        all_tasks = [candidate, _make_task("T-011", status="pending")]
        eligible, reason = check_scope_overlap_with_in_progress(candidate, all_tasks)
        assert eligible is True

    def test_task_not_overlapping_with_itself(self) -> None:
        task = _make_task("T-010", status="in_progress")
        all_tasks = [task]
        eligible, reason = check_scope_overlap_with_in_progress(task, all_tasks)
        assert eligible is True


# ── is_fully_auto_dispatchable ────────────────────────────────────────────────


class TestIsFullyAutoDispatchable:
    def test_all_predicates_pass(self) -> None:
        candidate = _make_task("T-010")
        other = _make_task("T-011", status="pending")
        eligible, reason = is_fully_auto_dispatchable(
            candidate,
            [candidate, other],
            _ENVELOPE,
            Path("/tmp/unused"),
        )
        assert eligible is True

    def test_fails_on_requires_approval(self) -> None:
        candidate = _make_task("T-010", requires_approval=True)
        eligible, reason = is_fully_auto_dispatchable(
            candidate,
            [candidate],
            _ENVELOPE,
            Path("/tmp/unused"),
        )
        assert eligible is False

    def test_fails_on_scope_overlap(self) -> None:
        candidate = _make_task("T-010", scope_paths=["runtime/orchestration/"])
        in_progress = _make_task("T-011", status="in_progress", scope_paths=["runtime/"])
        eligible, reason = is_fully_auto_dispatchable(
            candidate, [candidate, in_progress], _ENVELOPE, Path("/tmp/unused")
        )
        assert eligible is False
        assert "overlap" in reason

    def test_flagged_task_fails_without_council_record(self, tmp_path: Path) -> None:
        candidate = _make_task("T-010", decision_support_required=True)
        eligible, reason = is_fully_auto_dispatchable(candidate, [candidate], _ENVELOPE, tmp_path)
        assert eligible is False
        assert "decision_support_required" in reason

    def test_flagged_task_fails_with_unresolved_council_record(self, tmp_path: Path) -> None:
        candidate = _make_task("T-010", decision_support_required=True)
        closures_dir = tmp_path / "artifacts" / "dispatch" / "closures"
        closures_dir.mkdir(parents=True)
        (closures_dir / "CR-001.yaml").write_text(
            yaml.dump(
                {
                    "schema_version": "council_request.v1",
                    "request_id": "001",
                    "requested_at": "2026-04-05T12:00:00Z",
                    "trigger": "decision_support_needed",
                    "question": "Proceed?",
                    "context_summary": "Need decision support.",
                    "suggested_respondents": ["Governance", "Risk"],
                    "options": [{"label": "Approve", "description": "Proceed"}],
                    "requires_quorum": True,
                    "related_tasks": ["T-010"],
                    "resolved": False,
                    "resolved_at": None,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        eligible, reason = is_fully_auto_dispatchable(candidate, [candidate], _ENVELOPE, tmp_path)
        assert eligible is False
        assert "unresolved" in reason

    def test_flagged_task_passes_with_resolved_council_record(self, tmp_path: Path) -> None:
        candidate = _make_task("T-010", decision_support_required=True)
        closures_dir = tmp_path / "artifacts" / "dispatch" / "closures"
        closures_dir.mkdir(parents=True)
        (closures_dir / "CR-001.yaml").write_text(
            yaml.dump(
                {
                    "schema_version": "council_request.v1",
                    "request_id": "001",
                    "requested_at": "2026-04-05T12:00:00Z",
                    "trigger": "decision_support_needed",
                    "question": "Proceed?",
                    "context_summary": "Need decision support.",
                    "suggested_respondents": ["Governance", "Risk"],
                    "options": [{"label": "Approve", "description": "Proceed"}],
                    "requires_quorum": True,
                    "related_tasks": ["T-010"],
                    "resolved": True,
                    "resolved_at": "2026-04-05T12:10:00Z",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        eligible, reason = is_fully_auto_dispatchable(candidate, [candidate], _ENVELOPE, tmp_path)
        assert eligible is True
        assert "resolved" in reason


# ── cmd_coo_propose --execute integration ─────────────────────────────────────


def _write_backlog(repo_root: Path, tasks: list[dict]) -> None:
    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _task_dict(
    task_id: str,
    *,
    status: str = "pending",
    risk: str = "low",
    requires_approval: bool = False,
    task_type: str = "build",
    scope_paths: list[str] | None = None,
) -> dict:
    from datetime import datetime, timezone

    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": "P1",
        "risk": risk,
        "scope_paths": scope_paths or ["runtime/orchestration/coo/"],
        "status": status,
        "requires_approval": requires_approval,
        "decision_support_required": False,
        "owner": "codex",
        "evidence": "",
        "task_type": task_type,
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }


def _write_delegation(repo_root: Path) -> None:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump(_ENVELOPE),
        encoding="utf-8",
    )


def _write_template(repo_root: Path, template_name: str = "build") -> None:
    template_dir = repo_root / "config" / "tasks" / "order_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / f"{template_name}.yaml").write_text(
        yaml.dump(
            {
                "schema_version": "order_template.v1",
                "template_name": template_name,
                "description": f"{template_name} template",
                "steps": [{"name": "build", "role": "builder"}],
                "constraints": {
                    "worktree": True,
                    "max_duration_seconds": 900,
                    "governance_policy": None,
                },
                "shadow": {
                    "enabled": False,
                    "provider": "codex",
                    "receives": "full_task_payload",
                },
                "supervision": {"per_cycle_check": False},
            },
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


_ELIGIBLE_PROPOSAL_YAML = """\
schema_version: task_proposal.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
proposals:
  - task_id: T-auto-001
    rationale: Low-risk, no approval needed.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""

_INELIGIBLE_PROPOSAL_YAML = """\
schema_version: task_proposal.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
proposals:
  - task_id: T-needs-approval
    rationale: Requires explicit approval.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""


class TestProposExecuteFlag:
    def test_propose_execute_flag_registered(self, tmp_path: Path) -> None:
        """The --execute flag must be accepted by the CLI parser."""
        import argparse

        ns = argparse.Namespace(json=False, execute=True)
        assert getattr(ns, "execute", None) is True

    def test_propose_execute_dispatches_eligible(self, tmp_path: Path, capsys) -> None:
        """Eligible task auto-dispatches when --execute is set."""
        _write_backlog(tmp_path, [_task_dict("T-auto-001")])
        _write_delegation(tmp_path)
        _write_template(tmp_path, "build")

        mock_dispatch_result = MagicMock()
        mock_dispatch_result.order_id = "ORD-T-auto-001-20260310"
        mock_dispatch_result.outcome = "SUCCESS"

        with (
            patch(
                "runtime.orchestration.coo.service.invoke_coo_reasoning",
                return_value=_ELIGIBLE_PROPOSAL_YAML,
            ),
            patch(
                "runtime.orchestration.coo.commands.verify_claims",
                return_value=[],
            ),
            patch(
                "runtime.orchestration.coo.commands.collect_evidence",
            ),
            patch(
                "runtime.orchestration.dispatch.engine.DispatchEngine.execute",
                return_value=mock_dispatch_result,
            ),
        ):
            rc = cmd_coo_propose(argparse.Namespace(json=False, execute=True), tmp_path)

        assert rc == 0
        out = capsys.readouterr().out
        assert "T-auto-001" in out

    def test_propose_execute_skips_ineligible(self, tmp_path: Path, capsys) -> None:
        """Ineligible task (requires_approval=True) prints as pending approval."""
        _write_backlog(tmp_path, [_task_dict("T-needs-approval", requires_approval=True)])
        _write_delegation(tmp_path)

        with (
            patch(
                "runtime.orchestration.coo.service.invoke_coo_reasoning",
                return_value=_INELIGIBLE_PROPOSAL_YAML,
            ),
            patch(
                "runtime.orchestration.coo.commands.verify_claims",
                return_value=[],
            ),
            patch(
                "runtime.orchestration.coo.commands.collect_evidence",
            ),
        ):
            rc = cmd_coo_propose(argparse.Namespace(json=False, execute=True), tmp_path)

        assert rc == 0
        out = capsys.readouterr().out
        assert "pending approval" in out

    def test_propose_execute_clean_fail_returns_one(self, tmp_path: Path, capsys) -> None:
        """CLEAN_FAIL dispatch outcome must return exit code 1, not 0."""
        _write_backlog(tmp_path, [_task_dict("T-auto-001")])
        _write_delegation(tmp_path)
        _write_template(tmp_path, "build")

        mock_dispatch_result = MagicMock()
        mock_dispatch_result.order_id = "ORD-T-auto-001-20260310"
        mock_dispatch_result.outcome = "CLEAN_FAIL"
        mock_dispatch_result.reason = "repo dirty after execution"

        with (
            patch(
                "runtime.orchestration.coo.service.invoke_coo_reasoning",
                return_value=_ELIGIBLE_PROPOSAL_YAML,
            ),
            patch(
                "runtime.orchestration.coo.commands.verify_claims",
                return_value=[],
            ),
            patch(
                "runtime.orchestration.coo.commands.collect_evidence",
            ),
            patch(
                "runtime.orchestration.dispatch.engine.DispatchEngine.execute",
                return_value=mock_dispatch_result,
            ),
        ):
            rc = cmd_coo_propose(argparse.Namespace(json=False, execute=True), tmp_path)

        assert rc == 1
        err = capsys.readouterr().err
        assert "CLEAN_FAIL" in err


class TestProgressObligationIntegration:
    def test_progress_obligation_violation_warns(self, tmp_path: Path, capsys) -> None:
        """NTP with vague reason emits a warning."""
        _write_backlog(tmp_path, [_task_dict("T-001")])
        _write_delegation(tmp_path)

        vague_ntp = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: No pending actionable tasks.\n"
            "recommended_follow_up: Suggest waiting for alignment.\n"
        )

        with (
            patch(
                "runtime.orchestration.coo.service.invoke_coo_reasoning",
                return_value=vague_ntp,
            ),
            patch(
                "runtime.orchestration.coo.commands.collect_evidence",
            ),
        ):
            rc = cmd_coo_propose(argparse.Namespace(json=False, execute=False), tmp_path)

        assert rc == 0
        err = capsys.readouterr().err
        assert "PROGRESS_OBLIGATION_VIOLATION" in err

    def test_progress_obligation_satisfied_no_warning(self, tmp_path: Path, capsys) -> None:
        """NTP with policy-cited reason has no warning."""
        _write_backlog(tmp_path, [_task_dict("T-001")])
        _write_delegation(tmp_path)

        specific_ntp = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: All tasks require L3 approval per policy. Nothing auto-eligible.\n"
        )

        with (
            patch(
                "runtime.orchestration.coo.service.invoke_coo_reasoning",
                return_value=specific_ntp,
            ),
            patch(
                "runtime.orchestration.coo.commands.collect_evidence",
            ),
        ):
            rc = cmd_coo_propose(argparse.Namespace(json=False, execute=False), tmp_path)

        assert rc == 0
        err = capsys.readouterr().err
        assert "PROGRESS_OBLIGATION_VIOLATION" not in err
