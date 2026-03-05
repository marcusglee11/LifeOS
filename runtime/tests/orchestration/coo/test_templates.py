"""Tests for COO order templates and template instantiation."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.orchestration.coo.templates import (
    TEMPLATE_SCHEMA_VERSION,
    TemplateValidationError,
    instantiate_order,
    load_template,
)


def _write_template(repo_root: Path, name: str, data: dict) -> None:
    template_dir = repo_root / "config" / "tasks" / "order_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / f"{name}.yaml").write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _template_payload(name: str, worktree: bool) -> dict:
    return {
        "schema_version": TEMPLATE_SCHEMA_VERSION,
        "template_name": name,
        "description": f"{name} template",
        "steps": [
            {
                "name": "step_a",
                "role": "builder",
                "provider": "auto",
                "mode": "blocking",
            }
        ],
        "constraints": {
            "worktree": worktree,
            "max_duration_seconds": 3600,
            "governance_policy": None,
        },
        "shadow": {
            "enabled": False,
            "provider": "codex",
            "receives": "full_task_payload",
        },
        "supervision": {"per_cycle_check": False},
    }


def test_load_build_template_valid(tmp_path: Path) -> None:
    _write_template(tmp_path, "build", _template_payload("build", True))
    loaded = load_template("build", tmp_path)
    assert loaded["template_name"] == "build"


def test_load_content_template_valid(tmp_path: Path) -> None:
    _write_template(tmp_path, "content", _template_payload("content", False))
    loaded = load_template("content", tmp_path)
    assert loaded["template_name"] == "content"


def test_load_hygiene_template_valid(tmp_path: Path) -> None:
    _write_template(tmp_path, "hygiene", _template_payload("hygiene", True))
    loaded = load_template("hygiene", tmp_path)
    assert loaded["template_name"] == "hygiene"


def test_load_unknown_template_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_template("unknown", tmp_path)


def test_load_wrong_schema_version_raises(tmp_path: Path) -> None:
    bad = _template_payload("build", True)
    bad["schema_version"] = "order_template.v99"
    _write_template(tmp_path, "build", bad)
    with pytest.raises(TemplateValidationError, match="schema_version"):
        load_template("build", tmp_path)


def test_load_name_mismatch_raises(tmp_path: Path) -> None:
    bad = _template_payload("content", False)
    _write_template(tmp_path, "build", bad)
    with pytest.raises(TemplateValidationError, match="mismatch"):
        load_template("build", tmp_path)


def test_load_empty_steps_raises(tmp_path: Path) -> None:
    bad = _template_payload("build", True)
    bad["steps"] = []
    _write_template(tmp_path, "build", bad)
    with pytest.raises(TemplateValidationError, match="steps"):
        load_template("build", tmp_path)


def test_instantiate_order_schema_version() -> None:
    template = _template_payload("build", True)
    order = instantiate_order(
        template=template,
        task_id="T-001",
        scope_paths=["runtime/"],
        created_at="2026-03-05T10:20:30Z",
    )
    assert order["schema_version"] == "execution_order.v1"


def test_instantiate_order_id_format() -> None:
    template = _template_payload("build", True)
    order = instantiate_order(
        template=template,
        task_id="T-001",
        scope_paths=["runtime/"],
        created_at="2026-03-05T10:20:30Z",
    )
    assert order["order_id"] == "ORD-T-001-20260305102030"


def test_instantiate_order_scope_paths() -> None:
    template = _template_payload("build", True)
    paths = ["runtime/", "config/tasks/"]
    order = instantiate_order(
        template=template,
        task_id="T-001",
        scope_paths=paths,
        created_at="2026-03-05T10:20:30Z",
    )
    assert order["constraints"]["scope_paths"] == paths


def test_instantiate_order_worktree_flag_inherited() -> None:
    template = _template_payload("hygiene", True)
    order = instantiate_order(
        template=template,
        task_id="T-001",
        scope_paths=["runtime/"],
        created_at="2026-03-05T10:20:30Z",
    )
    assert order["constraints"]["worktree"] is True
