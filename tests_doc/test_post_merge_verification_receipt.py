from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.wiki import post_merge_verification_receipt as receipt


def test_classify_failure_distinguishes_drift_baseline_and_tooling() -> None:
    assert receipt.classify_failure("wiki-lint found stale source_commit_max") == "new_drift"
    assert receipt.classify_failure("pre-existing markdown baseline noise") == "baseline_noise"
    assert (
        receipt.classify_failure("ModuleNotFoundError: No module named doc_steward")
        == "tooling_failure"
    )


def test_summary_redacts_sensitive_command_output() -> None:
    summary = receipt._summarise(
        "api_key=abc123 ghp_abcdefghijklmnopqrstuvwxyz123456",
        "password: hunter2\nAuthorization: Bearer abcdefghijklmnopqrstuvwxyz",
    )

    assert "abc123" not in summary
    assert "hunter2" not in summary
    assert "ghp_" not in summary
    assert "Bearer abcdef" not in summary
    assert "[REDACTED]" in summary


def test_emit_yaml_matches_required_receipt_shape() -> None:
    rendered = receipt.emit_yaml(
        {
            "repo": "marcusglee11/LifeOS",
            "base_ref": "origin/main",
            "verified_commit": "abc123",
            "commands": ["python3 scripts/wiki/check_derived_outputs.py"],
            "results": [
                {
                    "command": "python3 scripts/wiki/check_derived_outputs.py",
                    "status": "pass",
                    "summary": "ok",
                }
            ],
            "dirty_worktree_after_verification": False,
            "follow_up_issues_created": [],
            "completion_claim": "conductor_verified",
        }
    )

    assert "repo: marcusglee11/LifeOS" in rendered
    assert "base_ref: origin/main" in rendered
    assert "verified_commit: abc123" in rendered
    assert "dirty_worktree_after_verification: false" in rendered
    assert "follow_up_issues_created: []" in rendered
    assert "completion_claim: conductor_verified" in rendered


def test_build_receipt_fetches_and_runs_commands_in_clean_origin_main_worktree(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[tuple[str, ...] | str, Path]] = []
    verify_root_holder: dict[str, Path] = {}

    def fake_run(cmd, cwd: Path):
        calls.append((tuple(cmd) if isinstance(cmd, list) else cmd, cwd))
        if isinstance(cmd, list) and cmd[:3] == ["git", "rev-parse", "origin/main"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            verify_root_holder["path"] = Path(cmd[-2])
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if isinstance(cmd, list) and cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(receipt, "_run", fake_run)
    monkeypatch.setattr(receipt.tempfile, "mkdtemp", lambda prefix: str(tmp_path / "verify"))
    monkeypatch.setattr(receipt.shutil, "rmtree", lambda *args, **kwargs: None)

    result, kept = receipt.build_receipt(Path("/repo"), ["python3 smoke.py"])

    assert kept is None
    assert result["base_ref"] == "origin/main"
    assert result["verified_commit"] == "deadbeef"
    assert result["completion_claim"] == "conductor_verified"
    assert result["dirty_worktree_after_verification"] is False
    assert (("git", "fetch", "origin", "main", "--prune"), Path("/repo")) in calls
    assert ("python3 smoke.py", verify_root_holder["path"]) in calls
    assert any(
        call[0][:3] == ("git", "worktree", "remove") for call in calls if isinstance(call[0], tuple)
    )


def test_failed_receipt_records_classification_and_follow_up_state(
    monkeypatch, tmp_path: Path
) -> None:
    def fake_run(cmd, cwd: Path):
        if isinstance(cmd, list) and cmd[:3] == ["git", "rev-parse", "origin/main"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")
        if isinstance(cmd, list) and cmd[:3] == ["git", "status", "--short"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd == "python3 scripts/wiki/check_derived_outputs.py":
            return subprocess.CompletedProcess(cmd, 1, stdout="stale wiki provenance", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(receipt, "_run", fake_run)
    monkeypatch.setattr(receipt.tempfile, "mkdtemp", lambda prefix: str(tmp_path / "verify"))
    monkeypatch.setattr(receipt.shutil, "rmtree", lambda *args, **kwargs: None)

    result, _ = receipt.build_receipt(
        Path("/repo"),
        ["python3 scripts/wiki/check_derived_outputs.py"],
        ["https://github.com/marcusglee11/LifeOS/issues/999"],
    )

    assert result["completion_claim"] == "follow_up_required"
    assert result["results"][0]["status"] == "fail"
    assert result["results"][0]["failure_classification"] == "new_drift"
    assert result["follow_up_issues_created"] == [
        "https://github.com/marcusglee11/LifeOS/issues/999"
    ]
