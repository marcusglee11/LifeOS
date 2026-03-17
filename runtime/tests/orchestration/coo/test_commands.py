"""Tests for COO CLI command handlers."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.commands import (
    cmd_coo_approve,
    cmd_coo_direct,
    cmd_coo_propose,
    cmd_coo_report,
    cmd_coo_status,
)
from runtime.orchestration.coo.invoke import InvocationError
from runtime.orchestration.dispatch.order import parse_order


_VALID_PROPOSAL_YAML = """\
schema_version: task_proposal.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
proposals:
  - task_id: T-101
    rationale: P1 priority, highest actionable.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""

_VALID_NTP_YAML = """\
schema_version: nothing_to_propose.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
reason: No pending actionable tasks.
recommended_follow_up: Wait for completions.
"""

_VALID_ESCALATION_YAML = """\
schema_version: escalation_packet.v1
generated_at: "2026-03-08T00:00:00Z"
run_id: burnin-test-001
type: governance_surface_touch
context:
  summary: Protected path modification requested.
  objective_ref: bootstrap
  task_ref: ""
analysis:
  issue: Path is protected.
options:
  - label: Escalate to CEO
    tradeoff: Governance-safe.
  - label: Defer
    tradeoff: Slower.
recommendation: Escalate to CEO.
"""


def _task(
    task_id: str,
    *,
    status: str = "pending",
    priority: str = "P1",
    task_type: str = "build",
    requires_approval: bool = True,
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": priority,
        "risk": "low",
        "scope_paths": ["runtime/"],
        "status": status,
        "requires_approval": requires_approval,
        "owner": "codex",
        "evidence": "",
        "task_type": task_type,
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": now_iso,
        "completed_at": None,
    }


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


def _write_delegation(repo_root: Path) -> None:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump({"schema_version": "delegation_envelope.v1", "trust_tier": "burn-in"}),
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


