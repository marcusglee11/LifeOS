from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    check_doc_stewardship,
    cleanup_after_merge,
    read_active_work,
    run_closure_tests,
    route_targeted_tests,
    write_active_work,
)


def test_active_work_roundtrip(tmp_path: Path) -> None:
    payload = build_active_work_payload(
        branch="feature/workflow-pack",
        latest_commits=["abc123 add router", "def456 add skills"],
        focus=["W4-T01", "W5-T04"],
        tests_targeted=["pytest -q runtime/tests/test_workflow_pack.py"],
        findings_open=[{"id": "M1", "severity": "moderate", "status": "open"}],
    )

    output = write_active_work(tmp_path, payload)
    assert output == tmp_path / ".context" / "active_work.yaml"

    loaded = read_active_work(tmp_path)
    assert loaded["version"] == "1.0"
    assert loaded["branch"] == "feature/workflow-pack"
    assert loaded["focus"] == ["W4-T01", "W5-T04"]
    assert loaded["findings_open"] == [{"id": "M1", "severity": "moderate", "status": "open"}]


def test_route_targeted_tests_routes_known_files() -> None:
    changed = [
        "runtime/orchestration/openclaw_bridge.py",
        "runtime/orchestration/missions/autonomous_build_cycle.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/orchestration/test_openclaw_bridge.py",
        "pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py",
    ]


def test_route_targeted_tests_deduplicates() -> None:
    changed = [
        "runtime/agents/api.py",
        "tests/test_agent_api.py",
        "runtime/agents/opencode_client.py",
    ]
    commands = route_targeted_tests(changed)
    assert commands == [
        "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py",
    ]


def test_route_targeted_tests_fallback() -> None:
    commands = route_targeted_tests(["docs/11_admin/BACKLOG.md"])
    assert commands == ["pytest -q runtime/tests"]


def test_run_closure_tests_passes_on_zero_returncode(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is True
    assert result["commands_run"] == ["pytest -q runtime/tests/test_workflow_pack.py"]


def test_run_closure_tests_fails_on_nonzero(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="failed",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = run_closure_tests(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["passed"] is False
    assert result["failures"]


def test_check_doc_stewardship_skips_when_no_docs(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess should not be called")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fail_if_called)
    result = check_doc_stewardship(Path("."), ["runtime/tools/workflow_pack.py"])
    assert result["required"] is False
    assert result["passed"] is True


def test_check_doc_stewardship_runs_when_docs_changed(monkeypatch) -> None:
    payload = {
        "passed": True,
        "docs_modified": True,
        "docs_files": ["docs/INDEX.md"],
        "errors": [],
    }

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = check_doc_stewardship(Path("."), ["docs/INDEX.md"])
    assert result["required"] is True
    assert result["passed"] is True
    assert result["docs_files"] == ["docs/INDEX.md"]


def test_cleanup_after_merge_clears_context(tmp_path: Path, monkeypatch) -> None:
    context_path = tmp_path / ".context" / "active_work.yaml"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text("{}", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("runtime.tools.workflow_pack.subprocess.run", fake_run)
    result = cleanup_after_merge(tmp_path, "build/feature", clear_context=True)
    assert result["branch_deleted"] is True
    assert result["context_cleared"] is True
    assert not context_path.exists()
