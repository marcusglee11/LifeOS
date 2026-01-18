---
packet_type: Review_Packet
mission_name: A1_A2_StepGate_Execution
version: 1.0
date: 2026-01-05
author: Antigravity
purpose: Evidence of A1/A2 StepGate completion (Tier-2 Green Baseline + Reactive Determinism)
scope: A1, A2, Tier-2 Tests, Reactive Logic
---

# Review Packet: A1/A2 StepGate Execution

## 1. Summary
Executed the A1/A2 StepGate requirements.
- **A1 (Tier-2 Green Baseline):** Achieved. `pytest` run completed with **452 passed**, 0 failed, 1 skipped, 1 xfailed.
- **A2 (Reactive Determinism):** Verified. `test_spec_conformance.py` asserts all determinism invariants.
- **Fix Applied:** Fixed a determinism bug in `steward_runner.py` where timestamps were not respecting the `determinism.timestamps: false` setting.

## 2. Issue Catalogue

| ID | Description | Resolution |
|----|-------------|------------|
| **BUG-001** | `steward_runner.py` generated variable timestamps even when disabled. | **FIXED**. Modified `DeterministicLogger` to accept `timestamps_enabled` flag and use fixed epoch timestamp when disabled. |

## 3. Acceptance Criteria

| ID | Criteria | Status | Evidence |
|----|----------|--------|----------|
| **A1** | Tier-2 Test Suite passes with 0 failures | **PASS** | `logs/tier2_green_evidence.log` (452 passed) |
| **A2** | Reactive v0.1 determinism tests exist & pass | **PASS** | `runtime/tests/test_reactive/test_spec_conformance.py` included in suite |
| **STW-1** | `LIFEOS_STATE.md` updated | **PASS** | See Appendix |
| **STW-2** | `docs/INDEX.md` timestamp updated | **PASS** | See Appendix |
| **STW-3** | `LifeOS_Strategic_Corpus.md` regenerated | **PASS** | See Appendix |

## 4. Non-Goals
- Fixing `xfailed` tests (deferred).
- Fixing `PytestCollectionWarning` (deferred).
- Creating new Reactive functionality (A2 was verification only).

---

# Appendix — Flattened Code Snapshots

### File: `scripts/steward_runner.py`
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

