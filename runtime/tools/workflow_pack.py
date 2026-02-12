"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


ACTIVE_WORK_RELATIVE_PATH = Path(".context/active_work.yaml")


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build_active_work_payload(
    *,
    branch: str,
    latest_commits: Sequence[str],
    focus: Sequence[str],
    tests_targeted: Sequence[str],
    findings_open: Sequence[dict[str, str]],
) -> dict:
    """Build normalized active-work payload."""
    normalized_findings = []
    for finding in findings_open:
        finding_id = str(finding.get("id", "")).strip()
        severity = str(finding.get("severity", "")).strip().lower()
        status = str(finding.get("status", "")).strip().lower()
        if not finding_id or not severity or not status:
            continue
        normalized_findings.append(
            {"id": finding_id, "severity": severity, "status": status}
        )

    return {
        "version": "1.0",
        "branch": branch.strip() or "unknown",
        "latest_commits": _unique_ordered(latest_commits),
        "focus": _unique_ordered(focus),
        "tests_targeted": _unique_ordered(tests_targeted),
        "findings_open": normalized_findings,
    }


def write_active_work(repo_root: Path, payload: dict) -> Path:
    """Write .context/active_work.yaml deterministically."""
    output_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def read_active_work(repo_root: Path) -> dict:
    """Read .context/active_work.yaml, returning a normalized fallback when absent."""
    input_path = Path(repo_root) / ACTIVE_WORK_RELATIVE_PATH
    if not input_path.exists():
        return build_active_work_payload(
            branch="unknown",
            latest_commits=[],
            focus=[],
            tests_targeted=[],
            findings_open=[],
        )
    try:
        loaded = json.loads(input_path.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    return build_active_work_payload(
        branch=str(loaded.get("branch", "unknown")),
        latest_commits=loaded.get("latest_commits") or [],
        focus=loaded.get("focus") or [],
        tests_targeted=loaded.get("tests_targeted") or [],
        findings_open=loaded.get("findings_open") or [],
    )


def _matches(file_path: str, prefixes: Sequence[str]) -> bool:
    return any(file_path == prefix or file_path.startswith(prefix) for prefix in prefixes)


def route_targeted_tests(changed_files: Sequence[str]) -> list[str]:
    """Map changed files to targeted test commands."""
    files = _unique_ordered(changed_files)

    routed: list[str] = []

    def add(command: str) -> None:
        if command not in routed:
            routed.append(command)

    for file_path in files:
        if _matches(
            file_path,
            (
                "runtime/orchestration/openclaw_bridge.py",
                "runtime/tests/orchestration/test_openclaw_bridge.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/test_openclaw_bridge.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/orchestration/missions/autonomous_build_cycle.py",
                "runtime/tests/orchestration/missions/test_autonomous_loop.py",
            ),
        ):
            add("pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py")
            continue

        if _matches(
            file_path,
            (
                "runtime/agents/api.py",
                "runtime/agents/opencode_client.py",
                "runtime/tests/test_agent_api_usage_plumbing.py",
                "tests/test_agent_api.py",
            ),
        ):
            add(
                "pytest -q runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py"
            )
            continue

        if _matches(
            file_path,
            (
                "runtime/tools/workflow_pack.py",
                "runtime/tests/test_workflow_pack.py",
                "scripts/workflow/",
            ),
        ):
            add("pytest -q runtime/tests/test_workflow_pack.py")
            continue

    if not routed:
        routed.append("pytest -q runtime/tests")
    return routed


def discover_changed_files(repo_root: Path) -> list[str]:
    """Discover changed files with staged-first precedence."""
    repo = Path(repo_root)
    probes = [
        ["git", "-C", str(repo), "diff", "--name-only", "--cached"],
        ["git", "-C", str(repo), "diff", "--name-only"],
        ["git", "-C", str(repo), "diff", "--name-only", "HEAD~1..HEAD"],
    ]
    for cmd in probes:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if files:
            return _unique_ordered(files)
    return []
