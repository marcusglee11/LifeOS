"""Tests for ExecutionOrder schema validation."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from runtime.orchestration.dispatch.order import (
    ORDER_SCHEMA_VERSION,
    ConstraintsSpec,
    ExecutionOrder,
    OrderValidationError,
    ShadowSpec,
    StepSpec,
    SupervisionSpec,
    load_order,
    parse_order,
)


MINIMAL_VALID = {
    "schema_version": ORDER_SCHEMA_VERSION,
    "order_id": "exec_test_001",
    "task_ref": "BACKLOG-P1-test",
    "created_at": "2026-02-26T10:00:00Z",
    "steps": [
        {"name": "build", "role": "builder"},
    ],
}


def test_parse_minimal_valid():
    order = parse_order(MINIMAL_VALID)
    assert order.order_id == "exec_test_001"
    assert order.task_ref == "BACKLOG-P1-test"
    assert order.schema_version == ORDER_SCHEMA_VERSION
    assert len(order.steps) == 1
    assert order.steps[0].name == "build"
    assert order.steps[0].role == "builder"
    assert order.steps[0].provider == "auto"


def test_parse_full_order():
    raw = {
        "schema_version": ORDER_SCHEMA_VERSION,
        "order_id": "exec_full_001",
        "task_ref": "BACKLOG-P1-full",
        "created_at": "2026-02-26T10:00:00Z",
        "steps": [
            {"name": "design", "role": "designer", "provider": "auto"},
            {"name": "build", "role": "builder", "provider": "codex"},
            {
                "name": "review",
                "role": "council_v2",
                "mode": "shadow",
                "lens_providers": {"architecture": "codex", "security": "claude"},
            },
        ],
        "constraints": {
            "worktree": True,
            "max_duration_seconds": 1800,
            "scope_paths": ["runtime/orchestration/"],
        },
        "shadow": {
            "enabled": True,
            "provider": "gemini",
        },
        "supervision": {
            "per_cycle_check": True,
            "batch_id": "batch_001",
            "cycle_number": 3,
        },
    }
    order = parse_order(raw)
    assert len(order.steps) == 3
    assert order.steps[1].provider == "codex"
    assert order.steps[2].lens_providers == {"architecture": "codex", "security": "claude"}
    assert order.constraints.worktree is True
    assert order.constraints.max_duration_seconds == 1800
    assert order.constraints.scope_paths == ["runtime/orchestration/"]
    assert order.shadow.enabled is True
    assert order.shadow.provider == "gemini"
    assert order.supervision.batch_id == "batch_001"
    assert order.supervision.cycle_number == 3


def test_wrong_schema_version_rejected():
    raw = dict(MINIMAL_VALID)
    raw["schema_version"] = "execution_order.v99"
    with pytest.raises(OrderValidationError, match="schema_version"):
        parse_order(raw)


def test_missing_order_id_rejected():
    raw = dict(MINIMAL_VALID)
    raw["order_id"] = ""
    with pytest.raises(OrderValidationError, match="order_id"):
        parse_order(raw)


def test_order_id_path_traversal_rejected():
    raw = dict(MINIMAL_VALID)
    raw["order_id"] = "../etc/passwd"
    with pytest.raises(OrderValidationError, match="order_id"):
        parse_order(raw)


def test_order_id_slash_rejected():
    raw = dict(MINIMAL_VALID)
    raw["order_id"] = "valid/but/slashed"
    with pytest.raises(OrderValidationError, match="order_id"):
        parse_order(raw)


def test_order_id_valid_formats():
    for valid_id in ["exec_001", "EXEC-001", "exec20260226001", "A-B_C-1"]:
        raw = dict(MINIMAL_VALID)
        raw["order_id"] = valid_id
        order = parse_order(raw)
        assert order.order_id == valid_id


def test_missing_task_ref_rejected():
    raw = dict(MINIMAL_VALID)
    raw["task_ref"] = ""
    with pytest.raises(OrderValidationError, match="task_ref"):
        parse_order(raw)


def test_empty_steps_rejected():
    raw = dict(MINIMAL_VALID)
    raw["steps"] = []
    with pytest.raises(OrderValidationError, match="steps"):
        parse_order(raw)


def test_step_missing_name_rejected():
    raw = dict(MINIMAL_VALID, steps=[{"role": "builder"}])
    with pytest.raises(OrderValidationError, match="name"):
        parse_order(raw)


def test_step_missing_role_rejected():
    raw = dict(MINIMAL_VALID, steps=[{"name": "build"}])
    with pytest.raises(OrderValidationError, match="role"):
        parse_order(raw)


def test_load_order_from_yaml_file(tmp_path):
    order_file = tmp_path / "test_order.yaml"
    order_file.write_text(
        yaml.dump(MINIMAL_VALID, sort_keys=True, default_flow_style=False),
        encoding="utf-8",
    )
    order = load_order(order_file)
    assert order.order_id == "exec_test_001"


def test_load_order_invalid_yaml(tmp_path):
    order_file = tmp_path / "bad.yaml"
    order_file.write_text("this: is: not: valid: yaml: [\n", encoding="utf-8")
    with pytest.raises(OrderValidationError):
        load_order(order_file)


def test_constraints_defaults():
    order = parse_order(MINIMAL_VALID)
    assert order.constraints.worktree is False
    assert order.constraints.max_duration_seconds == 3600
    assert order.constraints.scope_paths == []
    assert order.constraints.governance_policy is None


def test_shadow_defaults():
    order = parse_order(MINIMAL_VALID)
    assert order.shadow.enabled is False
    assert order.shadow.provider == "codex"
    assert order.shadow.receives == "full_task_payload"


def test_supervision_defaults():
    order = parse_order(MINIMAL_VALID)
    assert order.supervision.per_cycle_check is False
    assert order.supervision.batch_id is None
    assert order.supervision.cycle_number is None
