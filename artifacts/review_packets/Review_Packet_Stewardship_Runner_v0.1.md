# Review_Packet_Stewardship_Runner_v0.1

**Mission**: Implement Stewardship Runner v0.1  
**Date**: 2026-01-02  
**Author**: Antigravity Agent  
**Status**: COMPLETE — All 10 acceptance tests pass

---

## 1. Summary

Implemented a deterministic, auditable CLI pipeline for LifeOS autonomous stewardship:

```
preflight → tests → validators → corpus → change_detect → commit → postflight
```

**Key Features**:
- Fail-closed semantics (C1-C5)
- Deterministic JSONL logging with content-addressed streams (B1-B4)
- Commit disabled by default, allowlist enforcement
- Log directory excluded from change detection

---

## 2. Issue Catalogue

| ID | Issue | Resolution |
|----|-------|------------|
| ISS-01 | Validators lack CLI interface | Created `doc_steward/cli.py` |
| ISS-02 | No explicit config-driven pipeline | Created `config/steward_runner.yaml` |
| ISS-03 | Need isolated test environment | Used `git worktree` per H1 |
| ISS-04 | Runner logs appear as changes | Excluded log dir from change detection |

---

## 3. Proposed Resolutions

All resolutions implemented as new files:

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/steward_runner.py` | 580 | Main pipeline CLI |
| `config/steward_runner.yaml` | 54 | Default configuration |
| `doc_steward/cli.py` | 99 | Validator CLI wrapper |
| `tests_recursive/test_steward_runner.py` | 529 | Acceptance tests |

---

## 4. Acceptance Criteria

| Test | Requirement | Status |
|------|-------------|--------|
| AT-01 | Missing run-id fails closed | ✅ PASS |
| AT-02 | Dirty repo start fails when required | ✅ PASS |
| AT-03 | Tests failure blocks downstream | ✅ PASS |
| AT-04 | Validator failure blocks corpus | ✅ PASS |
| AT-05 | Corpus expected outputs enforced | ✅ PASS |
| AT-06 | No change = no commit | ✅ PASS |
| AT-07 | Change within allowed paths commits | ✅ PASS |
| AT-08 | Change outside allowed paths fails | ✅ PASS |
| AT-09 | Dry run never commits | ✅ PASS |
| AT-10 | Log determinism | ✅ PASS |

---

## 5. Non-Goals

- `git push` (I1: network/credential nondeterminism, handled in CI)
- MVP phased approach (user requested full spec)

---

## Appendix — Flattened Code Snapshots

### File: scripts/steward_runner.py

```python
#!/usr/bin/env python3
"""
Stewardship Runner — Deterministic, auditable CLI pipeline for LifeOS.

Pipeline order (A2):
    preflight → tests → validators → corpus → change_detect → commit → postflight

Usage:
    python scripts/steward_runner.py --run-id <ID> [options]

Options:
    --config PATH    Config file (default: config/steward_runner.yaml)
    --run-id ID      Required. Unique identifier for this run.
    --dry-run        Skip commit even if enabled.
    --no-commit      Skip commit even if enabled.
    --step STEP      Run single step only (for debugging).

Exit codes:
    0 - Pipeline completed successfully
    1 - Pipeline failed (see logs for details)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


# --- Logging Infrastructure ---

class DeterministicLogger:
    """JSONL logger with content-addressed stream storage."""
    
    def __init__(self, log_dir: Path, streams_dir: Path, run_id: str, timestamps: bool = False):
        self.log_dir = log_dir
        self.streams_dir = streams_dir
        self.run_id = run_id
        self.timestamps = timestamps
        self.log_file = log_dir / f"{run_id}.jsonl"
        
        # Ensure directories exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.streams_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear any existing log for this run_id (idempotent reruns)
        if self.log_file.exists():
            self.log_file.unlink()
    
    def _store_stream(self, content: str, suffix: str) -> str:
        """Store content in content-addressed file, return hash."""
        if not content:
            return ""
        content_bytes = content.encode("utf-8")
        sha = hashlib.sha256(content_bytes).hexdigest()
        stream_file = self.streams_dir / f"{sha}{suffix}"
        if not stream_file.exists():
            stream_file.write_bytes(content_bytes)
        return sha
    
    def log(self, event: str, step: str, status: str, **kwargs: Any) -> None:
        """Write a JSONL event line."""
        record: dict[str, Any] = {
            "run_id": self.run_id,
            "event": event,
            "step": step,
            "status": status,
        }
        record.update(kwargs)
        
        # Remove None values for cleaner logs
        record = {k: v for k, v in record.items() if v is not None}
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    
    def log_command(
        self,
        step: str,
        status: str,
        cwd: str,
        argv: list[str],
        exit_code: int,
        stdout: str,
        stderr: str,
        **kwargs: Any,
    ) -> None:
        """Log a command execution with content-addressed streams."""
        stdout_hash = self._store_stream(stdout, ".out")
        stderr_hash = self._store_stream(stderr, ".err")
        
        self.log(
            event="command",
            step=step,
            status=status,
            cwd=cwd,
            argv=argv,
            exit_code=exit_code,
            stdout_hash=stdout_hash,
            stderr_hash=stderr_hash,
            **kwargs,
        )


# --- Pipeline Stages ---

def get_repo_root() -> Path:
    """Get canonical repo root via git."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to determine repo root via git")
    return Path(result.stdout.strip()).resolve()


