"""Tests for COO proposal parsing and execution-order generation."""

from __future__ import annotations

import re
import subprocess as _subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.coo.parser import (
    OPERATION_PROPOSAL_SCHEMA_VERSION,
    ParseError,
    TaskProposal,
    _extract_yaml_payload,
    _extract_yaml_payload_with_stage,
    parse_execution_order,
    parse_operation_proposal,
    parse_proposal_response,
)


def _find_repo_root() -> Path:
    result = _subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_task(task_id: str = "T-003") -> TaskEntry:
    return TaskEntry(
        id=task_id,
        title="Example task",
        description="",
        dod="",
        priority="P1",
        risk="low",
        scope_paths=["runtime/orchestration/coo/"],
        status="pending",
        requires_approval=False,
        owner="",
        evidence="",
        task_type="build",
        tags=[],
        objective_ref="bootstrap",
        created_at=_now_iso(),
        completed_at=None,
    )


def test_parse_yaml_block_from_text() -> None:
    text = """
Some COO analysis text.

```yaml
schema_version: task_proposal.v1
proposals:
  - task_id: T-003
    rationale: Highest impact first
    urgency_override: P0
    suggested_owner: codex
    proposed_action: dispatch
```
"""
    proposals = parse_proposal_response(text)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.task_id == "T-003"
    assert proposal.rationale == "Highest impact first"
    assert proposal.urgency_override == "P0"
    assert proposal.suggested_owner == "codex"
    assert proposal.proposed_action == "dispatch"


def test_parse_raw_yaml_text() -> None:
    text = """
schema_version: task_proposal.v1
proposals:
  - task_id: T-004
    rationale: Depends on upstream merge
    proposed_action: defer
"""
    proposals = parse_proposal_response(text)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.task_id == "T-004"
    assert proposal.rationale == "Depends on upstream merge"
    assert proposal.proposed_action == "defer"
    assert proposal.urgency_override is None
    assert proposal.suggested_owner == ""


def test_parse_wrong_schema_version_raises() -> None:
    text = """
schema_version: task_proposal.v9
proposals:
  - task_id: T-004
    rationale: test
    proposed_action: defer
"""
    with pytest.raises(ParseError, match="schema_version"):
        parse_proposal_response(text)


def test_parse_empty_proposals_raises() -> None:
    text = """
schema_version: task_proposal.v1
proposals: []
"""
    with pytest.raises(ParseError, match="No proposals found in response"):
        parse_proposal_response(text)


def test_parse_missing_required_field_raises() -> None:
    text = """
schema_version: task_proposal.v1
proposals:
  - task_id: T-004
    proposed_action: dispatch
"""
    with pytest.raises(ParseError, match="missing required field"):
        parse_proposal_response(text)


def test_parse_invalid_proposed_action_raises() -> None:
    text = """
schema_version: task_proposal.v1
proposals:
  - task_id: T-004
    rationale: test
    proposed_action: execute
"""
    with pytest.raises(ParseError, match="invalid proposed_action"):
        parse_proposal_response(text)


def test_parse_invalid_urgency_override_raises() -> None:
    text = """
schema_version: task_proposal.v1
proposals:
  - task_id: T-004
    rationale: test
    urgency_override: PX
    proposed_action: dispatch
"""
    with pytest.raises(ParseError, match="invalid urgency_override"):
        parse_proposal_response(text)


def test_parse_execution_order_structure() -> None:
    proposal = TaskProposal(
        task_id="T-003",
        rationale="Ship quickly",
        urgency_override="P0",
        suggested_owner="codex",
        proposed_action="dispatch",
    )
    task = _make_task("T-003")
    template_data = {
        "steps": [{"name": "build", "role": "builder", "provider": "codex", "mode": "blocking"}],
        "constraints": {"worktree": True, "max_duration_seconds": 900},
        "shadow": {"enabled": True, "provider": "claude-code", "receives": "full_task_payload"},
        "supervision": {"per_cycle_check": True, "batch_id": "B-1", "cycle_number": 2},
    }

    order = parse_execution_order(proposal, task, template_data)

    assert order["schema_version"] == "execution_order.v1"
    assert order["task_ref"] == "T-003"
    assert order["order_id"].startswith("ORD-T-003-")
    datetime.fromisoformat(order["created_at"])
    assert order["steps"] == template_data["steps"]
    assert order["constraints"]["scope_paths"] == task.scope_paths
    assert order["constraints"]["worktree"] is True
    assert order["constraints"]["max_duration_seconds"] == 900
    assert order["shadow"] == template_data["shadow"]
    assert order["supervision"] == template_data["supervision"]


def test_parse_execution_order_order_id_format() -> None:
    proposal = TaskProposal(
        task_id="T_003-ALPHA",
        rationale="test",
        urgency_override=None,
        suggested_owner="",
        proposed_action="dispatch",
    )
    task = _make_task("T_003-ALPHA")
    order = parse_execution_order(
        proposal,
        task,
        {"steps": [{"name": "build", "role": "builder"}]},
    )

    assert re.match(r"^[a-zA-Z0-9_\-]{1,128}$", order["order_id"])


def test_parse_execution_order_invalid_task_id_raises_parse_error() -> None:
    proposal = TaskProposal(
        task_id="BAD/ID",
        rationale="test",
        urgency_override=None,
        suggested_owner="",
        proposed_action="dispatch",
    )
    task = _make_task("T-003")

    with pytest.raises(ParseError, match="Generated order_id"):
        parse_execution_order(
            proposal,
            task,
            {"steps": [{"name": "build", "role": "builder"}]},
        )


# ---------------------------------------------------------------------------
# Prose-preamble extraction tests (OUTPUT_CONTRACT_DRIFT fix)
# ---------------------------------------------------------------------------


