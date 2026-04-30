from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from runtime.tools.workflow_pack import (
    doctor_quality_tools,
    route_quality_tools,
    run_quality_gates,
)
from scripts.workflow import quality_gate


def test_route_quality_tools_python_change() -> None:
    routed = route_quality_tools(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
    assert routed["ruff_check"] == ["runtime/tools/workflow_pack.py"]
    assert routed["ruff_format"] == ["runtime/tools/workflow_pack.py"]
    assert routed["mypy"] == ["runtime/tools/workflow_pack.py"]
    assert routed["markdownlint"] == []


def test_route_quality_tools_markdown_is_style_only() -> None:
    routed = route_quality_tools(Path("."), ["docs/02_protocols/example.md"], scope="changed")
    assert routed["markdownlint"] == ["docs/02_protocols/example.md"]
    assert routed["ruff_check"] == []
    assert routed["mypy"] == []


def test_route_quality_tools_agent_control_plane_pin_manifest() -> None:
    routed = route_quality_tools(
        Path("."), ["config/external_contracts/agent_control_plane_pin.yaml"], scope="changed"
    )
    assert routed["agent_control_plane_pin"] == [
        "config/external_contracts/agent_control_plane_pin.yaml"
    ]


def test_route_quality_tools_wmf_backlog_change() -> None:
    routed = route_quality_tools(Path("."), ["config/tasks/backlog.yaml"], scope="changed")
    assert routed["wmf_validator"] == ["config/tasks/backlog.yaml"]


def test_route_quality_tools_wmf_workstreams_change_bypasses_artifacts_exclusion() -> None:
    routed = route_quality_tools(Path("."), ["artifacts/workstreams.yaml"], scope="changed")
    assert routed["wmf_validator"] == ["artifacts/workstreams.yaml"]


def test_route_quality_tools_workstream_context_bypasses_artifacts_exclusion() -> None:
    routed = route_quality_tools(
        Path("."), ["artifacts/workstreams/context_v1/state.yaml"], scope="changed"
    )
    assert routed["workstream_context"] == ["artifacts/workstreams/context_v1/state.yaml"]


def test_route_quality_tools_workstream_context_schema_doc_script_and_fixture() -> None:
    changed = [
        "schemas/workstreams/workstream_state.schema.json",
        "docs/02_protocols/workstream_context_v1.md",
        "scripts/workflow/workstream_context.py",
        "runtime/tests/fixtures/workstreams/context_v1/state.yaml",
    ]
    routed = route_quality_tools(Path("."), changed, scope="changed")
    assert routed["workstream_context"] == changed


def test_route_quality_tools_config_only_markdown_change_no_fan_out(monkeypatch) -> None:
    monkeypatch.setattr(
        "runtime.tools.workflow_pack._git_tracked_files",
        lambda repo_root: ["docs/02_protocols/example.md", "runtime/tools/workflow_pack.py"],
    )
    routed = route_quality_tools(Path("."), [".markdownlint.json"], scope="changed")
    assert routed["markdownlint"] == [], (
        "markdownlint config change should not expand to tracked docs — run repo-scope explicitly"
    )


def test_route_quality_tools_config_only_yaml_change_no_fan_out(monkeypatch) -> None:
    monkeypatch.setattr(
        "runtime.tools.workflow_pack._git_tracked_files",
        lambda repo_root: [
            ".github/workflows/ci.yml",
            "config/quality/manifest.yaml",
            "docs/02_protocols/example.md",
        ],
    )
    routed = route_quality_tools(Path("."), [".yamllint.yml"], scope="changed")
    assert routed["yamllint"] == [], (
        "yamllint config change should not expand to tracked yamls — run repo-scope explicitly"
    )


def test_run_quality_gates_blocks_on_blocking_failure(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:2] == ["ruff", "check"]:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="unused import"
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
    assert result["passed"] is False
    assert any(
        row["tool"] == "ruff_check" and row["mode"] == "blocking" for row in result["results"]
    )


def test_run_quality_gates_allows_advisory_failure(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd and cmd[0] == "yamllint":
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="bad indent"
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(Path("."), ["config/quality/manifest.yaml"], scope="changed")
    assert result["passed"] is True
    assert any(
        row["tool"] == "yamllint" and row["mode"] == "advisory" and not row["passed"]
        for row in result["results"]
    )


def test_run_quality_gates_runs_agent_control_plane_pin(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(*args, **kwargs):
        cmd = args[0]
        commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(
        Path("."), ["config/external_contracts/agent_control_plane_pin.yaml"], scope="changed"
    )

    assert result["passed"] is True
    assert any(row["tool"] == "agent_control_plane_pin" for row in result["results"])
    assert any(
        "scripts/workflow/check_agent_control_plane_pin.py" in command for command in commands
    )


def test_run_quality_gates_blocks_on_broken_wmf_backlog(tmp_path: Path) -> None:
    (tmp_path / "config" / "quality").mkdir(parents=True)
    (tmp_path / "config" / "tasks").mkdir(parents=True)
    (tmp_path / "docs" / "11_admin").mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "scripts").mkdir()

    shutil.copyfile(
        Path("scripts/validate_work_items.py"),
        tmp_path / "scripts" / "validate_work_items.py",
    )
    (tmp_path / "config" / "quality" / "manifest.yaml").write_text(
        """
version: 1
repo:
  exclude_prefixes: []
  python_targets: []
tools:
  wmf_validator:
    enabled: true
    mode: blocking
    scopes: ["changed", "repo"]
    autofix_allowed: false
    failure_class: wmf_validation_error
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "config" / "tasks" / "backlog.yaml").write_text(
        """
schema_version: backlog.v1
tasks:
- id: WI-2026-001
  title: Broken WMF item
  priority: P1
  risk: low
  status: BROKEN
  task_type: build
  objective_ref: test
  created_at: test-created-at
  workstream: test
  plan_mode: none
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "artifacts" / "workstreams.yaml").write_text(
        "test:\n  human_name: Test\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "11_admin" / "BACKLOG.md").write_text(
        "<!-- DERIVED VIEW -->\n",
        encoding="utf-8",
    )

    result = run_quality_gates(tmp_path, ["config/tasks/backlog.yaml"], scope="changed")

    assert result["passed"] is False
    assert result["commands_run"] == [
        "python3 scripts/validate_work_items.py --check --repo-root ."
    ]
    assert any(
        row["tool"] == "wmf_validator"
        and row["mode"] == "blocking"
        and not row["passed"]
        and "WM003_INVALID_STATUS" in str(row["details"])
        for row in result["results"]
    )


def test_run_quality_gates_missing_blocking_tool_is_advisory(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:2] == ["ruff", "check"] or cmd[:2] == ["ruff", "format"]:
            raise FileNotFoundError("ruff")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
    assert result["passed"] is True
    assert any(
        row["tool"] == "ruff_check"
        and row["mode"] == "advisory"
        and row["waiver_reason"] == "tool_unavailable_locally"
        for row in result["results"]
    )


def test_run_quality_gates_missing_blocking_tool_stays_blocking_in_repo_scope(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:2] == ["ruff", "check"] or cmd[:2] == ["ruff", "format"]:
            raise FileNotFoundError("ruff")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="repo")
    assert result["passed"] is False
    assert any(
        row["tool"] == "ruff_check" and row["mode"] == "blocking" for row in result["results"]
    )


def test_run_quality_gates_waiver_downgrades_blocking_failure(monkeypatch) -> None:
    manifest = {
        "repo": {"python_targets": ["runtime"]},
        "tools": {
            "ruff_check": {
                "enabled": True,
                "mode": "blocking",
                "scopes": ["changed"],
                "autofix_allowed": True,
                "failure_class": "ruff_error",
            }
        },
        "waivers": [
            {
                "tool": "ruff_check",
                "failure_class": "ruff_error",
                "paths": ["runtime/tools/"],
                "reason": "temporary waiver",
            }
        ],
    }

    def fake_run(*args, **kwargs):
        cmd = args[0]
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr="unused import"
        )

    monkeypatch.setattr(
        "runtime.tools.workflow_pack.load_quality_manifest", lambda repo_root: manifest
    )
    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_quality_gates(Path("."), ["runtime/tools/workflow_pack.py"], scope="changed")
    assert result["passed"] is True
    assert any(
        row["tool"] == "ruff_check"
        and row["mode"] == "advisory"
        and row["waiver_reason"] == "temporary waiver"
        for row in result["results"]
    )