def get_git_head() -> str:
    """Get current HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def is_repo_dirty() -> bool:
    """Check if repo has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def get_changed_files() -> list[str]:
    """Get list of changed files (sorted, forward-slash normalized)."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        return []
    
    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            # Format: "XY filename" or "XY old -> new" for renames
            parts = line[3:].split(" -> ")
            filename = parts[-1].strip()
            # Normalize to forward slashes (B3)
            filename = filename.replace("\\", "/")
            files.append(filename)
    
    return sorted(files)


def run_command(
    argv: list[str],
    cwd: Path,
    logger: DeterministicLogger,
    step: str,
) -> tuple[int, str, str]:
    """Run a command and log it."""
    result = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    
    status = "pass" if result.returncode == 0 else "fail"
    logger.log_command(
        step=step,
        status=status,
        cwd=str(cwd),
        argv=argv,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
    
    return result.returncode, result.stdout, result.stderr


# --- Pipeline Execution ---

def run_preflight(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
    run_id: str,
) -> tuple[bool, str]:
    """Preflight checks. Returns (success, git_head_before)."""
    git_head = get_git_head()
    
    # C1: run_id is required (enforced by argparse, but double-check)
    if not run_id:
        logger.log("preflight", "preflight", "fail", reason="missing_run_id")
        return False, git_head
    
    # C2: Check for clean start if required
    if config.get("git", {}).get("require_clean_start", False):
        if is_repo_dirty():
            logger.log(
                "preflight", "preflight", "fail",
                reason="dirty_repo",
                git_head_before=git_head,
            )
            return False, git_head
    
    logger.log(
        "preflight", "preflight", "pass",
        git_head_before=git_head,
    )
    return True, git_head


def run_tests(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
) -> bool:
    """Run test suite. Returns success."""
    tests_config = config.get("tests", {})
    command = tests_config.get("command", ["python", "-m", "pytest", "-q"])
    
    exit_code, _, _ = run_command(command, repo_root, logger, "tests")
    return exit_code == 0


def run_validators(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
) -> bool:
    """Run validators in order. Stops on first failure (E3). Returns success."""
    validators_config = config.get("validators", {})
    commands = validators_config.get("commands", [])
    
    for i, command in enumerate(commands):
        exit_code, _, _ = run_command(command, repo_root, logger, f"validator_{i}")
        if exit_code != 0:
            return False
    
    return True


def run_corpus(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
) -> bool:
    """Run corpus generation and verify outputs. Returns success."""
    corpus_config = config.get("corpus", {})
    command = corpus_config.get("command", [])
    outputs_expected = corpus_config.get("outputs_expected", [])
    
    if not command:
        logger.log("corpus", "corpus", "skip", reason="no_command")
        return True
    
    exit_code, _, _ = run_command(command, repo_root, logger, "corpus")
    if exit_code != 0:
        return False
    
    # F2: Verify expected outputs exist
    for output in outputs_expected:
        output_path = repo_root / output
        if not output_path.exists():
            logger.log(
                "corpus", "corpus", "fail",
                reason="missing_output",
                missing_file=output,
            )
            return False
    
    return True


def run_change_detect(
    config: dict[str, Any],
    logger: DeterministicLogger,
) -> list[str]:
    """Detect changes via git status, excluding runner's own log directory."""
    # Get log directory to exclude from change detection
    logging_config = config.get("logging", {})
    log_dir = logging_config.get("log_dir", "logs/steward_runner")
    # Normalize to forward slash and ensure trailing slash for prefix matching
    log_dir = log_dir.replace("\\", "/")
    if not log_dir.endswith("/"):
        log_dir += "/"
    
    all_changed = get_changed_files()
    
    # Filter out files in the log directory (runner's own artifacts)
    changed_files = [
        f for f in all_changed 
        if not f.startswith(log_dir) and f != log_dir.rstrip("/")
    ]
    
    if changed_files:
        logger.log(
            "change_detect", "change_detect", "detected",
            changed_files=changed_files,
        )
    else:
        logger.log("change_detect", "change_detect", "no_change")
    
    return changed_files


