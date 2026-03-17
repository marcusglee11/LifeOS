from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import repo_safety_gate as safety_gate
from scripts.workflow import close_build as close_build
from scripts.workflow import start_build as start_build


def test_normalize_branch_defaults_to_build() -> None:
    kind, branch = start_build._normalize_branch("auth token refresh", "build")
    assert kind == "build"
    assert branch == "build/auth-token-refresh"


def test_normalize_branch_uses_topic_prefix() -> None:
    kind, branch = start_build._normalize_branch("fix/cache busting", "build")
    assert kind == "fix"
    assert branch == "fix/cache-busting"


def test_normalize_branch_rejects_prefix_kind_conflict() -> None:
    with pytest.raises(ValueError, match="conflicts"):
        start_build._normalize_branch("fix/cache-busting", "hotfix")


def test_start_build_json_output_success(monkeypatch, capsys, tmp_path: Path) -> None:
    fake_out = "✓ Worktree ready at: /tmp/repo/.worktrees/auth-token\n  Run: cd /tmp/repo/.worktrees/auth-token\n"

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=fake_out, stderr="")

    monkeypatch.setattr(start_build.subprocess, "run", fake_run)
    monkeypatch.setattr(start_build, "_git_stdout", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(sys, "argv", ["start_build.py", "auth token", "--json"])

    rc = start_build.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["branch"] == "build/auth-token"
    assert payload["worktree_path"] == "/tmp/repo/.worktrees/auth-token"


def test_start_build_recover_primary_json_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        start_build,
        "recover_primary_branch",
        lambda *_args, **_kwargs: {
            "ok": True,
            "error": None,
            "branch": "build/runtime-fix",
            "worktree_path": "/tmp/repo/.worktrees/runtime-fix",
            "stash_ref": "stash@{0}",
            "worktree_created": True,
            "primary_repo": "/tmp/repo",
        },
    )
    monkeypatch.setattr(sys, "argv", ["start_build.py", "--recover-primary", "--json"])

    rc = start_build.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["worktree_path"] == "/tmp/repo/.worktrees/runtime-fix"


def test_start_build_recover_primary_json_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        start_build,
        "recover_primary_branch",
        lambda *_args, **_kwargs: {
            "ok": False,
            "error": "not in scoped branch",
            "branch": None,
            "worktree_path": None,
            "stash_ref": None,
            "worktree_created": False,
            "primary_repo": "/tmp/repo",
        },
    )
    monkeypatch.setattr(sys, "argv", ["start_build.py", "--recover-primary", "--json"])

    rc = start_build.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"] == "not in scoped branch"


def test_start_build_auto_recover_existing_primary_branch(monkeypatch, capsys) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="❌ branch already exists\n",
            stderr="",
        )

    monkeypatch.setattr(start_build.subprocess, "run", fake_run)
    monkeypatch.setattr(start_build, "_extract_worktree_path", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(start_build, "_should_auto_recover_existing_primary_branch", lambda _branch: True)
    monkeypatch.setattr(
        start_build,
        "recover_primary_branch",
        lambda _branch: {
            "ok": True,
            "error": None,
            "branch": "build/existing-work",
            "worktree_path": "/tmp/repo/.worktrees/existing-work",
            "stash_ref": "stash@{0}",
            "worktree_created": True,
            "primary_repo": "/tmp/repo",
        },
    )
    monkeypatch.setattr(sys, "argv", ["start_build.py", "existing work", "--json"])

    rc = start_build.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["auto_recovered"] is True
    assert payload["worktree_path"] == "/tmp/repo/.worktrees/existing-work"


def test_recover_primary_branch_stashes_switches_and_reapplies(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    wt_path = repo / ".worktrees" / "recover-case"
    call_log: list[tuple[Path, list[str]]] = []

    monkeypatch.setattr(start_build, "_resolve_primary_repo", lambda: repo)
    monkeypatch.setattr(start_build, "_validate_branch_name", lambda _branch: None)
    monkeypatch.setattr(start_build, "_branch_exists", lambda _repo, _branch: True)
    monkeypatch.setattr(start_build, "_upsert_active_branch_record", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(start_build, "_default_base_branch", lambda _repo: "main")
    monkeypatch.setattr(start_build, "_derive_worktree_short_name", lambda _branch: "recover-case")
    monkeypatch.setattr(
        start_build,
        "_stash_push_if_needed",
        lambda _repo, _branch: ("stash@{0}", None),
    )

    def fake_linked_worktree(_repo: Path, _branch: str):
        # No linked worktree discovered during lookup; command should create one.
        return None

    monkeypatch.setattr(start_build, "_linked_worktree_for_branch", fake_linked_worktree)

    def fake_git_stdout(_repo: Path, args: list[str]) -> str:
        if args == ["branch", "--show-current"]:
            return "build/recover-case"
        if args == ["rev-parse", "--git-common-dir"]:
            return ".git"
        return ""

    monkeypatch.setattr(start_build, "_git_stdout", fake_git_stdout)

    def fake_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        call_log.append((repo_root, args))
        return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(start_build, "_git", fake_git)

    result = start_build.recover_primary_branch()

    assert result["ok"] is True
    assert result["branch"] == "build/recover-case"
    assert result["worktree_path"] == str(wt_path)
    assert result["stash_ref"] == "stash@{0}"
    assert result["worktree_created"] is True

    expected_primary_calls = [
        (repo, ["checkout", "main"]),
        (repo, ["worktree", "add", str(wt_path), "build/recover-case"]),
    ]
    for expected in expected_primary_calls:
        assert expected in call_log
    assert (wt_path, ["stash", "pop", "stash@{0}"]) in call_log


def test_close_build_json_output(monkeypatch, capsys) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="done\n", stderr="")

    monkeypatch.setattr(close_build.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["close_build.py", "--json"])

    rc = close_build.main()
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["ok"] is True
    assert payload["exit_code"] == 0
    assert payload["stdout"] == "done\n"


def test_isolation_requirement_flags_primary_scoped_branch(monkeypatch) -> None:
    def fake_run_git(args: list[str]):
        if args == ["branch", "--show-current"]:
            return 0, "build/runtime-fix"
        if args == ["rev-parse", "--git-common-dir"]:
            return 0, ".git"
        return 0, ""

    monkeypatch.setattr(safety_gate, "run_git", fake_run_git)

    issues = safety_gate.check_isolation_requirement("merge")

    assert issues
    assert issues[0].startswith("ISOLATION_REQUIRED:")
    assert "--recover-primary" in issues[0]


def test_isolation_requirement_skips_linked_worktree(monkeypatch) -> None:
    def fake_run_git(args: list[str]):
        if args == ["branch", "--show-current"]:
            return 0, "fix/runtime-fix"
        if args == ["rev-parse", "--git-common-dir"]:
            return 0, "/repo/.git/worktrees/fix-runtime-fix"
        return 0, ""

    monkeypatch.setattr(safety_gate, "run_git", fake_run_git)

    assert safety_gate.check_isolation_requirement("merge") == []
