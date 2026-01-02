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
    
    def __init__(self, log_dir: Path, streams_dir: Path, run_id: str):
        self.log_dir = log_dir
        self.streams_dir = streams_dir
        self.run_id = run_id
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
        repo_root=str(repo_root),
        git_head_before=git_head,
    )
    return True, git_head


def run_tests(
    config: dict[str, Any],
    logger: DeterministicLogger,
    repo_root: Path,
) -> bool:
    """Run test suite with configured paths. Returns success."""
    tests_config = config.get("tests", {})
    command = tests_config.get("command", ["python", "-m", "pytest", "-q"])
    paths = tests_config.get("paths", [])
    
    # P0-1: Append test paths to command argv
    argv = list(command) + list(paths)
    
    exit_code, _, _ = run_command(argv, repo_root, logger, "tests")
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


def normalize_commit_path(path: str) -> tuple[str, str | None]:
    r"""
    Normalize a commit_paths entry per Commit Paths Contract.
    
    Returns (normalized_path, error_reason | None).
    
    Contract:
    - Entries ending with / are directory prefixes
    - Entries not ending with / are exact files
    - Bare names (no / or .) are interpreted as directory prefixes (normalized + logged)
    
    Fail-closed cases (error_reason is not None):
    - Absolute paths (Unix: /..., Windows: C:\, UNC: \\server, //server)
    - Path traversal (.. segment)
    - Current dir (. segment)
    - Glob patterns (* or ?)
    """
    # Normalize backslashes to forward slashes
    normalized = path.replace("\\", "/")
    
    # --- Fail-closed checks ---
    
    # UNC path (//server or after backslash normalization) - check BEFORE Unix
    if normalized.startswith("//"):
        return normalized, "absolute_path_unc"
    
    # Unix absolute path
    if normalized.startswith("/"):
        return normalized, "absolute_path_unix"
    
    # Windows drive absolute (C:/ or C:)
    if len(normalized) >= 2 and normalized[1] == ":":
        return normalized, "absolute_path_windows"
    
    # Glob patterns
    if "*" in normalized or "?" in normalized:
        return normalized, "glob_pattern"
    
    # Segment-based path traversal and current-dir check
    segments = normalized.rstrip("/").split("/")
    for segment in segments:
        if segment == "..":
            return normalized, "path_traversal"
        if segment == ".":
            return normalized, "current_dir_segment"
    
    # --- Normalization ---
    
    # Only normalize bare names (no / at all) that look like directories
    # Entries already containing / are treated as-is per contract
    if "/" not in path and not path.endswith("/"):
        # Bare name without extension → treat as directory prefix
        if "." not in path:
            normalized = normalized + "/"
    
    return normalized, None


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
    
    Implements Commit Paths Contract:
    - Directory prefixes (trailing /) or exact files
    - No globs, absolute paths, or path traversal
    - Uses git add -A for deterministic staging
    """
    git_config = config.get("git", {})
    commit_enabled = git_config.get("commit_enabled", False)
    raw_commit_paths = git_config.get("commit_paths", [])
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
    if not raw_commit_paths:
        logger.log(
            "commit", "commit", "fail",
            reason="empty_commit_paths",
            changed_files=changed_files,
        )
        return False, None
    
    # P1-2: Normalize and validate commit_paths
    commit_paths: list[str] = []
    for raw_path in raw_commit_paths:
        normalized, error_reason = normalize_commit_path(raw_path)
        if error_reason is not None:
            logger.log(
                "commit", "commit", "fail",
                reason="invalid_commit_path",
                error=error_reason,
                invalid_path=raw_path,
                normalized=normalized,
            )
            return False, None
        commit_paths.append(normalized)
    
    # C5: Verify all changes are within allowlist
    disallowed = []
    for changed_file in changed_files:
        allowed = False
        for allowed_path in commit_paths:
            # Directory match (starts with) or exact file match
            if allowed_path.endswith("/"):
                if changed_file.startswith(allowed_path):
                    allowed = True
                    break
            else:
                if changed_file == allowed_path:
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
    
    # P1-1: Stage using git add -A with allowlisted roots
    # Derive unique roots from commit_paths
    roots = sorted(set(commit_paths))
    
    message = commit_message_template.format(run_id=run_id)
    
    # Stage all changes under allowed roots
    add_cmd = ["git", "add", "-A", "--"] + roots
    result = subprocess.run(
        add_cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.log(
            "commit", "commit", "fail",
            reason="git_add_failed",
            stderr=result.stderr,
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
        commit_paths=commit_paths,
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
    
    logger = DeterministicLogger(log_dir, streams_dir, args.run_id)
    
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
