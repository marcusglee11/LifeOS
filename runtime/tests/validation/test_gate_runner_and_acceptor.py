from __future__ import annotations

from pathlib import Path
import json
import subprocess

import pytest

from runtime.validation.acceptor import AcceptanceTokenError, accept
from runtime.validation.core import AttemptContext, JobSpec, RetryCaps
from runtime.validation.evidence import compute_manifest
from runtime.validation.gate_runner import GateRunner
from runtime.validation.reporting import write_json_atomic


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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_light_evidence(evidence_root: Path) -> None:
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "exitcode.txt", "0\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"agent\"}\n")
    compute_manifest(evidence_root)


def _attempt_context() -> AttemptContext:
    return AttemptContext(
        run_id="run-1",
        attempt_id="attempt-0001",
        attempt_index=1,
        max_attempts_per_gate_per_run=2,
        max_total_attempts_per_run=3,
        max_consecutive_same_failure_code=2,
    )


def _job_spec(run_id: str = "run-1") -> JobSpec:
    return JobSpec(
        schema_version="job_spec_v1",
        run_id=run_id,
        mission_kind="build_with_validation",
        evidence_tier="light",
        gate_pipeline_version="v2.1a-p0",
        retry_caps=RetryCaps(2, 3, 2),
    )


def test_gate_runner_success_mints_token_and_acceptor_records_hash(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    _write_light_evidence(evidence_root)

    gate_runner = GateRunner()
    pre = gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    )
    assert pre.success

    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert post.success
    assert post.token_path is not None

    token_payload = json.loads(post.token_path.read_text(encoding="utf-8"))
    assert "token_sha256" not in token_payload

    record = accept(post.token_path)
    assert "acceptance_token_sha256" in record


def test_acceptor_rejects_invalid_token(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    _write_light_evidence(evidence_root)

    gate_runner = GateRunner()
    assert gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    ).success
    post = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert post.success
    assert post.token_path is not None

    payload = json.loads(post.token_path.read_text(encoding="utf-8"))
    payload["token_sha256"] = "illegal"
    write_json_atomic(post.token_path, payload)

    with pytest.raises(AcceptanceTokenError) as exc:
        accept(post.token_path)

    assert exc.value.code == "ACCEPTANCE_TOKEN_INVALID"


def test_validator_report_is_deterministic_for_same_failure(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    attempt_dir = repo / "artifacts" / "validation_runs" / "run-1" / "attempt-0001"
    evidence_root = attempt_dir / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    write_json_atomic(attempt_dir / "job_spec.json", _job_spec().to_dict())
    # Missing exitcode.txt intentionally; manifest includes only files present.
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"agent\"}\n")
    compute_manifest(evidence_root)

    gate_runner = GateRunner()
    assert gate_runner.run_preflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
    ).success

    first = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not first.success
    assert first.report_path is not None
    first_bytes = first.report_path.read_bytes()

    second = gate_runner.run_postflight(
        workspace_root=repo,
        attempt_dir=attempt_dir,
        attempt_context=_attempt_context(),
        receipt_required=False,
    )
    assert not second.success
    assert second.report_path is not None
    second_bytes = second.report_path.read_bytes()

    assert first_bytes == second_bytes