Log Determinism Contract (P1-B):
--------------------------------
- Timestamps: ISO 8601 UTC with Z suffix (e.g., "2026-01-02T14:30:00Z")
- File lists: Always sorted lexicographically before logging
- Git hashes: Logged for audit trail, never used in control flow
- Run-id: Externally provided, deterministic input
- No locale/timezone/ordering dependencies in decision logic
"""

import argparse
import datetime
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
    
    def __init__(self, log_dir: Path, streams_dir: Path, run_id: str, timestamps_enabled: bool = True):
        self.log_dir = log_dir
        self.streams_dir = streams_dir
        self.run_id = run_id
        self.timestamps_enabled = timestamps_enabled
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
        
        if self.timestamps_enabled:
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            ts = "1970-01-01T00:00:00Z"  # Deterministic fixed timestamp
            
        record: dict[str, Any] = {
            "timestamp": ts,
            "run_id": self.run_id,
            "event": event,
            "step": step,
            "status": status,
        }
        record.update(kwargs)
        
        # P1-B: Enforce sorted file lists for determinism
        for key in ("files", "changed_files", "staged_files", "validated_files", "unexpected_files", "disallowed_files", "commit_paths"):
            if key in record and isinstance(record[key], list):
                record[key] = sorted(record[key])
        
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
    """
    # Keep original for error returns (P2-C)
    original = path
    # Normalize backslashes to forward slashes
    normalized = path.replace("\\", "/")
    
    # --- Fail-closed checks ---
    
    # URL encoded chars rejection (P2-B)
    if "%" in normalized:
        return original, "url_encoded_chars"
    
    # UNC path (//server or after backslash normalization) - check BEFORE Unix
    if normalized.startswith("//"):
        return original, "absolute_path_unc"
    
    # Unix absolute path
    if normalized.startswith("/"):
        return original, "absolute_path_unix"
    
    # Windows drive absolute (C:/ or C:)
    if len(normalized) >= 2 and normalized[1] == ":":
        return original, "absolute_path_windows"
    
    # Glob patterns
    if "*" in normalized or "?" in normalized:
        return original, "glob_pattern"
    
    # Segment-based path traversal and current-dir check
    segments = normalized.rstrip("/").split("/")
    for segment in segments:
        if segment == "..":
            return original, "path_traversal"
        if segment == ".":
            return original, "current_dir_segment"
    
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
    # P1-A: Re-check for dirty state before commit to prevent race conditions
    current_changed = get_changed_files()
    unexpected = set(current_changed) - set(changed_files)
    if unexpected:
        logger.log(
            "commit", "commit", "fail",
            reason="repo_dirty_during_run",
            unexpected_files=list(unexpected),
        )
        return False, None

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
    
    # P1-D: Mutually exclusive commit control
    commit_group = parser.add_mutually_exclusive_group()
    commit_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all stages but skip git commit (default behavior)",
    )
    commit_group.add_argument(
        "--commit",
        action="store_true",
        help="Actually commit changes (explicit opt-in required)",
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
    
    logger = DeterministicLogger(
        log_dir, 
        streams_dir, 
        args.run_id,
        timestamps_enabled=config.get("determinism", {}).get("timestamps", True)
    )
    
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
        # P1-D: Default is dry-run. Commit requires explicit --commit flag.
        actually_commit = args.commit
        # dry_run arg is redundant if commit arg is not present, but for compatibility/clarity:
        dry_run = args.dry_run or (not actually_commit)
        
        success, git_head_after = run_commit(
            config, logger, repo_root, args.run_id,
            changed_files, dry_run, False, # no_commit removed, logic handled by dry_run
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

### File: `docs/11_admin/LIFEOS_STATE.md`
```markdown
# LIFEOS STATE — Last updated: 2026-01-04 by Antigravity

## Contract
- Repo is system-of-record; this file is CEO-facing cross-agent sync capsule
- Sufficient to restart session without additional context dumps
- DONE requires evidence refs; "assuming done" forbidden
- WIP max 2 enforced
- CEO decisions isolated and capped (max 3)

## Current Focus

**Transitioning to: Reactive Planner v0.2 / Mission Registry v0.2**

## Active WIP (max 2)

- **[WIP-1]** Planning: Mission Registry v0.2 (Synthesis & Validation logic) | Evidence: PENDING
- **[WIP-2]** OpenCode Integration Phase 1 (governance service skeleton) | Evidence: PENDING

## Blockers

- None

## CEO Decisions Needed (max 3)

- None

## Thread Kickoff Block (optional convenience)

\`\`\`
Focus: OpenCode Phase 1 / Mission Registry v0.2 planning
WIP: Mission Registry v0.2, OpenCode Integration Phase 1
Blockers: None
Next Action: Start OpenCode governance service skeleton
Refs:
- docs/11_admin/LIFEOS_STATE.md
- docs/02_protocols/Build_Handoff_Protocol_v1.0.md
- docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md
\`\`\`

## Next Actions

1. **[DONE]** Draft Reactive Task Layer v0.1 spec | Evidence: \`docs/01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md\`
2. **[DONE]** OpenCode Phase 0: API Connectivity | Evidence: \`artifacts/review_packets/OpenCode_CI_Proof.md\`
3. **[DONE]** OpenCode CI Integration | Evidence: \`commit 2026-01-03 (GitHub Action)\`
4. **[DONE]** Mission Registry v0.1 | Evidence: \`docs/01_governance/Council_Ruling_Mission_Registry_v0.1.md\`
5. **[APPROVED]** Build Handoff Protocol v1.0 | Evidence: \`docs/01_governance/Council_Ruling_Build_Handoff_v1.0.md\`
6. **[DONE]** Reactive v0.1 tests for determinism | Evidence: \`runtime/tests/test_reactive/test_spec_conformance.py\` + Review Packet A1/A2
7. **[DONE]** Run Tier-2 test suite and lock green baseline | Evidence: \`logs/tier2_green_evidence.log\` + Review Packet A1/A2
8. **OpenCode Phase 1**: Governance service skeleton + doc steward config
9. **[DONE]** Steward promotional assets (An_OS_for_Life.mp4) | Evidence: \`docs/INDEX.md\`, \`Review_Packet_Stewardship_Promotional_Assets_v1.0.md\`

## References (max 10)

- \`docs/03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md\`: Tier progression roadmap
- \`docs/03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md\`: Phase 1 & 2 complete
- \`docs/02_protocols/lifeos_packet_schemas_v1.yaml\`: Packet schemas
- \`docs/03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md\`: Entrypoint whitelist
- \`docs/01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md\`: Reactive Layer signoff
```

### File: `docs/INDEX.md`
```markdown
# LifeOS Documentation Index — Last updated: 2026-01-05 18:25 UTC+11:00  
**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

\`\`\`
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
\`\`\`

---

## Strategic Context

| Document | Purpose |
|----------|---------|
| [LifeOS_Strategic_Corpus.md](./LifeOS_Strategic_Corpus.md) | **Primary Context for the LifeOS Project** |

---

## 00_admin — Project Admin (Thin Control Plane)

| Document | Purpose |
|----------|---------|
| [LIFEOS_STATE.md](./11_admin/LIFEOS_STATE.md) | **Single source of truth** — Current focus, WIP, blockers, next actions |
| [BACKLOG.md](./11_admin/BACKLOG.md) | Actionable backlog (Now/Next/Later) — target ≤40 items |
| [DECISIONS.md](./11_admin/DECISIONS.md) | Append-only decision log (low volume) |
| [INBOX.md](./11_admin/INBOX.md) | Raw capture scratchpad for triage |

---

## 00_foundations — Core Principles

| Document | Purpose |
|----------|---------|
| [LifeOS_Constitution_v2.0.md](./00_foundations/LifeOS_Constitution_v2.0.md) | **Supreme governing document** — Raison d'être, invariants, principles |
| [Anti_Failure_Operational_Packet_v0.1.md](./00_foundations/Anti_Failure_Operational_Packet_v0.1.md) | Anti-failure mechanisms, human preservation, workflow constraints |
| [Architecture_Skeleton_v1.0.md](./00_foundations/Architecture_Skeleton_v1.0.md) | High-level conceptual architecture (CEO/COO/Worker layers) |
| [ARCH_Future_Build_Automation_Operating_Model_v0.2.md](./00_foundations/ARCH_Future_Build_Automation_Operating_Model_v0.2.md) | **Architecture Proposal** — Future Build Automation Operating Model v0.2 |

---

## 01_governance — Governance & Contracts

### Core Governance
| Document | Purpose |
|----------|---------|
| [COO_Operating_Contract_v1.0.md](./01_governance/COO_Operating_Contract_v1.0.md) | CEO/COO role boundaries and interaction rules |
| [AgentConstitution_GEMINI_Template_v1.0.md](./01_governance/AgentConstitution_GEMINI_Template_v1.0.md) | Template for agent GEMINI.md files |

### Council & Review
| Document | Purpose |
|----------|---------|
| [Council_Invocation_Runtime_Binding_Spec_v1.0.md](./01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md) | Council invocation and runtime binding |
| [Antigravity_Council_Review_Packet_Spec_v1.0.md](./01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md) | Council review packet format |
| [ALIGNMENT_REVIEW_TEMPLATE_v1.0.md](./01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md) | Monthly/quarterly alignment review template |

### Policies & Logs
| Document | Purpose |
|----------|---------|
| [COO_Expectations_Log_v1.0.md](./01_governance/COO_Expectations_Log_v1.0.md) | Working preferences and behavioral refinements |
| [Antigrav_Output_Hygiene_Policy_v0.1.md](./01_governance/Antigrav_Output_Hygiene_Policy_v0.1.md) | Output path rules for Antigravity |

### Historical Rulings
| Document | Purpose |
|----------|---------|
| [Tier1_Hardening_Council_Ruling_v0.1.md](./01_governance/Tier1_Hardening_Council_Ruling_v0.1.md) | Historical: Tier-1 ratification ruling |
| [Tier1_Tier2_Activation_Ruling_v0.2.md](./01_governance/Tier1_Tier2_Activation_Ruling_v0.2.md) | Historical: Tier-2 activation ruling |
| [Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md](./01_governance/Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md) | Historical: Tier transition conditions |
| [Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md](./01_governance/Tier2_Completion_Tier2.5_Activation_Ruling_v1.0.md) | Historical: Tier-2.5 activation ruling |
| [Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md](./01_governance/Tier3_Reactive_Task_Layer_Council_Ruling_v0.1.md) | **Active**: Reactive Task Layer v0.1 Signoff |
| [Council_Review_Stewardship_Runner_v1.0.md](./01_governance/Council_Review_Stewardship_Runner_v1.0.md) | **Approved**: Stewardship Runner cleared for agent-triggered runs |
| [Council_Ruling_Build_Handoff_v1.0.md](./01_governance/Council_Ruling_Build_Handoff_v1.0.md) | **Approved**: Build Handoff Protocol v1.0 activation-canonical |

---

## 02_protocols — Protocols & Agent Communication

### Core Protocols
| Document | Purpose |
|----------|---------|
| [Governance_Protocol_v1.0.md](./02_protocols/Governance_Protocol_v1.0.md) | Envelopes, escalation rules, council model |
| [Document_Steward_Protocol_v1.0.md](./02_protocols/Document_Steward_Protocol_v1.0.md) | Document creation, indexing, GitHub/Drive sync |
| [Deterministic_Artefact_Protocol_v2.0.md](./02_protocols/Deterministic_Artefact_Protocol_v2.0.md) | DAP — artefact creation, versioning, and storage rules |
| [Build_Artifact_Protocol_v1.0.md](./02_protocols/Build_Artifact_Protocol_v1.0.md) | **NEW** — Formal schemas/templates for Plans, Review Packets, Walkthroughs, etc. |
| [Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md](./02_protocols/Tier-2_API_Evolution_and_Versioning_Strategy_v1.0.md) | Tier-2 API Versioning, Deprecation, and Compatibility Rules |
| [Build_Handoff_Protocol_v1.0.md](./02_protocols/Build_Handoff_Protocol_v1.0.md) | Messaging & handoff architecture for agent coordination |

### Council Protocols
| Document | Purpose |
|----------|---------|
| [Council_Protocol_v1.1.md](./02_protocols/Council_Protocol_v1.1.md) | **Canonical** — Council review procedure, modes, topologies |
| [AI_Council_Procedural_Spec_v1.0.md](./02_protocols/AI_Council_Procedural_Spec_v1.0.md) | Runbook for executing Council Protocol v1.1 |
| [Council_Context_Pack_Schema_v0.2.md](./02_protocols/Council_Context_Pack_Schema_v0.2.md) | CCP template schema for council reviews |

### Packet & Artifact Schemas
| Document | Purpose |
|----------|---------|
| [lifeos_packet_schemas_v1.yaml](./02_protocols/lifeos_packet_schemas_v1.yaml) | Agent packet schema definitions (13 packet types) |
| [lifeos_packet_templates_v1.yaml](./02_protocols/lifeos_packet_templates_v1.yaml) | Ready-to-use packet templates |
| [build_artifact_schemas_v1.yaml](./02_protocols/build_artifact_schemas_v1.yaml) | **NEW** — Build artifact schema definitions (6 artifact types) |
| [templates/](./02_protocols/templates/) | **NEW** — Markdown templates for all artifact types |
| [example_converted_antigravity_packet.yaml](./02_protocols/example_converted_antigravity_packet.yaml) | Example: converted Antigravity review packet |

---

## 03_runtime — Runtime Specification

### Core Specs
| Document | Purpose |
|----------|---------|
| [COO_Runtime_Spec_v1.0.md](./03_runtime/COO_Runtime_Spec_v1.0.md) | Mechanical execution contract, FSM, determinism rules |
| [COO_Runtime_Implementation_Packet_v1.0.md](./03_runtime/COO_Runtime_Implementation_Packet_v1.0.md) | Implementation details for Antigravity |
| [COO_Runtime_Core_Spec_v1.0.md](./03_runtime/COO_Runtime_Core_Spec_v1.0.md) | Extended core specification |
| [COO_Runtime_Spec_Index_v1.0.md](./03_runtime/COO_Runtime_Spec_Index_v1.0.md) | Spec index and patch log |

### Roadmaps & Plans
| Document | Purpose |
|----------|---------|
| [LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md](./03_runtime/LifeOS_Programme_Roadmap_CoreFuelPlumbing_v1.0.md) | **Current roadmap** — Core/Fuel/Plumbing tracks |
| [LifeOS_Recursive_Improvement_Architecture_v0.2.md](./03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md) | Recursive improvement architecture |
| [LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md](./03_runtime/LifeOS_Router_and_Executor_Adapter_Spec_v0.1.md) | Future router and executor adapter spec |

### Work Plans & Fix Packs
| Document | Purpose |
|----------|---------|
| [Hardening_Backlog_v0.1.md](./03_runtime/Hardening_Backlog_v0.1.md) | Hardening work backlog |
| [Tier1_Hardening_Work_Plan_v0.1.md](./03_runtime/Tier1_Hardening_Work_Plan_v0.1.md) | Tier-1 hardening work plan |
| [Tier2.5_Unified_Fix_Plan_v1.0.md](./03_runtime/Tier2.5_Unified_Fix_Plan_v1.0.md) | Tier-2.5 unified fix plan |
| [F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md](./03_runtime/F3_Tier2.5_Activation_Conditions_Checklist_v1.0.md) | Tier-2.5 activation conditions checklist (F3) |
| [F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md](./03_runtime/F4_Tier2.5_Deactivation_Rollback_Conditions_v1.0.md) | Tier-2.5 deactivation and rollback conditions (F4) |
| [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](./03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) | Runtime↔Antigrav mission protocol (F7) |
| [Runtime_Hardening_Fix_Pack_v0.1.md](./03_runtime/Runtime_Hardening_Fix_Pack_v0.1.md) | Runtime hardening fix pack |
| [fixpacks/FP-4x_Implementation_Packet_v0.1.md](./03_runtime/fixpacks/FP-4x_Implementation_Packet_v0.1.md) | FP-4x implementation |

### Templates & Tools
| Document | Purpose |
|----------|---------|
| [BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md](./03_runtime/BUILD_STARTER_PROMPT_TEMPLATE_v1.0.md) | Build starter prompt template |
| [CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md](./03_runtime/CODE_REVIEW_PROMPT_TEMPLATE_v1.0.md) | Code review prompt template |
| [COO_Runtime_Walkthrough_v1.0.md](./03_runtime/COO_Runtime_Walkthrough_v1.0.md) | Runtime walkthrough |
| [COO_Runtime_Clean_Build_Spec_v1.1.md](./03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md) | Clean build specification |

### Other
| Document | Purpose |
|----------|---------|
| [Automation_Proposal_v0.1.md](./03_runtime/Automation_Proposal_v0.1.md) | Automation proposal |
| [Runtime_Complexity_Constraints_v0.1.md](./03_runtime/Runtime_Complexity_Constraints_v0.1.md) | Complexity constraints |
| [README_Recursive_Kernel_v0.1.md](./03_runtime/README_Recursive_Kernel_v0.1.md) | Recursive kernel readme |

---

## 07_productisation — Productisation & Marketing

| Document | Purpose |
|----------|---------|
| [An_OS_for_Life.mp4](./07_productisation/assets/An_OS_for_Life.mp4) | **Promotional Video** — An introduction to LifeOS |

---

## internal — Internal Reports

| Document | Purpose |
|----------|---------|
| [OpenCode_Phase0_Completion_Report_v1.0.md](./internal/OpenCode_Phase0_Completion_Report_v1.0.md) | OpenCode Phase 0 API connectivity validation — PASSED |

---

## 99_archive — Historical Documents

Archived documents are in \`99_archive/\`. Key locations:
- \`99_archive/superseded_by_constitution_v2/\` — Documents superseded by Constitution v2.0
- \`99_archive/legacy_structures/\` — Legacy governance and specs

---

## Other Directories

| Directory | Contents |
|-----------|----------|
| \`04_project_builder/\` | Project builder specs |
| \`05_agents/\` | Agent architecture |
| \`06_user_surface/\` | User surface specs |
| \`08_manuals/\` | Manuals |
| \`09_prompts/v1.0/\` | Legacy v1.0 prompt templates |
| \`09_prompts/v1.2/\` | **Current** — Council role prompts (Chair, Co-Chair, 10 reviewer seats) |
| \`10_meta/\` | Meta documents, reviews, tasks |
```

### File: `docs/LifeOS_Strategic_Corpus.md` (Header Only — Autogenerated)
*> Note: This file consumes ~275KB. Per Smart Failure protocols, only the header is included here to verify regeneration. The full file exists on disk.*
```markdown
# ⚡ LifeOS Strategic Dashboard
**Generated:** 2026-01-05 21:19
**Current Tier:** Tier-2.5 (Activated)
**Active Roadmap Phase:** Core / Fuel / Plumbing (See Roadmap)
**Current Governance Mode:** Phase 2 — Operational Autonomy (Target State)
**Purpose:** High-level strategic reasoning and catch-up context.
**Authority Chain:** Constitution (Supreme) → Governance → Runtime (Mechanical)

---

# File: 00_foundations/LifeOS_Constitution_v2.0.md
...
```
