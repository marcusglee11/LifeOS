from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)


def _load_safe_cleanup_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "safe_cleanup.py"
    spec = importlib.util.spec_from_file_location("safe_cleanup_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".gitignore").write_text(
        "artifacts/99_archive/**\nlogs/cleanup_ledger.jsonl\n",
        encoding="utf-8",
    )
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _configure_module_paths(module, repo: Path) -> None:
    module.REPO_ROOT = repo
    module.ISOLATION_VAULT = repo / "artifacts" / "99_archive" / "stray"
    module.CLEANUP_LOG = repo / "logs" / "cleanup_ledger.jsonl"


def _setup_repo_without_ignore(tmp_path: Path) -> Path:
    repo = tmp_path / "repo-no-ignore"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def test_isolate_without_apply_is_dry_run(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(apply=False, rationale=None, allow_protected=False, repo_root=repo)
    assert rc == 0
    assert (repo / "draft.txt").exists()


def test_isolate_apply_requires_rationale(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.main(["--isolate", "--apply"])
    assert rc == 1
    assert (repo / "draft.txt").exists()


def test_isolate_blocks_protected_paths_without_override(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    target = repo / "runtime" / "tmp.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("protected\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="cleanup",
        allow_protected=False,
        repo_root=repo,
    )
    assert rc == 1
    assert target.exists()


def test_isolate_allow_protected_moves_and_logs_invoker(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    target = repo / "runtime" / "tmp.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("protected\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="intentional isolation",
        allow_protected=True,
        repo_root=repo,
    )
    assert rc == 0
    assert not target.exists()

    date_str = mod.datetime.now().strftime("%Y%m%d")
    isolated = repo / "artifacts" / "99_archive" / "stray" / date_str / "tmp.txt"
    assert isolated.exists()

    ledger = repo / "logs" / "cleanup_ledger.jsonl"
    assert ledger.exists()
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert entries
    last = entries[-1]
    assert last["rationale"] == "intentional isolation"
    assert "invoker" in last
    assert set(last["invoker"]).issuperset({"pid", "ppid", "argv", "parent_cmd"})


def test_isolate_blocks_when_output_paths_not_ignored(tmp_path: Path) -> None:
    repo = _setup_repo_without_ignore(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="isolate now",
        allow_protected=False,
        repo_root=repo,
    )
    assert rc == 1
    assert (repo / "draft.txt").exists()


def test_isolate_apply_keeps_git_status_clean_when_outputs_ignored(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    (repo / "draft.txt").write_text("hello\n", encoding="utf-8")

    mod = _load_safe_cleanup_module()
    _configure_module_paths(mod, repo)

    rc = mod.isolate(
        apply=True,
        rationale="cleanup",
        allow_protected=False,
        repo_root=repo,
    )
    assert rc == 0

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout.strip() == ""
