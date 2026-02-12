"""Tests for scripts/workflow/closure_gate.py run_gate function."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.workflow.closure_gate import run_gate


def _make_fake_run(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Return a fake subprocess.run that returns fixed results."""
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0], returncode=returncode, stdout=stdout, stderr=stderr,
        )
    return fake_run


def test_all_gates_pass(monkeypatch) -> None:
    """When tests pass and no docs changed, verdict is passed."""
    monkeypatch.setattr(
        "runtime.tools.workflow_pack.subprocess.run",
        _make_fake_run(returncode=0, stdout="ok"),
    )
    verdict = run_gate(Path("."))
    assert verdict["passed"] is True
    assert verdict["gate"] == "all"
    assert "skipped" in verdict["summary"].lower()


def test_test_gate_fails(monkeypatch) -> None:
    """When targeted tests fail, gate is 'tests'."""

    def sequenced_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)

        # git diff probes for discover_changed_files
        if "git" in cmd_str and "diff" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="runtime/engine.py\n", stderr="",
            )

        # Test command fails
        if "pytest" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="FAILED test_foo.py",
            )

        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(
        "runtime.tools.workflow_pack.subprocess.run", sequenced_run,
    )
    verdict = run_gate(Path("."))
    assert verdict["passed"] is False
    assert verdict["gate"] == "tests"


def test_doc_gate_fails(monkeypatch) -> None:
    """When doc stewardship fails, gate is 'doc_stewardship'."""
    call_count = {"n": 0}

    def sequenced_run(*args, **kwargs):
        call_count["n"] += 1
        cmd = args[0] if args else kwargs.get("args", [])
        cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)

        # discover_changed_files: return docs path on first git diff probe
        if "git" in cmd_str and "diff" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="docs/INDEX.md\n", stderr="",
            )

        # Test commands pass
        if "pytest" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="ok", stderr="",
            )

        # Doc stewardship gate fails
        if "doc_stewardship" in cmd_str or "claude_doc_stewardship" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout='{"passed": false, "errors": ["INDEX.md out of date"]}',
                stderr="",
            )

        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(
        "runtime.tools.workflow_pack.subprocess.run", sequenced_run,
    )
    verdict = run_gate(Path("."))
    assert verdict["passed"] is False
    assert verdict["gate"] == "doc_stewardship"


def test_no_docs_changed_summary_mentions_skipped(monkeypatch) -> None:
    """When no docs are in changed files, summary mentions skipped."""
    call_count = {"n": 0}

    def sequenced_run(*args, **kwargs):
        call_count["n"] += 1
        cmd = args[0] if args else kwargs.get("args", [])
        cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)

        # discover_changed_files: return non-docs path
        if "git" in cmd_str and "diff" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="runtime/engine.py\n", stderr="",
            )

        # All test commands pass
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="ok", stderr="",
        )

    monkeypatch.setattr(
        "runtime.tools.workflow_pack.subprocess.run", sequenced_run,
    )
    verdict = run_gate(Path("."))
    assert verdict["passed"] is True
    assert "skipped" in verdict["summary"].lower()
