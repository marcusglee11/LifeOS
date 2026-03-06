from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import scripts.git_workflow as gw
from scripts.workflow import closure_pack as cp


def _load_new_build_guard():
    hook_path = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "new-build-worktree-guard.py"
    spec = importlib.util.spec_from_file_location("new_build_worktree_guard", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_guard(module, payload: dict) -> dict:
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    old_stdin = module.sys.stdin
    old_stdout = module.sys.stdout
    try:
        module.sys.stdin = stdin
        module.sys.stdout = stdout
        module.main()
    except SystemExit:
        pass
    finally:
        module.sys.stdin = old_stdin
        module.sys.stdout = old_stdout
    out = stdout.getvalue().strip()
    return json.loads(out) if out else {}


class TestBranchNameHelpers:
    def test_validate_branch_valid_prefixes(self) -> None:
        for name in (
            "build/worktree-isolation",
            "fix/worktree-isolation",
            "hotfix/worktree-isolation",
            "spike/worktree-isolation",
        ):
            assert gw.validate_branch_name(name) is None

    def test_validate_branch_rejects_uppercase(self) -> None:
        assert gw.validate_branch_name("build/Worktree") is not None

    def test_validate_branch_rejects_no_prefix(self) -> None:
        assert gw.validate_branch_name("feature/worktree") is not None

    def test_derive_short_name_strips_prefix(self) -> None:
        assert gw._derive_worktree_short_name("build/test-isolation") == "test-isolation"

    def test_derive_short_name_sanitizes_non_alnum(self) -> None:
        assert gw._derive_worktree_short_name("build/test_isolation.v1") == "test-isolation-v1"

    def test_derive_short_name_truncates_at_30(self) -> None:
        name = "build/" + ("a" * 40)
        assert len(gw._derive_worktree_short_name(name)) == 30


def test_collision_aborts_with_recovery_hint(tmp_path, monkeypatch, capsys) -> None:
    primary = tmp_path / "primary"
    linked = tmp_path / "linked"
    primary.mkdir(parents=True)
    linked.mkdir(parents=True)
    (primary / ".worktrees" / "test-isolation").mkdir(parents=True)

    monkeypatch.setattr(gw, "_resolve_primary_repo", lambda: primary)
    monkeypatch.setattr(gw, "REPO_ROOT", linked)

    rc = gw.cmd_branch_create_worktree("build/test-isolation")
    output = capsys.readouterr().out

    assert rc == 1
    assert "git worktree prune" in output


def test_create_worktree_auto_resolves_to_primary(tmp_path, monkeypatch, capsys) -> None:
    primary = tmp_path / "primary"
    linked = tmp_path / "linked"
    primary.mkdir(parents=True)
    linked.mkdir(parents=True)

    saved: dict = {}

    def fake_run_git_in(path: Path, args: list[str]):
        if args[:2] == ["pull", "--ff-only"]:
            return 1, "", "offline"
        if args[:2] == ["worktree", "add"]:
            return 0, "", ""
        return 0, "", ""

    def fake_save_active(data: dict, repo_root: Path | None = None):
        saved["data"] = data
        saved["repo_root"] = repo_root

    monkeypatch.setattr(gw, "_resolve_primary_repo", lambda: primary)
    monkeypatch.setattr(gw, "run_git_in", fake_run_git_in)
    monkeypatch.setattr(gw, "load_active_branches", lambda repo_root=None: {"branches": []})
    monkeypatch.setattr(gw, "save_active_branches", fake_save_active)
    monkeypatch.setattr(gw, "REPO_ROOT", linked)

    rc = gw.cmd_branch_create_worktree("build/auto-resolve")
    output = capsys.readouterr().out

    assert rc == 0
    assert "Invoked from" in output
    assert "Primary repo" in output
    assert saved["repo_root"] == primary
    assert saved["data"]["branches"][0]["worktree_path"].startswith(str(primary / ".worktrees"))


def test_resolve_primary_repo_falls_back_to_git_common_dir(tmp_path, monkeypatch) -> None:
    primary = tmp_path / "primary"
    linked = tmp_path / "linked"
    primary.mkdir(parents=True)
    linked.mkdir(parents=True)

    worktree_list = (
        f"worktree {linked}\n"
        "HEAD deadbeef\n"
        "branch refs/heads/build/other\n\n"
        f"worktree {primary}\n"
        "HEAD cafe1234\n"
        "branch refs/heads/build/current\n"
    )

    def fake_run_git_in(path: Path, args: list[str]):
        if args == ["worktree", "list", "--porcelain"] and path == linked:
            return 0, worktree_list, ""
        if args == ["rev-parse", "--git-common-dir"] and path == linked:
            return 0, ".git/worktrees/build-other", ""
        if args == ["rev-parse", "--git-common-dir"] and path == primary:
            return 0, ".git", ""
        return 0, "", ""

    monkeypatch.setattr(gw, "REPO_ROOT", linked)
    monkeypatch.setattr(gw, "run_git_in", fake_run_git_in)

    assert gw._resolve_primary_repo() == primary


def test_guard_fast_path_non_bash(monkeypatch) -> None:
    """Tool without a 'command' field (e.g. Write) is always allowed."""
    module = _load_new_build_guard()
    result = _run_guard(module, {"tool_name": "Write", "tool_input": {"file_path": "runtime/foo.py"}})
    assert result.get("decision") == "allow"


def test_guard_fast_path_no_branch_creation(monkeypatch) -> None:
    """Plain git commands that don't create scoped branches are allowed."""
    module = _load_new_build_guard()
    result = _run_guard(module, {"tool_name": "Bash", "tool_input": {"command": "git status"}})
    assert result.get("decision") == "allow"


def test_guard_warns_when_untracked(monkeypatch) -> None:
    """Direct scoped branch creation via checkout -b is blocked with start_build.py guidance."""
    module = _load_new_build_guard()
    result = _run_guard(
        module,
        {"tool_name": "Bash", "tool_input": {"command": "git checkout -b build/foo"}},
    )
    assert result.get("decision") == "block"
    assert "start_build.py" in result.get("reason", "")


def test_guard_silent_when_clean(monkeypatch) -> None:
    """Direct scoped branch creation via switch -c is also blocked."""
    module = _load_new_build_guard()
    result = _run_guard(
        module,
        {"tool_name": "Bash", "tool_input": {"command": "git switch -c fix/bar"}},
    )
    assert result.get("decision") == "block"
    assert "start_build.py" in result.get("reason", "")


def test_closure_pack_regen_after_merge(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "linked"
    primary = tmp_path / "primary"
    repo_root.mkdir(parents=True)
    (primary / "scripts").mkdir(parents=True)
    (primary / "artifacts" / "status").mkdir(parents=True)
    status_gen = primary / "scripts" / "generate_runtime_status.py"
    status_gen.write_text("print('ok')\n", encoding="utf-8")

    events: list[str] = []
    commit_commands: list[list[str]] = []

    def fake_git_stdout(repo: Path, args: list[str]) -> str:
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return "build/feature"
        if args == ["log", "--oneline", "-n", "10"]:
            return "abc123 test commit"
        if args == ["diff", "--cached", "--name-only"]:
            return "artifacts/status/runtime_status.json"
        return ""

    def fake_merge_to_main(repo_root_arg: Path, branch: str) -> dict:
        events.append("merge")
        return {
            "success": True,
            "merge_sha": "deadbeef",
            "primary_repo": str(primary),
            "errors": [],
        }

    def fake_subprocess_run(cmd, **kwargs):
        if cmd[:2] == [sys.executable, str(status_gen)]:
            events.append("regen")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if len(cmd) >= 7 and cmd[:4] == ["git", "-C", str(primary), "add"]:
            events.append("git_add")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if len(cmd) >= 6 and cmd[:4] == ["git", "-C", str(primary), "commit"]:
            commit_commands.append(cmd)
            events.append("git_commit")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cp, "_git_stdout", fake_git_stdout)
    monkeypatch.setattr(cp, "_working_tree_clean", lambda _: True)
    monkeypatch.setattr(cp, "discover_changed_files", lambda _: [])
    monkeypatch.setattr(
        cp,
        "run_closure_tests",
        lambda *_: {"passed": True, "summary": "ok", "commands_run": [], "failures": []},
    )
    monkeypatch.setattr(
        cp,
        "check_doc_stewardship",
        lambda *_args, **_kwargs: {"passed": True, "required": False, "auto_fixed": False, "errors": []},
    )
    monkeypatch.setattr(cp, "merge_to_main", fake_merge_to_main)
    monkeypatch.setattr(
        cp,
        "update_state_and_backlog",
        lambda *_args, **_kwargs: {
            "state_updated": False,
            "backlog_updated": False,
            "items_marked": 0,
            "errors": [],
        },
    )
    monkeypatch.setattr(
        cp,
        "cleanup_after_merge",
        lambda *_args, **_kwargs: {
            "branch_deleted": True,
            "context_cleared": True,
            "worktree_removed": False,
            "errors": [],
        },
    )
    monkeypatch.setattr(cp.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(sys, "argv", ["closure_pack.py", "--repo-root", str(repo_root), "--no-state-update"])

    rc = cp.main()

    assert rc == 0
    assert "merge" in events
    assert "regen" in events
    assert events.index("merge") < events.index("regen")
    assert commit_commands
    assert "chore: refresh runtime_status.json (post-merge)" in commit_commands[0]


def test_closure_pack_blocks_primary_scoped_branch(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "primary"
    repo_root.mkdir(parents=True)

    def fake_git_stdout(repo: Path, args: list[str]) -> str:
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return "fix/runtime-guard"
        if args == ["log", "--oneline", "-n", "10"]:
            return "abc123 test commit"
        return ""

    monkeypatch.setattr(cp, "_git_stdout", fake_git_stdout)
    monkeypatch.setattr(cp, "_is_primary_worktree", lambda _: True)
    monkeypatch.setattr(sys, "argv", ["closure_pack.py", "--repo-root", str(repo_root)])

    rc = cp.main()
    output = capsys.readouterr().out

    assert rc == 1
    assert "ISOLATION_REQUIRED" in output
    assert "--recover-primary" in output
