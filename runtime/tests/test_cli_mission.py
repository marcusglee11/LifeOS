from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

import pytest

from runtime.cli import cmd_mission_list, cmd_mission_run, cmd_run_mission
from runtime.orchestration.orchestrator import OrchestrationResult
from runtime.validation.acceptor import accept
from runtime.validation.core import JobSpec, RetryCaps
from runtime.validation.reporting import sha256_file, write_acceptance_token


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

    config_dir = repo / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "backlog.yaml").write_text(
        """
schema_version: "1.0"
tasks:
  - id: TASK001
    description: Echo mission backlog task
    priority: P1
    context_hints: []
    constraints: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    _git(repo, "add", ".gitignore", "tracked.txt", "config/backlog.yaml")
    _git(repo, "commit", "-m", "init")
    return repo


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    return _setup_repo(tmp_path)


def _mission_run_args(params: str = "{}") -> argparse.Namespace:
    return argparse.Namespace(
        mission_type="echo",
        param=None,
        params=params,
        json=True,
    )


def _run_mission_args() -> argparse.Namespace:
    return argparse.Namespace(
        from_backlog="TASK001",
        backlog="config/backlog.yaml",
        mission_type="echo",
        json=True,
    )


def _assert_success_payload(payload: dict) -> None:
    required = (
        "acceptance_token_path",
        "acceptance_record_path",
        "acceptance_token_sha256",
        "evidence_manifest_sha256",
    )
    for field in required:
        assert field in payload
        assert isinstance(payload[field], str)
        assert payload[field]

    assert Path(payload["acceptance_token_path"]).exists()
    assert Path(payload["acceptance_record_path"]).exists()


def _fake_orchestrator_run(repo_root: Path, corruption: str):
    def _run(
        self,
        *,
        mission_kind: str,
        evidence_tier: str,
        agent_runner,
        run_id: str | None = None,
        gate_pipeline_version: str = "v2.1a-p0",
        retry_caps=None,
        receipt_required: bool = False,
    ) -> OrchestrationResult:
        _ = evidence_tier
        _ = retry_caps
        _ = receipt_required
        run_id = run_id or "fake-run"
        attempt_id = "attempt-0001"

        attempt_dir = repo_root / "artifacts" / "validation_runs" / run_id / attempt_id
        attempt_dir.mkdir(parents=True, exist_ok=True)

        job_spec = JobSpec(
            schema_version="job_spec_v1",
            run_id=run_id,
            mission_kind=mission_kind,
            evidence_tier="light",
            gate_pipeline_version=gate_pipeline_version,
            retry_caps=RetryCaps(2, 3, 2),
        )
        agent_runner(attempt_dir, job_spec)

        manifest_path = attempt_dir / "evidence" / "evidence_manifest.json"
        token_path = attempt_dir / "acceptance_token.json"

        token_payload = {
            "schema_version": "acceptance_token_v1",
            "pass": True,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "attempt_index": 1,
            "gate_pipeline_version": gate_pipeline_version,
            "evidence_manifest_sha256": sha256_file(manifest_path),
            "receipt_sha256": None,
            "created_at": "2026-02-10T00:00:00+00:00",
            "provenance": {
                "minted_by": "runtime.tests.test_cli_mission",
                "attempt_dir": str(attempt_dir),
                "manifest_path": str(manifest_path),
                "receipt_path": str(attempt_dir / "receipt.json"),
            },
        }
        write_acceptance_token(token_path, token_payload)
        accept(token_path)

        record_path = attempt_dir / "acceptance_record.json"

        if corruption == "missing_record":
            record_path.unlink()
        elif corruption == "missing_token":
            token_path.unlink()
        elif corruption == "tampered_token":
            tampered_payload = json.loads(token_path.read_text(encoding="utf-8"))
            tampered_payload["pass"] = False
            token_path.write_text(json.dumps(tampered_payload, sort_keys=True), encoding="utf-8")
        elif corruption == "missing_record_path":
            return OrchestrationResult(
                success=True,
                run_id=run_id,
                attempt_id=attempt_id,
                attempt_index=1,
                message="Accepted",
                acceptance_token_path=str(token_path),
                acceptance_record_path=None,
            )

        return OrchestrationResult(
            success=True,
            run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=1,
            message="Accepted",
            acceptance_token_path=str(token_path),
            acceptance_record_path=str(record_path),
        )

    return _run


class TestMissionCLI:
    def test_mission_list_returns_sorted_json(self, capsys):
        ret = cmd_mission_list(None)
        assert ret == 0

        output = json.loads(capsys.readouterr().out)
        assert isinstance(output, list)
        assert output == sorted(output)
        assert "echo" in output

    def test_mission_run_json_success_includes_acceptance_proof(self, temp_repo: Path, capsys):
        ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        assert ret == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is True
        assert payload["final_state"]["mission_result"]["success"] is True
        _assert_success_payload(payload)

    def test_run_mission_json_success_includes_acceptance_proof(self, temp_repo: Path, capsys):
        ret = cmd_run_mission(_run_mission_args(), temp_repo)
        assert ret == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is True
        assert payload["final_state"]["mission_result"]["success"] is True
        _assert_success_payload(payload)

    @pytest.mark.parametrize("command", ["mission_run", "run_mission"])
    @pytest.mark.parametrize("corruption", ["missing_record", "missing_token", "tampered_token"])
    def test_commands_fail_closed_when_proof_invalid(
        self,
        temp_repo: Path,
        capsys,
        monkeypatch: pytest.MonkeyPatch,
        command: str,
        corruption: str,
    ):
        monkeypatch.setattr(
            "runtime.cli.ValidationOrchestrator.run",
            _fake_orchestrator_run(temp_repo, corruption),
        )

        if command == "mission_run":
            ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        else:
            ret = cmd_run_mission(_run_mission_args(), temp_repo)

        assert ret == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is False

    @pytest.mark.parametrize("command", ["mission_run", "run_mission"])
    def test_commands_fail_closed_without_acceptance_record_path(
        self,
        temp_repo: Path,
        capsys,
        monkeypatch: pytest.MonkeyPatch,
        command: str,
    ):
        monkeypatch.setattr(
            "runtime.cli.ValidationOrchestrator.run",
            _fake_orchestrator_run(temp_repo, "missing_record_path"),
        )

        if command == "mission_run":
            ret = cmd_mission_run(_mission_run_args('{"message":"hello"}'), temp_repo)
        else:
            ret = cmd_run_mission(_run_mission_args(), temp_repo)

        assert ret == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["success"] is False
        assert payload.get("acceptance_record_path") is None
