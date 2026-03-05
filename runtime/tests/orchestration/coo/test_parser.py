"""Tests for COO proposal parsing and execution-order generation."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.coo.parser import (
    ParseError,
    TaskProposal,
    parse_execution_order,
    parse_proposal_response,
)

import subprocess as _subprocess


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
        "steps": [
            {"name": "build", "role": "builder", "provider": "codex", "mode": "blocking"}
        ],
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
