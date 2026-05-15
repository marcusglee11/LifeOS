from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "clean_origin_post_merge_receipt.py"
spec = importlib.util.spec_from_file_location("clean_origin_post_merge_receipt", SCRIPT)
assert spec is not None
receipt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = receipt
assert spec.loader is not None
spec.loader.exec_module(receipt)


def test_redacts_token_shaped_output_from_summary() -> None:
    summary = receipt.summarize(
        "access_token=ghp_abcdefghijklmnopqrstuvwxyz123456 password=hunter2",
        "Authorization: Bearer sk-testsecretsecretsecretsecret",
        500,
    )

    assert "ghp_" not in summary
    assert "hunter2" not in summary
    assert "sk-test" not in summary
    assert "testsecret" not in summary
    assert "Bearer" not in summary
    assert "<REDACTED>" in summary


def test_build_receipt_uses_origin_main_clean_worktree_and_records_success(
    monkeypatch, tmp_path
) -> None:
    calls: list[tuple[str, object]] = []
    clean = tmp_path / "clean"
    clean.mkdir()

    def fake_run_git(args, repo_root):
        calls.append(("git", tuple(args)))
        if tuple(args) == ("rev-parse", "origin/main"):
            return "a" * 40
        if tuple(args) == ("status", "--short"):
            return ""
        return ""

    monkeypatch.setattr(receipt, "run_git", fake_run_git)
    monkeypatch.setattr(receipt, "create_clean_worktree", lambda repo_root, base_ref: clean)
    monkeypatch.setattr(
        receipt,
        "remove_clean_worktree",
        lambda repo_root, worktree: calls.append(("remove", worktree)),
    )
    monkeypatch.setattr(
        receipt,
        "run_command",
        lambda command, cwd, timeout, summary_limit: receipt.CommandResult(
            command=command, status="pass", summary="ok"
        ),
    )

    args = Namespace(
        repo_root=tmp_path,
        repo="marcusglee11/LifeOS",
        base_ref="origin/main",
        command=["python3 -m doc_steward.cli wiki-lint ."],
        follow_up_issue=[],
        timeout=10,
        summary_limit=200,
    )
    data, exit_code = receipt.build_receipt(args)

    assert exit_code == 0
    assert ("git", ("fetch", "origin", "main", "--prune")) in calls
    assert data["base_ref"] == "origin/main"
    assert data["verified_commit"] == "a" * 40
    assert data["dirty_worktree_after_verification"] is False
    assert data["completion_claim"] == "conductor_verified"


def test_failed_wiki_drift_is_follow_up_required(monkeypatch, tmp_path) -> None:
    clean = tmp_path / "clean"
    clean.mkdir()
    monkeypatch.setattr(
        receipt,
        "run_git",
        lambda args, repo_root: "b" * 40 if tuple(args) == ("rev-parse", "origin/main") else "",
    )
    monkeypatch.setattr(receipt, "create_clean_worktree", lambda repo_root, base_ref: clean)
    monkeypatch.setattr(receipt, "remove_clean_worktree", lambda repo_root, worktree: None)
    monkeypatch.setattr(
        receipt,
        "run_command",
        lambda command, cwd, timeout, summary_limit: receipt.CommandResult(
            command=command,
            status="fail",
            summary="wiki-lint found stale source_commit_max drift",
            failure_class="new_drift",
        ),
    )

    args = Namespace(
        repo_root=tmp_path,
        repo="marcusglee11/LifeOS",
        base_ref="origin/main",
        command=["python3 -m doc_steward.cli wiki-lint ."],
        follow_up_issue=["https://github.com/marcusglee11/LifeOS/issues/120"],
        timeout=10,
        summary_limit=200,
    )
    data, exit_code = receipt.build_receipt(args)

    assert exit_code == 1
    assert data["completion_claim"] == "follow_up_required"
    assert data["results"][0]["failure_class"] == "new_drift"
    assert data["follow_up_issues_created"] == ["https://github.com/marcusglee11/LifeOS/issues/120"]


def test_script_never_uses_shell_true() -> None:
    source = SCRIPT.read_text()
    assert "shell=True" not in source