def run_commit(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
    run_id: str,
    changed_files: list[str],
    dry_run: bool,
    no_commit: bool,
) -> tuple[bool, str | None]:
    """
    Commit changes if allowed. Returns (success, git_head_after).
    
    Implements C4/C5: commit disabled by default, allowlist enforcement.
    """
    git_config = config.get("git", {})
    commit_enabled = git_config.get("commit_enabled", False)
    commit_paths = git_config.get("commit_paths", [])
    commit_message_template = git_config.get(
        "commit_message_template",
        "[steward] Autonomous run {run_id}"
    )
    
    # G2: No changes = no commit needed
    if not changed_files:
        return True, None
    
    # Check if commit should be skipped
    if dry_run or no_commit or not commit_enabled:
        reason = "dry_run" if dry_run else ("no_commit" if no_commit else "disabled")
        logger.log(
            "commit", "commit", "skipped",
            reason=reason,
            changed_files=changed_files,
        )
        return True, None
    
    # C5: Verify commit_paths allowlist is non-empty
    if not commit_paths:
        logger.log(
            "commit", "commit", "fail",
            reason="empty_commit_paths",
            changed_files=changed_files,
        )
        return False, None
    
    # C5: Verify all changes are within allowlist
    disallowed = []
    for changed_file in changed_files:
        allowed = False
        for allowed_path in commit_paths:
            if changed_file.startswith(allowed_path):
                allowed = True
                break
        if not allowed:
            disallowed.append(changed_file)
    
    if disallowed:
        logger.log(
            "commit", "commit", "fail",
            reason="changes_outside_allowlist",
            disallowed_files=disallowed,
            changed_files=changed_files,
        )
        return False, None
    
    # Stage and commit
    message = commit_message_template.format(run_id=run_id)
    
    # Stage all changed files
    for changed_file in changed_files:
        result = subprocess.run(
            ["git", "add", changed_file],
            cwd=repo_root,
            capture_output=True,
        )
        if result.returncode != 0:
            logger.log(
                "commit", "commit", "fail",
                reason="git_add_failed",
                file=changed_file,
            )
            return False, None
    
    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.log(
            "commit", "commit", "fail",
            reason="git_commit_failed",
            stderr=result.stderr,
        )
        return False, None
    
    git_head_after = get_git_head()
    logger.log(
        "commit", "commit", "pass",
        git_head_after=git_head_after,
        changed_files=changed_files,
    )
    
    return True, git_head_after


def run_postflight(
    logger: DeterministicLogger,
    success: bool,
    git_head_before: str,
    git_head_after: str | None,
) -> None:
    """Final logging."""
    logger.log(
        "postflight", "postflight", "complete" if success else "failed",
        git_head_before=git_head_before,
        git_head_after=git_head_after,
    )


# --- Main Entry Point ---