def test_coo_status_returns_zero(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-001", status="pending", priority="P0"),
            _task("T-002", status="in_progress", priority="P1"),
            _task("T-003", status="completed", priority="P2"),
            _task("T-004", status="blocked", priority="P3"),
        ],
    )

    rc = cmd_coo_status(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: 4 tasks" in out
    assert "pending:     1" in out
    assert "in_progress: 1" in out
    assert "completed:   1" in out
    assert "blocked:     1" in out
    assert "actionable (2):" in out


def test_coo_status_json_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", priority="P2")])

    rc = cmd_coo_status(argparse.Namespace(json=True), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_tasks"] == 1
    assert payload["by_status"]["pending"] == 1
    assert payload["actionable_count"] == 1


def test_coo_propose_success(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "schema_version: task_proposal.v1" in out
    assert "# COO invocation: not yet wired" not in out


def test_coo_propose_json_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=True, yaml=False, format="auto", execute=False),
            tmp_path,
        )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "task_proposal"
    assert "payload" in payload


def test_coo_propose_parse_error(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value="this is not valid yaml: ::::",
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 1
    err = capsys.readouterr().err
    assert "Error" in err


def test_coo_propose_invocation_error(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        side_effect=InvocationError("gateway unreachable"),
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 1
    err = capsys.readouterr().err
    assert "gateway unreachable" in err


def test_coo_propose_ntp(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_NTP_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "nothing_to_propose" in out


def test_coo_propose_ntp_json(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_NTP_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=True, yaml=False, format="auto", execute=False),
            tmp_path,
        )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "nothing_to_propose"
    assert payload["payload"]["reason"] == "No pending actionable tasks."


def test_coo_direct_prose_preamble_recovered(tmp_path: Path, capsys) -> None:
    """Prose preamble before escalation_packet.v1 YAML must be recovered (rc=0)."""
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value="Let me explain my reasoning.\n\n" + _VALID_ESCALATION_YAML,
    ):
        rc = cmd_coo_direct(
            argparse.Namespace(intent="update protected governance doc"),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("queued:")


def test_coo_direct_success(tmp_path: Path, capsys) -> None:
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_ESCALATION_YAML,
    ):
        rc = cmd_coo_direct(
            argparse.Namespace(intent="update protected governance doc"),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("queued:")


def test_coo_direct_invocation_error(tmp_path: Path, capsys) -> None:
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        side_effect=InvocationError("timeout"),
    ):
        rc = cmd_coo_direct(
            argparse.Namespace(intent="do something"),
            tmp_path,
        )

    assert rc == 1
    err = capsys.readouterr().err
    assert "timeout" in err


def test_coo_approve_writes_order_to_inbox(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-003", status="pending", task_type="build")])
    _write_template(tmp_path, "build")

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-003"], json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "approved: T-003 -> ORD-T-003-" in out

    inbox_dir = tmp_path / "artifacts" / "dispatch" / "inbox"
    files = list(inbox_dir.glob("ORD-T-003-*.yaml"))
    assert len(files) == 1

    raw = yaml.safe_load(files[0].read_text(encoding="utf-8"))
    assert raw["task_ref"] == "T-003"
    assert parse_order(raw).order_id == raw["order_id"]


def test_coo_approve_unknown_task_returns_one(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", task_type="build")])

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-X"], json=False), tmp_path)

    assert rc == 1
    captured = capsys.readouterr()
    assert "task not found: T-X" in captured.err


def test_coo_approve_creates_inbox_dir_if_missing(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-005", status="pending", task_type="build")])
    _write_template(tmp_path, "build")

    inbox_dir = tmp_path / "artifacts" / "dispatch" / "inbox"
    assert not inbox_dir.exists()

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-005"], json=False), tmp_path)

    assert rc == 0
    assert inbox_dir.exists()


def test_coo_approve_content_task_writes_native_workflow_order(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-020", status="pending", task_type="content")])
    _write_template(tmp_path, "content")

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-020"], json=False), tmp_path)

    assert rc == 0
    inbox_dir = tmp_path / "artifacts" / "dispatch" / "inbox"
    files = list(inbox_dir.glob("ORD-T-020-*.yaml"))
    assert len(files) == 1

    raw = yaml.safe_load(files[0].read_text(encoding="utf-8"))
    assert raw["workflow_id"] == "spec_creation.v1"
    assert raw["review_policy_id"] == "spec_review.v1"
    assert raw["mutation_policy_id"] == "mutation_authority.v1"
    assert raw["task_context"]["schema_version"] == "task_context.v1"
    assert raw["task_context"]["payload"]["requested_artifact"]["format"] == "markdown"


def test_coo_propose_prose_preamble_recovered(tmp_path: Path, capsys) -> None:
    """Prose preamble before task_proposal.v1 YAML must be recovered (rc=0)."""
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    prose_plus_yaml = (
        "I reviewed the backlog and here is my proposal.\n\n"
        + _VALID_PROPOSAL_YAML
    )
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=prose_plus_yaml,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 0


def test_coo_propose_ntp_prose_preamble_recovered(tmp_path: Path, capsys) -> None:
    """Prose preamble before nothing_to_propose.v1 YAML must be recovered (rc=0)."""
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    prose_plus_ntp = (
        "After careful analysis, I find nothing actionable right now.\n\n"
        + _VALID_NTP_YAML
    )
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=prose_plus_ntp,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 0


def test_coo_report_returns_json(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-201", status="pending"),
            _task("T-202", status="completed"),
        ],
    )
    _write_delegation(tmp_path)

    rc = cmd_coo_report(argparse.Namespace(), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["all_tasks"]) == 2
    assert payload["delegation_envelope"]["schema_version"] == "delegation_envelope.v1"


# ── Claim verification tests ──────────────────────────────────────────────────

_PROPOSAL_WITH_CLAIM = """\
schema_version: task_proposal.v1
generated_at: "2026-03-08T00:00:00Z"
mode: propose
objective_ref: bootstrap
proposals:
  - task_id: T-101
    rationale: T-101 has been completed. Now proposing next step.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""


def test_propose_blocks_on_claim_violation(tmp_path: Path, capsys) -> None:
    """Proposal with unsupported execution claim -> exit code 1."""
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_PROPOSAL_WITH_CLAIM,
    ), patch(
        "runtime.orchestration.coo.commands.verify_claims",
        return_value=[
            __import__(
                "runtime.orchestration.coo.claim_verifier",
                fromlist=["ClaimViolation"],
            ).ClaimViolation(
                claim_text="T-101 has been completed",
                claim_type="execution_state",
                required_evidence="order in completed/ with SUCCESS for task T-101",
                found_evidence="none",
            )
        ],
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 1
    err = capsys.readouterr().err
    assert "CLAIM_VIOLATION" in err


def test_propose_passes_clean_output(tmp_path: Path, capsys) -> None:
    """Proposal with no execution claims -> exit code 0."""
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ), patch(
        "runtime.orchestration.coo.commands.verify_claims",
        return_value=[],
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="yaml", execute=False),
            tmp_path,
        )

    assert rc == 0


def test_coo_propose_human_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="human", execute=False),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "COO proposal: 1 item(s)" in out
    assert "T-101 - Task T-101 [dispatch]" in out
    assert "Suggested owner: codex" in out


def test_coo_propose_human_ntp_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_NTP_YAML,
    ):
        rc = cmd_coo_propose(
            argparse.Namespace(json=False, yaml=False, format="human", execute=False),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "Nothing to propose" in out
    assert "Recommended follow-up: Wait for completions." in out


def test_status_shows_dispatch_state(tmp_path: Path, capsys) -> None:
    """cmd_coo_status output includes dispatch state section."""
    _write_backlog(
        tmp_path,
        [
            _task("T-001", status="pending", priority="P0"),
            _task("T-002", status="in_progress", priority="P1"),
        ],
    )

    rc = cmd_coo_status(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "dispatch:" in out
    assert "escalations:" in out


def test_status_json_includes_dispatch_state(tmp_path: Path, capsys) -> None:
    """cmd_coo_status --json output includes dispatch key."""
    _write_backlog(tmp_path, [_task("T-001", status="pending", priority="P0")])

    rc = cmd_coo_status(argparse.Namespace(json=True), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "dispatch" in payload
    assert "inbox" in payload["dispatch"]
    assert "active" in payload["dispatch"]
