"""
Run Controller - Mission lifecycle management with safety checks.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.6

Fail-Closed Boundary:
Git command failures and filesystem errors are wrapped into GitCommandError,
RunLockError, or StaleLockDetected. No OSError propagates to callers.

See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Kill switch path per v0.3 spec §5.6.1
KILL_SWITCH_PATH = "STOP_AUTONOMY"

# Run lock path per v0.3 spec §5.6.2
LOCK_FILE_PATH = ".lifeos_run_lock"


class KillSwitchActive(Exception):
    """Raised when STOP_AUTONOMY file is detected."""
    
    def __init__(self, detected_at: str):
        self.detected_at = detected_at
        super().__init__(
            f"Kill switch (STOP_AUTONOMY) detected at {detected_at}. "
            "Autonomous operations halted."
        )


class RunLockError(Exception):
    """Base exception for run lock errors."""
    pass


class RunLockHeld(RunLockError):
    """Another process holds the run lock."""
    
    def __init__(self, holder_pid: int, holder_run_id: str):
        self.holder_pid = holder_pid
        self.holder_run_id = holder_run_id
        super().__init__(
            f"Run lock held by PID {holder_pid} (run_id={holder_run_id}). "
            "Only one mission may execute at a time."
        )


class StaleLockDetected(RunLockError):
    """Lock file exists but owning process is dead."""
    
    def __init__(self, stale_pid: int, stale_run_id: str):
        self.stale_pid = stale_pid
        self.stale_run_id = stale_run_id
        super().__init__(
            f"Stale lock detected: PID {stale_pid} (run_id={stale_run_id}) is dead. "
            "Crash recovery required."
        )


class RepoDirtyError(Exception):
    """Repository has uncommitted or untracked changes."""
    
    def __init__(self, status_output: str, untracked_output: str):
        self.status_output = status_output
        self.untracked_output = untracked_output
        super().__init__(
            "Repository is not clean. Cannot proceed with mission.\n"
            f"git status --porcelain:\n{status_output}\n"
            f"Untracked files:\n{untracked_output}"
        )


class CanonSpineError(Exception):
    """Canon spine validation failed."""
    
    def __init__(self, output: str):
        self.output = output
        super().__init__(f"Canon spine validation failed:\n{output}")


class GitCommandError(Exception):
    """
    Raised when a git command fails.
    
    [v0.3 Fail-Closed]: Git executable missing OR returncode != 0 => HALT.
    """
    
    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Git command failed (fail-closed HALT).\n"
            f"Command: {command}\n"
            f"Return code: {returncode}\n"
            f"Stderr: {stderr}"
        )


@dataclass
class RunLock:
    """Lock file contents per v0.3 spec §5.6.2."""
    
    run_id: str
    pid: int
    started_at: str
    mission_type: str


def check_kill_switch(repo_root: Optional[Path] = None) -> bool:
    """
    Check if kill switch is active.
    
    Per v0.3 spec §5.6.1:
    Returns True if STOP_AUTONOMY file exists.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    kill_switch_path = repo_root / KILL_SWITCH_PATH
    return kill_switch_path.exists()


def _is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is alive."""
    if sys.platform == "win32":
        # Windows: use tasklist
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
            )
            return str(pid) in result.stdout
        except Exception:
            return True  # Assume alive if check fails (fail-closed)
    else:
        # POSIX: use kill 0
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _read_lock_file(lock_path: Path) -> Optional[RunLock]:
    """Read and parse lock file."""
    if not lock_path.exists():
        return None
    
    try:
        content = lock_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        data = {}
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
        
        return RunLock(
            run_id=data.get("run_id", "unknown"),
            pid=int(data.get("pid", 0)),
            started_at=data.get("started_at", ""),
            mission_type=data.get("mission_type", "unknown"),
        )
    except Exception:
        return None


def _write_lock_file(lock_path: Path, lock: RunLock) -> None:
    """Write lock file."""
    content = (
        f"run_id={lock.run_id}\n"
        f"pid={lock.pid}\n"
        f"started_at={lock.started_at}\n"
        f"mission_type={lock.mission_type}\n"
    )
    lock_path.write_text(content, encoding="utf-8")


def acquire_run_lock(
    run_id: str,
    mission_type: str,
    repo_root: Optional[Path] = None,
) -> bool:
    """
    Attempt to acquire exclusive run lock.
    
    Per v0.3 spec §5.6.2:
    1. Check if lock file exists
    2. If exists, check if owning process is still alive
    3. If process dead, raise StaleLockDetected (crash recovery)
    4. If process alive, raise RunLockHeld
    5. If no lock, create lock file
    
    Returns True if lock acquired.
    Raises RunLockHeld or StaleLockDetected on failure.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    lock_path = repo_root / LOCK_FILE_PATH
    existing = _read_lock_file(lock_path)
    
    if existing is not None:
        if _is_process_alive(existing.pid):
            raise RunLockHeld(existing.pid, existing.run_id)
        else:
            raise StaleLockDetected(existing.pid, existing.run_id)
    
    # Create new lock
    lock = RunLock(
        run_id=run_id,
        pid=os.getpid(),
        started_at=datetime.now(timezone.utc).isoformat(),
        mission_type=mission_type,
    )
    _write_lock_file(lock_path, lock)
    return True