def load_config(config_path: Path) -> dict[str, Any]:
    """Load YAML configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LifeOS Stewardship Runner - Deterministic pipeline CLI"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/steward_runner.yaml"),
        help="Config file path (default: config/steward_runner.yaml)",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Required. Unique identifier for this run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip commit even if enabled.",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Skip commit even if enabled.",
    )
    parser.add_argument(
        "--step",
        choices=["preflight", "tests", "validators", "corpus", "change_detect", "commit", "postflight"],
        help="Run single step only (for debugging).",
    )
    
    args = parser.parse_args()
    
    # Resolve repo root (A3)
    try:
        repo_root = get_repo_root()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    os.chdir(repo_root)
    
    # Load config
    config_path = repo_root / args.config
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1
    
    config = load_config(config_path)
    
    # Initialize logger
    logging_config = config.get("logging", {})
    log_dir = repo_root / logging_config.get("log_dir", "logs/steward_runner")
    streams_dir = repo_root / logging_config.get("streams_dir", "logs/steward_runner/streams")
    timestamps = config.get("determinism", {}).get("timestamps", False)
    
    logger = DeterministicLogger(log_dir, streams_dir, args.run_id, timestamps)
    
    # --- Pipeline Execution ---
    
    single_step = args.step
    success = True
    git_head_before = ""
    git_head_after = None
    changed_files: list[str] = []
    
    # PREFLIGHT
    if single_step is None or single_step == "preflight":
        success, git_head_before = run_preflight(config, logger, repo_root, args.run_id)
        if not success:
            run_postflight(logger, False, git_head_before, None)
            return 1
        if single_step == "preflight":
            return 0
    
    # TESTS
    if single_step is None or single_step == "tests":
        success = run_tests(config, logger, repo_root)
        if not success:
            run_postflight(logger, False, git_head_before, None)
            return 1
        if single_step == "tests":
            return 0
    
    # VALIDATORS
    if single_step is None or single_step == "validators":
        success = run_validators(config, logger, repo_root)
        if not success:
            run_postflight(logger, False, git_head_before, None)
            return 1
        if single_step == "validators":
            return 0
    
    # CORPUS
    if single_step is None or single_step == "corpus":
        success = run_corpus(config, logger, repo_root)
        if not success:
            run_postflight(logger, False, git_head_before, None)
            return 1
        if single_step == "corpus":
            return 0
    
    # CHANGE DETECT
    if single_step is None or single_step == "change_detect":
        changed_files = run_change_detect(config, logger)
        if single_step == "change_detect":
            return 0
    
    # COMMIT
    if single_step is None or single_step == "commit":
        success, git_head_after = run_commit(
            config, logger, repo_root, args.run_id,
            changed_files, args.dry_run, args.no_commit,
        )
        if not success:
            run_postflight(logger, False, git_head_before, None)
            return 1
        if single_step == "commit":
            return 0
    
    # POSTFLIGHT
    run_postflight(logger, True, git_head_before, git_head_after)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

### File: config/steward_runner.yaml

```yaml
# Stewardship Runner Configuration v0.1
# All paths are repo-root relative unless absolute.

# Repo root is canonicalized at runtime via: git rev-parse --show-toplevel
repo_root: "."

tests:
  # Command to run tests. Uses -q for reduced output noise per D3.
  command: ["python", "-m", "pytest", "-q", "-c", "pytest.ini"]
  # Test directories to include (D1)
  paths:
    - "runtime/tests"
    - "tests_doc"
    - "tests_recursive"

validators:
  # Ordered list of validator commands (E3: stop on first failure)
  commands:
    - ["python", "tools/validate_governance_index.py", "--repo-root", "."]
    - ["python", "-m", "doc_steward.cli", "dap-validate", "docs/"]
    - ["python", "-m", "doc_steward.cli", "index-check", "docs/", "docs/INDEX.md"]

corpus:
  # Corpus generation command (F1)
  command: ["python", "docs/scripts/generate_corpus.py"]
  # Expected outputs to verify after corpus step (F2)
  outputs_expected:
    - "docs/LifeOS_Universal_Corpus.md"

git:
  # If true, fail preflight if repo has uncommitted changes (C2)
  require_clean_start: true
  # Commit is DISABLED by default (C4). Must be explicitly enabled.
  commit_enabled: false
  # Commit message template. {run_id} is substituted.
  commit_message_template: "[steward] Autonomous run {run_id}"
  # Allowlist of paths that may be committed (C5)
  commit_paths:
    - "docs/"

logging:
  # Directory for JSONL logs (J2)
  log_dir: "logs/steward_runner"
  # Directory for content-addressed stdout/stderr streams (B4)
  streams_dir: "logs/steward_runner/streams"
  # Log format
  format: "jsonl"

determinism:
  # Run ID is required (C1)
  run_id_required: true
  # No timestamps in logs by default (B1)
  timestamps: false
```

---

### File: doc_steward/cli.py

```python
#!/usr/bin/env python3
"""
doc_steward CLI — Stable command-line interface for documentation validators.

Usage:
    python -m doc_steward.cli dap-validate <doc_root>
    python -m doc_steward.cli index-check <doc_root> <index_path>
    python -m doc_steward.cli link-check <doc_root>

Exit codes:
    0 - Validation passed
    1 - Validation failed
