#!/usr/bin/env python3
"""
Acceptance Tests for Stewardship Runner (AT-01 through AT-10).

These tests use git worktree to create isolated test environments (H1).
Each test creates a temporary worktree, runs the runner, and validates
both exit codes and log contents.

Run with:
    python -m pytest tests_recursive/test_steward_runner.py -v
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


# --- Test Fixtures ---

@pytest.fixture
def repo_root() -> Path:
    """Get the main repo root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


@pytest.fixture
def worktree(repo_root: Path, tmp_path: Path):
    """
    Create a git worktree for isolated testing (H1).
    
    Copies untracked/modified steward runner files to worktree so tests
    work before the runner is committed. Commits them so worktree is clean.
    
    Yields the worktree path and cleans up after.
    """
    worktree_path = tmp_path / "test_worktree"
    branch_name = f"test-steward-{os.getpid()}"
    
    # Create orphan branch for isolation
    subprocess.run(
        ["git", "branch", branch_name, "HEAD"],
        cwd=repo_root,
        capture_output=True,
    )
    
    # Create worktree
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=repo_root,
        capture_output=True,
    )
    
    # Copy untracked/modified files needed for running tests
    # These files may not be committed yet during development
    files_to_copy = [
        "scripts/steward_runner.py",
        "config/steward_runner.yaml",
        "doc_steward/cli.py",
    ]
    
    copied_any = False
    for rel_path in files_to_copy:
        src = repo_root / rel_path
        dst = worktree_path / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_any = True
    
    # Commit copied files so worktree starts clean
    if copied_any:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "[test] Add steward runner files for testing"],
            cwd=worktree_path,
            capture_output=True,
        )
    
    yield worktree_path
    
    # Cleanup
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_root,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=repo_root,
        capture_output=True,
    )


@pytest.fixture
def test_config(worktree: Path) -> Path:
    """Create a minimal test config in the worktree and commit it."""
    config_dir = worktree / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_content = """
repo_root: "."

tests:
  command: ["python", "-c", "print('tests pass')"]
  paths: []

validators:
  commands: []

corpus:
  command: ["python", "-c", "print('corpus generated')"]
  outputs_expected: []

git:
  require_clean_start: false
  commit_enabled: false
  commit_message_template: "[test] {run_id}"
  commit_paths: ["docs/"]

logging:
  log_dir: "logs/steward_runner"
  streams_dir: "logs/steward_runner/streams"
  format: "jsonl"

determinism:
  run_id_required: true
  timestamps: false
"""
    
    config_path = config_dir / "test_runner.yaml"
    config_path.write_text(config_content)
    
    # Commit the config so worktree starts clean
    subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "[test] Add test config"],
        cwd=worktree,
        capture_output=True,
    )
    
    return config_path


def run_steward(
    worktree: Path,
    config_path: Path,
    run_id: str | None = None,
    dry_run: bool = False,
    no_commit: bool = False,
    expect_fail: bool = False,
) -> tuple[int, Path | None]:
    """
    Run the steward runner in the worktree.
    
    Returns (exit_code, log_file_path or None).
    """
    runner_path = worktree / "scripts" / "steward_runner.py"
    
    cmd = ["python", str(runner_path)]
    cmd.extend(["--config", str(config_path.relative_to(worktree))])
    
    if run_id:
        cmd.extend(["--run-id", run_id])
    
    if dry_run:
        cmd.append("--dry-run")
    
    if no_commit:
        cmd.append("--no-commit")
    
    result = subprocess.run(
        cmd,
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    
    # Find log file
    log_dir = worktree / "logs" / "steward_runner"
    log_file = None
    if run_id and log_dir.exists():
        expected_log = log_dir / f"{run_id}.jsonl"
        if expected_log.exists():
            log_file = expected_log
    
    return result.returncode, log_file


def read_log_events(log_file: Path) -> list[dict]:
    """Read JSONL log file into list of events."""
    events = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))
    return events


def find_event(events: list[dict], step: str, status: str) -> dict | None:
    """Find an event by step and status."""
    for event in events:
        if event.get("step") == step and event.get("status") == status:
            return event
    return None


# --- Acceptance Tests ---