def release_run_lock(
    run_id: str,
    repo_root: Optional[Path] = None,
) -> bool:
    """
    Release run lock after mission completion.
    
    Per v0.3 spec §5.6.2:
    1. Verify we own the lock (run_id matches)
    2. Delete lock file
    
    Returns True on success, False if we don't own the lock.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    lock_path = repo_root / LOCK_FILE_PATH
    existing = _read_lock_file(lock_path)
    
    if existing is None:
        return False  # No lock to release
    
    if existing.run_id != run_id:
        return False  # We don't own this lock
    
    lock_path.unlink(missing_ok=True)
    return True


def run_git_command(args: list[str], cwd: Optional[Path] = None) -> bytes:
    """
    Execute a git command and return stdout.
    
    Per v0.3 Fail-Closed: Git failure (missing executable or non-zero return) => HALT.
    
    Args:
        args: Git command arguments (e.g., ["diff", "HEAD"])
        cwd: Working directory (defaults to current directory)
    
    Returns:
        stdout as bytes
    
    Raises:
        GitCommandError: If git command fails or executable not found
    """
    if cwd is None:
        cwd = Path.cwd()
    
    cmd = ["git"] + args
    cmd_str = " ".join(cmd)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=cwd,
        )
    except FileNotFoundError as e:
        raise GitCommandError(cmd_str, -1, f"git not found: {e}")
    
    if result.returncode != 0:
        raise GitCommandError(
            cmd_str,
            result.returncode,
            result.stderr.decode('utf-8', errors='replace'),
        )
    
    return result.stdout


def verify_repo_clean(repo_root: Optional[Path] = None) -> None:
    """
    Verify repository is in clean state.
    
    Per v0.3 spec §5.6.3:
    1. git status --porcelain must return empty
    2. git ls-files --others --exclude-standard must return empty
    
    [v0.3 Fail-Closed]: Git failure (missing executable or non-zero return) => HALT.
    
    Raises:
        GitCommandError: If git command fails
        RepoDirtyError: If not clean
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    # Check for staged/unstaged changes
    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except FileNotFoundError as e:
        raise GitCommandError("git status --porcelain", -1, f"git not found: {e}")
    
    if status_result.returncode != 0:
        raise GitCommandError(
            "git status --porcelain",
            status_result.returncode,
            status_result.stderr,
        )
    status_output = status_result.stdout.strip()
    
    # Check for untracked files
    try:
        untracked_result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except FileNotFoundError as e:
        raise GitCommandError("git ls-files", -1, f"git not found: {e}")
    
    if untracked_result.returncode != 0:
        raise GitCommandError(
            "git ls-files --others --exclude-standard",
            untracked_result.returncode,
            untracked_result.stderr,
        )
    untracked_output = untracked_result.stdout.strip()
    
    if status_output or untracked_output:
        raise RepoDirtyError(status_output, untracked_output)


def verify_canon_spine(repo_root: Optional[Path] = None) -> None:
    """
    Verify the integrity of the Canonical Spine.
    
    Executes scripts/validate_canon_spine.py.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    script_path = repo_root / "scripts" / "validate_canon_spine.py"
    if not script_path.exists():
        raise CanonSpineError(f"Validator script missing: {script_path}")
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    
    if result.returncode != 0:
        raise CanonSpineError(result.stdout or result.stderr)


@dataclass
class StartupResult:
    """Result of mission startup sequence."""
    
    success: bool
    run_id: str
    baseline_commit: str
    message: str = ""


def mission_startup_sequence(
    run_id: str,
    mission_type: str,
    repo_root: Optional[Path] = None,
) -> StartupResult:
    """
    Race-safe startup sequence.
    
    Per v0.3 spec §5.6.1:
    1. CHECK STOP_AUTONOMY (first check)
    2. ACQUIRE single-run lock
    3. RE-CHECK STOP_AUTONOMY (second check, post-lock)
    4. PROCEED with mission
    
    This double-check pattern eliminates TOCTOU race conditions.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    # Step 1: First kill switch check
    if check_kill_switch(repo_root):
        raise KillSwitchActive("pre-lock check")
    
    # Step 2: Acquire lock
    acquire_run_lock(run_id, mission_type, repo_root)
    
    try:
        # Step 3: Second kill switch check (post-lock)
        if check_kill_switch(repo_root):
            # Release lock before raising
            release_run_lock(run_id, repo_root)
            raise KillSwitchActive("post-lock check")
        
        # Step 4: Verify clean workspace
        verify_repo_clean(repo_root)
        
        # Step 5: Verify Canon Spine integrity
        verify_canon_spine(repo_root)
        
        # Get baseline commit [v0.3 Fail-Closed]
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=repo_root,
            )
        except FileNotFoundError as e:
            raise GitCommandError("git rev-parse HEAD", -1, f"git not found: {e}")
        
        if result.returncode != 0:
            raise GitCommandError(
                "git rev-parse HEAD",
                result.returncode,
                result.stderr,
            )
        baseline_commit = result.stdout.strip()
        
        return StartupResult(
            success=True,
            run_id=run_id,
            baseline_commit=baseline_commit,
            message="Startup sequence completed successfully",
        )
    
    except Exception:
        # Release lock on any failure
        release_run_lock(run_id, repo_root)
        raise