def test_doctor_quality_tools_reports_presence(monkeypatch) -> None:
    def fake_which(name: str) -> str | None:
        return None if name in {"ruff", "mypy"} else f"/usr/bin/{name}"

    monkeypatch.setattr("runtime.tools.workflow_pack.shutil.which", fake_which)
    result = doctor_quality_tools(Path("."))
    assert result["passed"] is False
    assert any(row["tool"] == "ruff_check" and row["present"] is False for row in result["results"])


def test_quality_gate_main_check_json(monkeypatch, capsys) -> None:
    payload = {
        "passed": True,
        "scope": "changed",
        "summary": "Quality gate ran 1 tool(s); 0 blocking failure(s), 0 advisory failure(s).",
        "commands_run": ["ruff check runtime/tools/workflow_pack.py"],
        "files_checked": ["runtime/tools/workflow_pack.py"],
        "results": [],
        "auto_fixed": False,
    }

    monkeypatch.setattr(
        "scripts.workflow.quality_gate.load_quality_manifest", lambda repo_root: {"tools": {}}
    )
    monkeypatch.setattr(
        "scripts.workflow.quality_gate.run_quality_gates", lambda *args, **kwargs: payload
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["quality_gate.py", "check", "--json", "--changed-file", "runtime/tools/workflow_pack.py"],
    )

    rc = quality_gate.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out)["passed"] is True