class TestAT01MissingRunId:
    """AT-01: Missing run-id fails closed."""
    
    def test_missing_run_id_fails(self, worktree: Path, test_config: Path):
        """Invoke without --run-id → exit != 0."""
        runner_path = worktree / "scripts" / "steward_runner.py"
        
        result = subprocess.run(
            ["python", str(runner_path), "--config", str(test_config.relative_to(worktree))],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0, "Should fail without --run-id"
        assert "required" in result.stderr.lower() or "run-id" in result.stderr.lower()


class TestAT02DirtyRepoStart:
    """AT-02: Dirty repo start fails when required."""
    
    def test_dirty_repo_fails_with_require_clean(self, worktree: Path, test_config: Path):
        """With uncommitted change and require_clean_start=true → exit != 0."""
        # Update config to require clean start
        config_content = test_config.read_text().replace(
            "require_clean_start: false",
            "require_clean_start: true"
        )
        test_config.write_text(config_content)
        
        # Create uncommitted file
        dirty_file = worktree / "dirty_file.txt"
        dirty_file.write_text("uncommitted content")
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at02-test")
        
        assert exit_code != 0, "Should fail with dirty repo"
        
        if log_file:
            events = read_log_events(log_file)
            fail_event = find_event(events, "preflight", "fail")
            assert fail_event is not None, "Should have preflight.fail event"
            assert fail_event.get("reason") == "dirty_repo"


class TestAT03TestsFailureBlocksDownstream:
    """AT-03: Tests failure blocks downstream."""
    
    def test_tests_failure_blocks_validators(self, worktree: Path, test_config: Path):
        """Make tests return non-zero → validators/corpus/commit never run."""
        # Update config with failing tests
        config_content = test_config.read_text().replace(
            'command: ["python", "-c", "print(\'tests pass\')"]',
            'command: ["python", "-c", "import sys; sys.exit(1)"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at03-test")
        
        assert exit_code != 0, "Should fail when tests fail"
        
        if log_file:
            events = read_log_events(log_file)
            # Should have tests.fail
            tests_fail = find_event(events, "tests", "fail")
            assert tests_fail is not None, "Should have tests.fail event"
            
            # Should NOT have validators or corpus events
            for event in events:
                assert "validator" not in event.get("step", ""), "Validators should not run"
                assert event.get("step") != "corpus", "Corpus should not run"


class TestAT04ValidatorFailureBlocksCorpus:
    """AT-04: Validator failure blocks corpus."""
    
    def test_validator_failure_blocks_corpus(self, worktree: Path, test_config: Path):
        """Tests pass, validator returns non-zero → corpus not executed."""
        # Update config with failing validator
        config_content = test_config.read_text().replace(
            "validators:\n  commands: []",
            'validators:\n  commands:\n    - ["python", "-c", "import sys; sys.exit(1)"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at04-test")
        
        assert exit_code != 0, "Should fail when validator fails"
        
        if log_file:
            events = read_log_events(log_file)
            # Should have validator fail
            validator_fail = find_event(events, "validator_0", "fail")
            assert validator_fail is not None, "Should have validator.fail event"
            
            # Should NOT have corpus event
            for event in events:
                assert event.get("step") != "corpus", "Corpus should not run"


class TestAT05CorpusExpectedOutputsEnforced:
    """AT-05: Corpus expected outputs enforced."""
    
    def test_missing_corpus_output_fails(self, worktree: Path, test_config: Path):
        """Corpus exits 0 but any outputs_expected missing → fail."""
        # Update config to expect an output that won't be created
        config_content = test_config.read_text().replace(
            "outputs_expected: []",
            'outputs_expected: ["docs/nonexistent.md"]'
        )
        test_config.write_text(config_content)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at05-test")
        
        assert exit_code != 0, "Should fail when expected output missing"
        
        if log_file:
            events = read_log_events(log_file)
            corpus_fail = find_event(events, "corpus", "fail")
            assert corpus_fail is not None, "Should have corpus.fail event"
            assert corpus_fail.get("reason") == "missing_output"


class TestAT06NoChangeNoCommit:
    """AT-06: No change = no commit."""
    
    def test_no_change_exits_success(self, worktree: Path, test_config: Path):
        """Corpus runs, no changes → exit 0; no commit."""
        exit_code, log_file = run_steward(worktree, test_config, run_id="at06-test")
        
        assert exit_code == 0, "Should succeed with no changes"
        
        if log_file:
            events = read_log_events(log_file)
            no_change = find_event(events, "change_detect", "no_change")
            assert no_change is not None, "Should have no_change event"


class TestAT07ChangeWithinAllowedPathsCommits:
    """AT-07: Change within allowed paths commits once."""
    
    def test_allowed_change_commits(self, worktree: Path, test_config: Path):
        """Corpus creates diff only within commit_paths → exactly one commit."""
        # Enable commit and create a change in allowed path
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Make corpus create a file in docs/
        config_content = config_content.replace(
            'command: ["python", "-c", "print(\'corpus generated\')"]',
            'command: ["python", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        config_content = config_content.replace(
            "commit_paths: [\"docs/\"]",
            'commit_paths: ["docs/"]'
        )
        test_config.write_text(config_content)
        
        # Commit the config change so only docs/ changes are uncommitted
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] Update config for AT-07"],
            cwd=worktree,
            capture_output=True,
        )
        
        # Ensure docs dir exists
        (worktree / "docs").mkdir(exist_ok=True)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at07-test")
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code == 0, "Should succeed with allowed changes"
        assert head_after != head_before, "HEAD should change after commit"
        
        if log_file:
            events = read_log_events(log_file)
            commit_pass = find_event(events, "commit", "pass")
            assert commit_pass is not None, "Should have commit.pass event"


class TestAT08ChangeOutsideAllowedPathsFails:
    """AT-08: Change outside allowed paths fails closed."""
    
    def test_disallowed_change_fails(self, worktree: Path, test_config: Path):
        """Diff touches any path outside commit_paths → exit != 0; no commit."""
        # Enable commit but create change outside allowed path
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Make corpus create a file outside docs/
        config_content = config_content.replace(
            'command: ["python", "-c", "print(\'corpus generated\')"]',
            'command: ["python", "-c", "open(\'outside.txt\', \'w\').write(\'disallowed\')"]'
        )
        test_config.write_text(config_content)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at08-test")
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code != 0, "Should fail with disallowed changes"
        assert head_after == head_before, "HEAD should not change"
        
        if log_file:
            events = read_log_events(log_file)
            commit_fail = find_event(events, "commit", "fail")
            assert commit_fail is not None, "Should have commit.fail event"
            assert commit_fail.get("reason") == "changes_outside_allowlist"


class TestAT09DryRunNeverCommits:
    """AT-09: Dry run never commits."""
    
    def test_dry_run_skips_commit(self, worktree: Path, test_config: Path):
        """With allowable diff and --dry-run → exit 0; commit skipped."""
        # Enable commit and create allowed change
        config_content = test_config.read_text().replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python", "-c", "print(\'corpus generated\')"]',
            'command: ["python", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        head_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        # Run with --dry-run
        exit_code, log_file = run_steward(worktree, test_config, run_id="at09-test", dry_run=True)
        
        head_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            capture_output=True,
            text=True,
        ).stdout.strip()
        
        assert exit_code == 0, "Should succeed with dry-run"
        assert head_after == head_before, "HEAD should not change with dry-run"
        
        if log_file:
            events = read_log_events(log_file)
            commit_skipped = find_event(events, "commit", "skipped")
            assert commit_skipped is not None, "Should have commit.skipped event"
            assert commit_skipped.get("reason") == "dry_run"


class TestAT10LogDeterminism:
    """AT-10: Log determinism."""
    
    def test_logs_are_deterministic(self, worktree: Path, test_config: Path):
        """Same repo state + same run_id → byte-identical JSONL."""
        run_id = "at10-determinism"
        
        # First run
        exit_code1, log_file1 = run_steward(worktree, test_config, run_id=run_id)
        assert exit_code1 == 0
        assert log_file1 is not None
        content1 = log_file1.read_text()
        
        # Delete log for second run
        log_file1.unlink()
        
        # Second run with same state and run_id
        exit_code2, log_file2 = run_steward(worktree, test_config, run_id=run_id)
        assert exit_code2 == 0
        assert log_file2 is not None
        content2 = log_file2.read_text()
        
        # H2: byte-identical
        assert content1 == content2, "Logs should be byte-identical for same state/run_id"


class TestAT11TestScopeEnforcement:
    """AT-11: Test scope enforcement (P0-1)."""
    
    def test_tests_argv_includes_paths(self, worktree: Path, test_config: Path):
        """tests.paths must appear in the tests step argv."""
        # Update config to have specific test paths
        config_content = test_config.read_text()
        config_content = config_content.replace(
            "paths: []",
            'paths: ["path_a", "path_b", "path_c"]'
        )
        test_config.write_text(config_content)
        
        # Commit config change
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] Update config for AT-11"],
            cwd=worktree,
            capture_output=True,
        )
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at11-test")
        
        # Test passes or fails, but we need to check the argv
        assert log_file is not None, "Should have log file"
        
        events = read_log_events(log_file)
        
        # Find the tests command event
        tests_event = None
        for event in events:
            if event.get("step") == "tests" and event.get("event") == "command":
                tests_event = event
                break
        
        assert tests_event is not None, "Should have tests command event"
        
        argv = tests_event.get("argv", [])
        
        # Assert all paths are in argv in order
        assert "path_a" in argv, "path_a should be in argv"
        assert "path_b" in argv, "path_b should be in argv"
        assert "path_c" in argv, "path_c should be in argv"
        
        # Assert paths appear after the command part
        path_a_idx = argv.index("path_a")
        path_b_idx = argv.index("path_b")
        path_c_idx = argv.index("path_c")
        
        assert path_a_idx < path_b_idx < path_c_idx, "Paths should appear in config order"


