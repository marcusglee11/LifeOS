"""Tests for sprint-close emission helpers and wrapper guardrails."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).parents[2]
_EMIT_SCRIPT = _REPO_ROOT / "scripts" / "workflow" / "emit_sprint_close_packet.py"
_CODEX_WRAPPER = _REPO_ROOT / "scripts" / "workflow" / "dispatch_codex.sh"
_OPENCODE_WRAPPER = _REPO_ROOT / "scripts" / "workflow" / "dispatch_opencode.sh"


def _run_emit(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(_EMIT_SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--python-root",
            str(_REPO_ROOT),
            "--order-id",
            "ORD-T-030-20260406T120000Z",
            "--task-ref",
            "T-030",
            "--agent",
            "codex",
            "--outcome",
            "success",
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _write_backlog(repo_root: Path, *task_ids: str) -> None:
    backlog = repo_root / "config" / "tasks" / "backlog.yaml"
    backlog.parent.mkdir(parents=True, exist_ok=True)
    tasks = [{"id": task_id} for task_id in task_ids]
    backlog.write_text(yaml.dump({"schema_version": "backlog.v1", "tasks": tasks}), encoding="utf-8")


def _run_wrapper(
    script: Path,
    tmp_path: Path,
    task: str,
    *,
    provider_exit: str = "0",
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "LIFEOS_DISPATCH_REPO_ROOT": str(tmp_path),
            "LIFEOS_DISPATCH_PYTHON_ROOT": str(_REPO_ROOT),
            "LIFEOS_DISPATCH_WORKTREE_PATH": str(worktree_path),
            "LIFEOS_DISPATCH_PROVIDER_EXIT_CODE": provider_exit,
        }
    )
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["/bin/bash", str(script), "topic", task],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def test_emit_sprint_close_packet_writes_packet(tmp_path: Path) -> None:
    result = _run_emit(tmp_path, "--sync-check-result", "skipped")
    assert result.returncode == 0, result.stderr

    packet_path = tmp_path / "artifacts" / "dispatch" / "closures" / "SC-ORD-T-030-20260406T120000Z.yaml"
    assert packet_path.is_file()
    payload = yaml.safe_load(packet_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "sprint_close_packet.v1"
    assert payload["task_ref"] == "T-030"


def test_emit_sprint_close_packet_rejects_invalid_agent(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_EMIT_SCRIPT),
            "--repo-root",
            str(tmp_path),
            "--python-root",
            str(_REPO_ROOT),
            "--order-id",
            "ORD-T-030-20260406T120000Z",
            "--task-ref",
            "T-030",
            "--agent",
            "invalid",
            "--outcome",
            "success",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_dispatch_codex_wrapper_rejects_missing_task_id(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030")
    result = _run_wrapper(_CODEX_WRAPPER, tmp_path, "Build the backlog module per plan")
    assert result.returncode == 5
    assert "exactly one backlog task ID" in result.stderr


def test_dispatch_codex_wrapper_rejects_multiple_task_ids(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030", "T-031")
    result = _run_wrapper(_CODEX_WRAPPER, tmp_path, "Handle T-030 and T-031 together")
    assert result.returncode == 5


def test_dispatch_codex_wrapper_rejects_nonexistent_task_id(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030")
    result = _run_wrapper(_CODEX_WRAPPER, tmp_path, "Implement T-999 now")
    assert result.returncode == 5
    assert "was not found" in result.stderr


def test_dispatch_codex_wrapper_emits_packet_and_receipt(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030")
    result = _run_wrapper(_CODEX_WRAPPER, tmp_path, "Implement T-030 now")
    assert result.returncode == 0, result.stderr

    closures = list((tmp_path / "artifacts" / "dispatch" / "closures").glob("SC-*.yaml"))
    assert len(closures) == 1

    index_file = next((tmp_path / "artifacts" / "receipts").rglob("index.json"))
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert index["receipts"][0]["exit_status"] == 0


def test_dispatch_opencode_wrapper_emits_packet(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030")
    result = _run_wrapper(_OPENCODE_WRAPPER, tmp_path, "Implement T-030 now")
    assert result.returncode == 0, result.stderr
    closures = list((tmp_path / "artifacts" / "dispatch" / "closures").glob("SC-*.yaml"))
    assert len(closures) == 1


def test_dispatch_opencode_wrapper_runs_in_worktree(tmp_path: Path) -> None:
    _write_backlog(tmp_path, "T-030")
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(parents=True, exist_ok=True)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "cwd.txt"
    fake_opencode = fake_bin / "opencode"
    fake_opencode.write_text(
        "#!/usr/bin/env bash\npwd > \"$FAKE_OPENCODE_MARKER\"\n",
        encoding="utf-8",
    )
    fake_opencode.chmod(0o755)

    result = _run_wrapper(
        _OPENCODE_WRAPPER,
        tmp_path,
        "Implement T-030 now",
        provider_exit="",
        env_overrides={
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "FAKE_OPENCODE_MARKER": str(marker),
        },
    )
    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8").strip() == str(worktree_path)
