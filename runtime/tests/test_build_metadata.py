import json
import subprocess

from scripts.workflow.closure_pack import _close_build_record
from scripts.workflow.start_build import _write_build_record


def test_write_build_record(tmp_path, monkeypatch):
    primary_repo = tmp_path / "repo"
    primary_repo.mkdir()

    # Mock git rev-parse --git-common-dir to return a relative path that resolves to primary_repo
    def mock_run(args, **kwargs):
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    branch = "build/test-topic"
    kind = "build"
    topic = "test-topic"
    worktree_path = "/path/to/worktree"
    entrypoint = "start_build"

    _write_build_record(
        primary_repo=primary_repo,
        branch=branch,
        kind=kind,
        topic=topic,
        worktree_path=worktree_path,
        entrypoint=entrypoint,
    )

    record_path = primary_repo / ".git" / "lifeos" / "builds" / "build__test-topic.json"
    assert record_path.exists()

    record = json.loads(record_path.read_text())
    assert record["version"] == 1
    assert record["branch"] == branch
    assert record["kind"] == kind
    assert record["topic"] == topic
    assert record["entrypoint"] == entrypoint
    assert record["status"] == "active"
    assert record["worktree_path"] == worktree_path
    assert record["primary_repo"] == str(primary_repo)
    assert "created_at_utc" in record


def test_write_build_record_fail_open(tmp_path, monkeypatch):
    primary_repo = tmp_path / "repo"
    primary_repo.mkdir()

    # Mock git failure
    def mock_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Should not raise exception
    _write_build_record(
        primary_repo=primary_repo,
        branch="build/foo",
        kind="build",
        topic="foo",
        worktree_path="wt",
        entrypoint="test",
    )

    record_dir = primary_repo / ".git" / "lifeos" / "builds"
    assert not record_dir.exists()


def test_close_build_record(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_common = repo_root / ".git"
    record_dir = git_common / "lifeos" / "builds"
    record_dir.mkdir(parents=True)

    branch = "build/test-topic"
    slug = "build__test-topic"
    record_path = record_dir / f"{slug}.json"

    initial_record = {
        "version": 1,
        "branch": branch,
        "status": "active",
        "created_at_utc": "2026-01-01T00:00:00Z",
    }
    record_path.write_text(json.dumps(initial_record))

    def mock_run(args, **kwargs):
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    _close_build_record(repo_root, branch)

    record = json.loads(record_path.read_text())
    assert record["status"] == "closed"
    assert "closed_at_utc" in record
    assert record["branch"] == branch
    assert record["created_at_utc"] == "2026-01-01T00:00:00Z"


def test_close_build_record_no_record(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def mock_run(args, **kwargs):
        if "rev-parse" in args and "--git-common-dir" in args:
            return subprocess.CompletedProcess(args, 0, stdout=".git\n")
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Should not raise exception if record doesn't exist
    _close_build_record(repo_root, "build/nonexistent")