def test_extract_yaml_payload_prose_preamble() -> None:
    text = (
        "I reviewed the backlog and here is my recommendation.\n\n"
        "schema_version: task_proposal.v1\n"
        "proposals:\n"
        "  - task_id: T-010\n"
        "    rationale: Highest priority.\n"
        "    proposed_action: dispatch\n"
        "    urgency_override: null\n"
        "    suggested_owner: codex\n"
    )
    result = _extract_yaml_payload(text)
    assert result.startswith("schema_version: task_proposal.v1")
    assert "I reviewed" not in result


def test_extract_yaml_payload_indented_schema_version() -> None:
    text = (
        "  schema_version: task_proposal.v1\n"
        "proposals:\n"
        "  - task_id: T-011\n"
        "    rationale: test\n"
        "    proposed_action: defer\n"
        "    urgency_override: null\n"
        '    suggested_owner: ""\n'
    )
    result = _extract_yaml_payload(text)
    assert result.startswith("schema_version: task_proposal.v1")


def test_extract_yaml_payload_valid_yaml_schema_not_first_not_truncated() -> None:
    """Valid YAML where schema_version is not the first key must not be truncated."""
    text = "proposals:\n  - task_id: T-020\nschema_version: task_proposal.v1\n"
    result = _extract_yaml_payload(text)
    assert "proposals" in result
    assert "schema_version" in result


def test_extract_yaml_payload_with_stage_fence_recovery() -> None:
    text = "Operator note.\n\n```yaml\nschema_version: task_proposal.v1\nproposals: []\n```\n"
    result, stage = _extract_yaml_payload_with_stage(text)
    assert result.startswith("schema_version: task_proposal.v1")
    assert stage == "fence_recovery"


def test_extract_yaml_payload_with_stage_schema_block_recovery() -> None:
    text = "Intro prose.\n\nschema_version: task_proposal.v1\nproposals: []\n"
    result, stage = _extract_yaml_payload_with_stage(text)
    assert result.startswith("schema_version: task_proposal.v1")
    assert stage == "schema_block_recovery"


def test_extract_yaml_payload_with_stage_direct() -> None:
    text = "schema_version: task_proposal.v1\nproposals: []\n"
    result, stage = _extract_yaml_payload_with_stage(text)
    assert result.startswith("schema_version: task_proposal.v1")
    assert stage == "direct"


def test_parse_proposal_prose_preamble() -> None:
    text = (
        "Here is my analysis of the backlog.\n\n"
        "schema_version: task_proposal.v1\n"
        "proposals:\n"
        "  - task_id: T-012\n"
        "    rationale: Top priority task.\n"
        "    proposed_action: dispatch\n"
        "    urgency_override: null\n"
        "    suggested_owner: codex\n"
    )
    proposals = parse_proposal_response(text)
    assert len(proposals) == 1
    assert proposals[0].task_id == "T-012"
    assert proposals[0].proposed_action == "dispatch"


def test_parse_proposal_pure_prose_raises() -> None:
    text = "I looked at the backlog and recommend starting with the highest priority items."
    with pytest.raises(ParseError):
        parse_proposal_response(text)


def test_parse_operation_proposal_success() -> None:
    text = (
        f"schema_version: {OPERATION_PROPOSAL_SCHEMA_VERSION}\n"
        "proposal_id: OP-a1b2c3d4\n"
        "title: Write note\n"
        "rationale: Safe workspace mutation.\n"
        "operation_kind: mutation\n"
        "action_id: workspace.file.write\n"
        "args:\n"
        "  path: /workspace/notes/test.md\n"
        "  content: hello\n"
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
    )

    parsed = parse_operation_proposal(text)

    assert parsed["proposal_id"] == "OP-a1b2c3d4"
    assert parsed["action_id"] == "workspace.file.write"


def test_parse_operation_proposal_accepts_hyphenated_proposal_id() -> None:
    text = (
        f"schema_version: {OPERATION_PROPOSAL_SCHEMA_VERSION}\n"
        "proposal_id: OP-WORKSPACE-WRITE-TELEGRAM-002\n"
        "title: Write note\n"
        "rationale: Safe workspace mutation.\n"
        "operation_kind: mutation\n"
        "action_id: workspace.file.write\n"
        "args:\n"
        "  path: /workspace/notes/test.md\n"
        "  content: hello\n"
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
    )

    parsed = parse_operation_proposal(text)

    assert parsed["proposal_id"] == "OP-WORKSPACE-WRITE-TELEGRAM-002"


def test_parse_operation_proposal_rejects_unknown_action() -> None:
    text = (
        f"schema_version: {OPERATION_PROPOSAL_SCHEMA_VERSION}\n"
        "proposal_id: OP-a1b2c3d4\n"
        "title: Bad action\n"
        "rationale: no-op\n"
        "operation_kind: mutation\n"
        "action_id: workspace.file.delete\n"
        "args: {}\n"
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
    )

    with pytest.raises(ParseError, match="Unsupported action_id"):
        parse_operation_proposal(text)


def test_parse_operation_proposal_rejects_invalid_workspace_path() -> None:
    text = (
        f"schema_version: {OPERATION_PROPOSAL_SCHEMA_VERSION}\n"
        "proposal_id: OP-a1b2c3d4\n"
        "title: Bad path\n"
        "rationale: invalid\n"
        "operation_kind: mutation\n"
        "action_id: workspace.file.write\n"
        "args:\n"
        "  path: /tmp/outside.md\n"
        "  content: hello\n"
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
    )

    with pytest.raises(ParseError, match="relative or use the /workspace"):
        parse_operation_proposal(text)