class TestAT12AllowlistNormalization:
    """AT-12: Allowlist normalization (bare names → directories)."""
    
    def test_bare_name_normalized_to_directory(self, worktree: Path, test_config: Path):
        """Bare names like 'docs' normalize to 'docs/' in committed paths."""
        # Update config with bare name (no trailing /)
        config_content = test_config.read_text()
        config_content = config_content.replace(
            'commit_paths: ["docs/"]',
            'commit_paths: ["docs"]'  # No trailing slash
        )
        config_content = config_content.replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        config_content = config_content.replace(
            'command: ["python", "-c", "print(\'corpus generated\')"]',
            'command: ["python", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        # Commit config changes
        subprocess.run(["git", "add", "-A"], cwd=worktree, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "[test] AT-12 config"],
            cwd=worktree,
            capture_output=True,
        )
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id="at12-test")
        
        assert exit_code == 0, "Should succeed with bare name normalized"
        assert log_file is not None
        
        events = read_log_events(log_file)
        commit_event = find_event(events, "commit", "pass")
        assert commit_event is not None, "Should have commit.pass event"
        
        # Normalized paths should have trailing /
        commit_paths = commit_event.get("commit_paths", [])
        assert "docs/" in commit_paths, "Bare name 'docs' should normalize to 'docs/'"


