import json
import subprocess
from datetime import datetime, timedelta, timezone

from scripts.workflow.build_entry_gate import check_gate, is_qualifying


def test_is_qualifying():
    assert is_qualifying("runtime/engine.py") is True
    assert is_qualifying("scripts/workflow/start_build.py") is True
    assert is_qualifying("config/invariants.yaml") is True
    assert is_qualifying("schemas/tasks.yaml") is True
    assert is_qualifying("tests/test_foo.py") is True
    assert is_qualifying(".github/workflows/ci.yml") is True
    assert is_qualifying("pyproject.toml") is True
    assert is_qualifying("pytest.ini") is True
    assert is_qualifying("requirements.txt") is True
    assert is_qualifying("requirements-dev.txt") is True

    assert is_qualifying("docs/README.md") is False
    assert is_qualifying("artifacts/active_branches.json") is False
    assert is_qualifying("README.md") is False
    assert is_qualifying("LICENSE") is False


def test_check_gate_no_qualifying(tmp_path):
    result = check_gate(repo_path=tmp_path, staged_files=[])
    assert result["passed"] is True
    assert result["qualifying"] is False
    assert result["reason"] == "No qualifying files staged."

    result = check_gate(repo_path=tmp_path, staged_files=["docs/README.md"])
    assert result["passed"] is True
    assert result["qualifying"] is False


def test_check_gate_main_fails(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    def mock_run(args, **kwargs):
        if "symbolic-ref" in args:
            return subprocess.CompletedProcess(args, 0, stdout="main\n")
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_gate(repo_path=repo, staged_files=["runtime/engine.py"])
    assert result["passed"] is False
    assert result["qualifying"] is True
    assert "not a scoped build branch" in result["reason"]
    assert result["branch"] == "main"
    assert result["on_worktree"] is False


def test_check_gate_linked_worktree_active_record(tmp_path, monkeypatch):
    repo = tmp_path / "worktree"
    repo.mkdir()
    primary = tmp_path / "primary"
    primary.mkdir()
    git_common = primary / ".git"
    git_common.mkdir()

    branch = "build/feature"
    slug = "build__feature"
    record_dir = git_common / "lifeos" / "builds"
    record_dir.mkdir(parents=True)
    record_path = record_dir / f"{slug}.json"
    record_path.write_text(json.dumps({"status": "active", "branch": branch}))

    def mock_run(args, **kwargs):
        if "symbolic-ref" in args:
            return subprocess.CompletedProcess(args, 0, stdout=f"{branch}\n")
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=f"{git_common}\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_gate(repo_path=repo, staged_files=["runtime/engine.py"])
    assert result["passed"] is True
    assert result["qualifying"] is True
    assert result["on_worktree"] is True
    assert result["has_record"] is True


def test_check_gate_linked_worktree_missing_record(tmp_path, monkeypatch):
    repo = tmp_path / "worktree"
    repo.mkdir()
    primary = tmp_path / "primary"
    primary.mkdir()
    git_common = primary / ".git"
    git_common.mkdir()

    branch = "build/feature"

    def mock_run(args, **kwargs):
        if "symbolic-ref" in args:
            return subprocess.CompletedProcess(args, 0, stdout=f"{branch}\n")
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=f"{git_common}\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_gate(repo_path=repo, staged_files=["runtime/engine.py"])
    assert result["passed"] is False
    assert result["qualifying"] is True
    assert result["on_worktree"] is True
    assert result["has_record"] is False
    assert "No active build record" in result["reason"]


def test_check_gate_bypass_token(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git_common = repo / ".git"
    git_common.mkdir()

    slug = "main"
    bypass_dir = git_common / "lifeos" / "bypass"
    bypass_dir.mkdir(parents=True)
    bypass_path = bypass_dir / f"{slug}.json"

    # Valid bypass token
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    bypass_path.write_text(json.dumps({"expires_at_utc": expires.isoformat()}))

    def mock_run(args, **kwargs):
        if "symbolic-ref" in args:
            return subprocess.CompletedProcess(args, 0, stdout="main\n")
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_gate(repo_path=repo, staged_files=["runtime/engine.py"])
    assert result["passed"] is True
    assert result["qualifying"] is True
    assert result["bypass_active"] is True
    assert result["reason"] == "Bypass token active."


def test_check_gate_bypass_token_expired(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git_common = repo / ".git"
    git_common.mkdir()

    slug = "main"
    bypass_dir = git_common / "lifeos" / "bypass"
    bypass_dir.mkdir(parents=True)
    bypass_path = bypass_dir / f"{slug}.json"

    # Expired bypass token
    expires = datetime.now(timezone.utc) - timedelta(hours=1)
    bypass_path.write_text(json.dumps({"expires_at_utc": expires.isoformat()}))

    def mock_run(args, **kwargs):
        if "symbolic-ref" in args:
            return subprocess.CompletedProcess(args, 0, stdout="main\n")
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = check_gate(repo_path=repo, staged_files=["runtime/engine.py"])
    assert result["passed"] is False
    assert result["qualifying"] is True
    assert result["bypass_active"] is False
    assert not bypass_path.exists()  # Should be unlinked
