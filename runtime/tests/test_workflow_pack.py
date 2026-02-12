from __future__ import annotations

from pathlib import Path

from runtime.tools.workflow_pack import (
    build_active_work_payload,
    read_active_work,
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