class TestAT13FailClosedUnsafePaths:
    """AT-13: Fail-closed on unsafe commit paths."""
    
    @pytest.mark.parametrize("unsafe_path,expected_error", [
        ("../docs/", "path_traversal"),
        ("docs/../other/", "path_traversal"),
        ("docs/*.md", "glob_pattern"),
        ("docs/?.md", "glob_pattern"),
        ("C:/temp/", "absolute_path_windows"),
        ("C:\\temp\\", "absolute_path_windows"),
        ("/absolute/path/", "absolute_path_unix"),
        ("//server/share/", "absolute_path_unc"),
    ])
    def test_unsafe_path_fails(self, worktree: Path, test_config: Path, unsafe_path: str, expected_error: str):
        """Unsafe paths fail closed with clear error reason."""
        # Update config with unsafe path
        config_content = test_config.read_text()
        # Escape for YAML
        escaped_path = unsafe_path.replace("\\", "\\\\")
        config_content = config_content.replace(
            'commit_paths: ["docs/"]',
            f'commit_paths: ["{escaped_path}"]'
        )
        config_content = config_content.replace(
            "commit_enabled: false",
            "commit_enabled: true"
        )
        # Create a change so commit is attempted
        config_content = config_content.replace(
            'command: ["python", "-c", "print(\'corpus generated\')"]',
            'command: ["python", "-c", "import os; os.makedirs(\'docs\', exist_ok=True); open(\'docs/test.md\', \'w\').write(\'test\')"]'
        )
        test_config.write_text(config_content)
        
        (worktree / "docs").mkdir(exist_ok=True)
        
        exit_code, log_file = run_steward(worktree, test_config, run_id=f"at13-{expected_error}")
        
        assert exit_code != 0, f"Should fail with unsafe path: {unsafe_path}"
        assert log_file is not None
        
        events = read_log_events(log_file)
        commit_fail = find_event(events, "commit", "fail")
        assert commit_fail is not None, "Should have commit.fail event"
        assert commit_fail.get("reason") == "invalid_commit_path"
        assert commit_fail.get("error") == expected_error, f"Expected error {expected_error}"
