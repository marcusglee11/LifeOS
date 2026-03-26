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
    cmd_coo_chat,
    cmd_coo_direct,
    cmd_coo_prompt_status,
    cmd_coo_propose,
    cmd_coo_reject,
    cmd_coo_report,
    cmd_coo_status,
    cmd_coo_telegram_status,
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

_VALID_OPERATION_YAML = """\
schema_version: operation_proposal.v1
proposal_id: OP-a1b2c3d4
title: "Write workspace note"
rationale: "The request fits the allowlisted ops lane."
operation_kind: mutation
action_id: workspace.file.write
args:
  path: /workspace/notes/example.md
  content: "Hello from COO."
requires_approval: true
suggested_owner: lifeos
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


def test_coo_direct_operation_proposal_queued(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=_VALID_OPERATION_YAML,
    ):
        rc = cmd_coo_direct(
            argparse.Namespace(intent="write a workspace note", execute=False),
            tmp_path,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == "queued: OP-a1b2c3d4"
    assert (tmp_path / "artifacts" / "coo" / "operations" / "proposals" / "OP-a1b2c3d4.yaml").exists()


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


def test_coo_approve_operation_proposal_executes(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["OP-a1b2c3d4"], json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "approved: OP-a1b2c3d4 -> OPR-" in out
    assert (tmp_path / "workspace" / "notes" / "example.md").read_text(encoding="utf-8") == "Hello from COO."


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


def test_coo_chat_returns_json_envelope_with_operation(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    with patch(
        "runtime.orchestration.coo.commands.coo_service.chat_message",
        return_value={
            "mode": "chat",
            "has_proposal": True,
            "proposal_id": "OP-a1b2c3d4",
            "status": "pending",
            "message": "I can stage that for approval.",
        },
    ):
        rc = cmd_coo_chat(
            argparse.Namespace(message="write a workspace note", execute=False),
            tmp_path,
        )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["has_proposal"] is True
    assert payload["proposal_id"] == "OP-a1b2c3d4"
    assert payload["status"] == "pending"
    assert "stage that for approval" in payload["message"]


def test_coo_chat_returns_conversation_only(tmp_path: Path, capsys) -> None:
    with patch(
        "runtime.orchestration.coo.commands.coo_service.chat_message",
        return_value={
            "mode": "chat",
            "has_proposal": False,
            "proposal_id": None,
            "status": "conversation_only",
            "message": "Here is a conversational answer with no machine packet.",
        },
    ):
        rc = cmd_coo_chat(
            argparse.Namespace(message="hello", execute=False),
            tmp_path,
        )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["has_proposal"] is False
    assert payload["status"] == "conversation_only"


def test_coo_prompt_status_detects_drift(tmp_path: Path, capsys, monkeypatch) -> None:
    canonical = tmp_path / "config" / "coo"
    canonical.mkdir(parents=True, exist_ok=True)
    (canonical / "prompt_canonical.md").write_text("canonical prompt", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("different prompt", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))

    rc = cmd_coo_prompt_status(argparse.Namespace(json=True), tmp_path)

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["in_sync"] is False


def test_coo_reject_operation_proposal_writes_receipt(tmp_path: Path, capsys) -> None:
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    rc = cmd_coo_reject(
        argparse.Namespace(
            proposal_id="OP-a1b2c3d4",
            reason="Not approved",
        ),
        tmp_path,
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert payload["reason"] == "Not approved"
    assert payload["order_id"] is None


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


# ---------------------------------------------------------------------------
# coo telegram status
# ---------------------------------------------------------------------------

def test_telegram_status_no_file(tmp_path: Path, capsys) -> None:
    rc = cmd_coo_telegram_status(argparse.Namespace(json=False), tmp_path)
    assert rc == 0
    assert "not running" in capsys.readouterr().out


def test_telegram_status_no_file_json(tmp_path: Path, capsys) -> None:
    rc = cmd_coo_telegram_status(argparse.Namespace(json=True), tmp_path)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "not_running"


def _write_telegram_status(tmp_path: Path, data: dict) -> None:
    p = tmp_path / "artifacts" / "status"
    p.mkdir(parents=True, exist_ok=True)
    (p / "coo_telegram_runtime.json").write_text(json.dumps(data), encoding="utf-8")


def test_telegram_status_running_active(tmp_path: Path, capsys) -> None:
    _write_telegram_status(tmp_path, {
        "state": "running",
        "mode": "polling",
        "started_at": "2026-03-26T10:00:00+00:00",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_message_at": "2026-03-26T10:01:00+00:00",
        "last_reply_at": "2026-03-26T10:01:01+00:00",
        "last_latency_ms": 950,
    })
    rc = cmd_coo_telegram_status(argparse.Namespace(json=False), tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "running (active)" in out
    assert "950" in out


def test_telegram_status_stale(tmp_path: Path, capsys) -> None:
    from datetime import timedelta
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    _write_telegram_status(tmp_path, {
        "state": "running",
        "mode": "polling",
        "started_at": "2026-03-26T10:00:00+00:00",
        "updated_at": stale_time,
    })
    rc = cmd_coo_telegram_status(argparse.Namespace(json=False), tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "stale" in out


def test_telegram_status_stale_json(tmp_path: Path, capsys) -> None:
    from datetime import timedelta
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    _write_telegram_status(tmp_path, {
        "state": "running",
        "mode": "polling",
        "updated_at": stale_time,
    })
    rc = cmd_coo_telegram_status(argparse.Namespace(json=True), tmp_path)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "stale" in payload["state_display"]


def test_telegram_status_error_state(tmp_path: Path, capsys) -> None:
    _write_telegram_status(tmp_path, {
        "state": "error",
        "mode": "polling",
        "started_at": "2026-03-26T10:00:00+00:00",
        "updated_at": "2026-03-26T10:05:00+00:00",
        "last_error": "gateway connection refused",
    })
    rc = cmd_coo_telegram_status(argparse.Namespace(json=False), tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "error" in out
    assert "gateway connection refused" in out
