"""Workflow pack helpers for low-friction multi-agent handoffs."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
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


def run_closure_tests(repo_root: Path, changed_files: Sequence[str]) -> dict:
    """Run targeted closure tests derived from changed files."""
    commands = route_targeted_tests(changed_files)
    commands_run: list[str] = []
    failures: list[str] = []
    passed_count = 0

    for command in commands:
        commands_run.append(command)
        proc = subprocess.run(
            shlex.split(command),
            check=False,
            cwd=Path(repo_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            passed_count += 1
            continue
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        details = stderr or stdout or f"exit code {proc.returncode}"
        failures.append(f"{command}: {details}")

    passed = not failures
    summary = f"{passed_count}/{len(commands_run)} targeted test command(s) passed."
    if failures:
        summary += f" Failures: {len(failures)}."

    return {
        "passed": passed,
        "commands_run": commands_run,
        "summary": summary,
        "failures": failures,
    }


def check_doc_stewardship(
    repo_root: Path,
    changed_files: Sequence[str],
    auto_fix: bool = True,
) -> dict:
    """Run doc stewardship gate only when docs paths are present."""
    docs_changed = any(path == "docs" or path.startswith("docs/") for path in changed_files)
    if not docs_changed:
        return {
            "required": False,
            "passed": True,
            "errors": [],
            "auto_fixed": False,
        }

    cmd = [sys.executable, "scripts/claude_doc_stewardship_gate.py"]
    if auto_fix:
        cmd.append("--auto-fix")

    proc = subprocess.run(
        cmd,
        check=False,
        cwd=Path(repo_root),
        capture_output=True,
        text=True,
    )

    payload: dict = {}
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            loaded = json.loads(stdout)
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded

    errors = []
    for item in payload.get("errors", []):
        text = str(item).strip()
        if text:
            errors.append(text)
    if not payload and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        errors.append(stderr or "doc stewardship gate returned non-zero without JSON output")

    passed = bool(payload.get("passed")) and proc.returncode == 0
    auto_fixed = bool(payload.get("auto_fix_applied") or payload.get("auto_fix_success"))

    return {
        "required": True,
        "passed": passed,
        "errors": errors,
        "auto_fixed": auto_fixed,
        "docs_files": payload.get("docs_files", []),
    }


def merge_to_main(repo_root: Path, branch: str) -> dict:
    """Merge a feature branch into main using squash merge."""
    source_branch = branch.strip()
    if not source_branch:
        return {"success": False, "merge_sha": None, "errors": ["source branch is empty"]}
    if source_branch in {"main", "master"}:
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"cannot merge protected branch '{source_branch}'"],
        }

    repo = Path(repo_root)
    errors: list[str] = []

    safety = subprocess.run(
        [sys.executable, "scripts/repo_safety_gate.py", "--operation", "merge"],
        check=False,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if safety.returncode != 0:
        details = (safety.stderr or "").strip() or (safety.stdout or "").strip()
        return {
            "success": False,
            "merge_sha": None,
            "errors": [f"safety gate blocked merge: {details or 'unknown failure'}"],
        }

    steps = [
        ("checkout main", ["git", "-C", str(repo), "checkout", "main"]),
        ("pull --ff-only", ["git", "-C", str(repo), "pull", "--ff-only"]),
        ("squash merge", ["git", "-C", str(repo), "merge", "--squash", source_branch]),
        (
            "commit squash merge",
            ["git", "-C", str(repo), "commit", "-m", f"feat: Merge {source_branch} (squashed)"],
        ),
    ]

    for label, cmd in steps:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            continue
        details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
        errors.append(f"{label} failed: {details or f'exit code {proc.returncode}'}")
        subprocess.run(
            ["git", "-C", str(repo), "checkout", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        return {"success": False, "merge_sha": None, "errors": errors}

    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    merge_sha = head.stdout.strip() if head.returncode == 0 else None
    if not merge_sha:
        errors.append("failed to resolve merge commit SHA")
        return {"success": False, "merge_sha": None, "errors": errors}

    return {"success": True, "merge_sha": merge_sha, "errors": []}


def cleanup_after_merge(repo_root: Path, branch: str, clear_context: bool = True) -> dict:
    """Cleanup local branch and active context artifact after merge."""
    repo = Path(repo_root)
    source_branch = branch.strip()

    errors: list[str] = []
    branch_deleted = False
    if source_branch and source_branch not in {"main", "master"}:
        proc = subprocess.run(
            ["git", "-C", str(repo), "branch", "-d", source_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            branch_deleted = True
        else:
            details = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            errors.append(
                f"failed to delete local branch '{source_branch}': {details or f'exit code {proc.returncode}'}"
            )

    context_path = repo / ACTIVE_WORK_RELATIVE_PATH
    context_cleared = False
    if clear_context:
        try:
            if context_path.exists():
                context_path.unlink()
            context_cleared = not context_path.exists()
        except OSError as exc:
            errors.append(f"failed to clear {ACTIVE_WORK_RELATIVE_PATH}: {exc}")

    return {
        "branch_deleted": branch_deleted,
        "context_cleared": context_cleared,
        "errors": errors,
    }