"""

import argparse
import sys
from pathlib import Path

from .dap_validator import check_dap_compliance
from .index_checker import check_index
from .link_checker import check_links


def cmd_dap_validate(args: argparse.Namespace) -> int:
    """Run DAP compliance validation."""
    doc_root = str(Path(args.doc_root).resolve())
    errors = check_dap_compliance(doc_root)
    
    if errors:
        print(f"[FAILED] DAP validation failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] DAP validation passed.")
        return 0


def cmd_index_check(args: argparse.Namespace) -> int:
    """Run index consistency check."""
    doc_root = str(Path(args.doc_root).resolve())
    index_path = str(Path(args.index_path).resolve())
    errors = check_index(doc_root, index_path)
    
    if errors:
        print(f"[FAILED] Index check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Index check passed.")
        return 0


def cmd_link_check(args: argparse.Namespace) -> int:
    """Run link validation."""
    doc_root = str(Path(args.doc_root).resolve())
    errors = check_links(doc_root)
    
    if errors:
        print(f"[FAILED] Link check failed ({len(errors)} errors):\n")
        for err in errors:
            print(f"  * {err}")
        return 1
    else:
        print("[PASSED] Link check passed.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="doc_steward.cli",
        description="LifeOS Documentation Steward CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # dap-validate
    p_dap = subparsers.add_parser("dap-validate", help="Check DAP naming compliance")
    p_dap.add_argument("doc_root", help="Root directory to validate")
    p_dap.set_defaults(func=cmd_dap_validate)
    
    # index-check
    p_idx = subparsers.add_parser("index-check", help="Check index consistency")
    p_idx.add_argument("doc_root", help="Root directory of documentation")
    p_idx.add_argument("index_path", help="Path to INDEX.md file")
    p_idx.set_defaults(func=cmd_index_check)
    
    # link-check
    p_link = subparsers.add_parser("link-check", help="Check for broken links")
    p_link.add_argument("doc_root", help="Root directory to validate")
    p_link.set_defaults(func=cmd_link_check)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

---

### File: tests_recursive/test_steward_runner.py

> [!NOTE]
> Full file is 529 lines. Key sections shown below. Full file available at [test_steward_runner.py](tests_recursive/test_steward_runner.py).

```python
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
def worktree(repo_root: Path, tmp_path: Path):
    """
    Create a git worktree for isolated testing (H1).
    
    Copies untracked/modified steward runner files to worktree so tests
    work before the runner is committed. Commits them so worktree is clean.
    """
    # ... fixture implementation ...


@pytest.fixture
def test_config(worktree: Path) -> Path:
    """Create a minimal test config in the worktree and commit it."""
    # ... fixture implementation ...


# --- Acceptance Tests ---

class TestAT01MissingRunId:
    """AT-01: Missing run-id fails closed."""
    def test_missing_run_id_fails(self, worktree, test_config): ...

class TestAT02DirtyRepoStart:
    """AT-02: Dirty repo start fails when required."""
    def test_dirty_repo_fails_with_require_clean(self, worktree, test_config): ...

class TestAT03TestsFailureBlocksDownstream:
    """AT-03: Tests failure blocks downstream."""
    def test_tests_failure_blocks_validators(self, worktree, test_config): ...

class TestAT04ValidatorFailureBlocksCorpus:
    """AT-04: Validator failure blocks corpus."""
    def test_validator_failure_blocks_corpus(self, worktree, test_config): ...

class TestAT05CorpusExpectedOutputsEnforced:
    """AT-05: Corpus expected outputs enforced."""
    def test_missing_corpus_output_fails(self, worktree, test_config): ...

class TestAT06NoChangeNoCommit:
    """AT-06: No change = no commit."""
    def test_no_change_exits_success(self, worktree, test_config): ...

class TestAT07ChangeWithinAllowedPathsCommits:
    """AT-07: Change within allowed paths commits once."""
    def test_allowed_change_commits(self, worktree, test_config): ...

class TestAT08ChangeOutsideAllowedPathsFails:
    """AT-08: Change outside allowed paths fails closed."""
    def test_disallowed_change_fails(self, worktree, test_config): ...

class TestAT09DryRunNeverCommits:
    """AT-09: Dry run never commits."""
    def test_dry_run_skips_commit(self, worktree, test_config): ...

class TestAT10LogDeterminism:
    """AT-10: Log determinism."""
    def test_logs_are_deterministic(self, worktree, test_config): ...
```

---

## End of Review Packet

