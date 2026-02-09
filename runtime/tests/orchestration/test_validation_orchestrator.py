from __future__ import annotations

from pathlib import Path
import subprocess

from runtime.orchestration.orchestrator import ValidationOrchestrator
from runtime.validation.core import JobSpec, RetryCaps
from runtime.validation.evidence import compute_manifest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".gitignore").write_text("artifacts/validation_runs/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _light_agent_runner(attempt_dir: Path, _job_spec: JobSpec) -> None:
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
    (evidence_root / "exitcode.txt").write_text("0\n", encoding="utf-8")
    (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
    compute_manifest(evidence_root)


def test_orchestrator_success_path(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    orchestrator = ValidationOrchestrator(workspace_root=repo)

    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_light_agent_runner,
        run_id="run-success",
        retry_caps=RetryCaps(2, 3, 2),
    )

    assert result.success
    assert result.acceptance_token_path is not None
    assert result.acceptance_record_path is not None


def test_orchestrator_preflight_failure_is_terminal(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    calls = {"count": 0}

    def _agent_never_called(attempt_dir: Path, job_spec: JobSpec) -> None:
        _ = attempt_dir
        _ = job_spec
        calls["count"] += 1

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_agent_never_called,
        run_id="run-dirty-preflight",
        retry_caps=RetryCaps(2, 3, 2),
    )

    assert not result.success
    assert result.attempt_index == 1
    assert calls["count"] == 0
    assert result.validator_report_path is not None
    assert "validator_report.json" in result.validator_report_path


def test_orchestrator_owns_retry_loop(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    calls = {"count": 0}

    def _flaky_agent(attempt_dir: Path, _job_spec: JobSpec) -> None:
        calls["count"] += 1
        evidence_root = attempt_dir / "evidence"
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / "meta.json").write_text("{}\n", encoding="utf-8")
        (evidence_root / "commands.jsonl").write_text('{"cmd":"agent"}\n', encoding="utf-8")
        if calls["count"] >= 2:
            (evidence_root / "exitcode.txt").write_text("0\n", encoding="utf-8")
        compute_manifest(evidence_root)

    orchestrator = ValidationOrchestrator(workspace_root=repo)
    result = orchestrator.run(
        mission_kind="build_with_validation",
        evidence_tier="light",
        agent_runner=_flaky_agent,
        run_id="run-retry",
        retry_caps=RetryCaps(3, 3, 2),
    )

    assert result.success
    assert result.attempt_index == 2
    assert calls["count"] == 2
