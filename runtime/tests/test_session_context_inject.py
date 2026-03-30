from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    hook_path = (
        Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "session-context-inject.py"
    )
    spec = importlib.util.spec_from_file_location("session_context_inject", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worktree_audit_noop_when_clean(monkeypatch) -> None:
    module = _load_module()

    def fake_run_git(args: list[str], timeout: int = 3) -> str:
        if args == ["worktree", "prune", "--dry-run"]:
            return ""
        if args == ["worktree", "list", "--porcelain"]:
            return "worktree /repo\nworktree /repo/.worktrees/a"
        return ""

    monkeypatch.setattr(module, "run_git", fake_run_git)
    assert module.worktree_audit() == ""


def test_worktree_audit_prunes_and_warns(monkeypatch) -> None:
    module = _load_module()
    calls = []

    def fake_run_git(args: list[str], timeout: int = 3) -> str:
        calls.append(args)
        if args == ["worktree", "prune", "--dry-run"]:
            return "prunable"
        if args == ["worktree", "prune"]:
            return ""
        if args == ["worktree", "list", "--porcelain"]:
            return "\n".join(f"worktree /repo/{i}" for i in range(10))
        return ""

    monkeypatch.setattr(module, "run_git", fake_run_git)
    result = module.worktree_audit()
    assert "pruned stale registrations" in result
    assert "10 linked worktrees" in result
    assert ["worktree", "prune"] in calls
