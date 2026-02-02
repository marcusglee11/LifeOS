"""
Tests for Run Controller - Kill switch, lock, and repo clean checks.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.6
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from runtime.orchestration.run_controller import (
    KILL_SWITCH_PATH,
    LOCK_FILE_PATH,
    KillSwitchActive,
    RunLockHeld,
    StaleLockDetected,
    RepoDirtyError,
    CanonSpineError,
    GitCommandError,
    check_kill_switch,
    acquire_run_lock,
    release_run_lock,
    verify_repo_clean,
    verify_canon_spine,
    mission_startup_sequence,
)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary directory simulating a git repo."""
    # Initialize minimal git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main")
    return tmp_path


class TestKillSwitch:
    """Tests for kill switch ordering per v0.3 §5.6.1."""
    
    def test_kill_switch_not_present(self, temp_repo):
        """Should return False when STOP_AUTONOMY does not exist."""
        assert check_kill_switch(temp_repo) is False
    
    def test_kill_switch_present(self, temp_repo):
        """Should return True when STOP_AUTONOMY exists."""
        (temp_repo / KILL_SWITCH_PATH).touch()
        assert check_kill_switch(temp_repo) is True
    
    def test_mission_startup_halts_before_lock_when_kill_switch_present(self, temp_repo):
        """
        Per v0.3 §5.6.1: If STOP_AUTONOMY exists at first check,
        should halt immediately without acquiring lock.
        """
        (temp_repo / KILL_SWITCH_PATH).touch()
        # Mock script existence to pass the Canon Spine gate
        script_dir = temp_repo / "scripts"
        script_dir.mkdir(exist_ok=True)
        (script_dir / "validate_canon_spine.py").touch()
        
        with pytest.raises(KillSwitchActive) as exc_info:
            mission_startup_sequence("test-run", "test", temp_repo)
        
        assert "pre-lock check" in str(exc_info.value)
        # Lock should NOT have been created
        assert not (temp_repo / LOCK_FILE_PATH).exists()
    
    def test_mission_startup_halts_after_lock_if_kill_switch_created_between_checks(self, temp_repo):
        """
        Per v0.3 §5.6.1: Double-check pattern eliminates TOCTOU race.
        If STOP_AUTONOMY appears between first check and second check,
        should still halt and release lock.
        """
        # Patch check_kill_switch to return False first, then True
        call_count = [0]
        original_check = check_kill_switch
        
        def mock_check(repo_root=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return False  # First check passes
            # Create the file for second check
            (temp_repo / KILL_SWITCH_PATH).touch()
            return True
        
        # Mock script existence
        script_dir = temp_repo / "scripts"
        script_dir.mkdir(exist_ok=True)
        (script_dir / "validate_canon_spine.py").touch()
        
        with patch("runtime.orchestration.run_controller.check_kill_switch", mock_check):
            with pytest.raises(KillSwitchActive) as exc_info:
                mission_startup_sequence("test-run", "test", temp_repo)
        
        assert "post-lock check" in str(exc_info.value)
        # Lock should have been released
        assert not (temp_repo / LOCK_FILE_PATH).exists()


class TestRunLock:
    """Tests for single-run lock per v0.3 §5.6.2."""
    
    def test_acquire_lock_success(self, temp_repo):
        """Should successfully acquire lock when none exists."""
        result = acquire_run_lock("run-1", "test", temp_repo)
        assert result is True
        assert (temp_repo / LOCK_FILE_PATH).exists()
    
    def test_acquire_lock_fails_when_held(self, temp_repo):
        """Should fail when lock is held by another process."""
        # Create a lock with current PID (simulates another process holding lock)
        lock_path = temp_repo / LOCK_FILE_PATH
        lock_path.write_text(f"run_id=run-1\npid={os.getpid()}\nstarted_at=2026-01-08\nmission_type=test\n")
        
        with pytest.raises(RunLockHeld) as exc_info:
            acquire_run_lock("run-2", "test", temp_repo)
        
        assert exc_info.value.holder_run_id == "run-1"
    
    def test_stale_lock_detection(self, temp_repo):
        """Should detect stale lock when owning process is dead."""
        # Create a lock with a definitely-dead PID
        lock_path = temp_repo / LOCK_FILE_PATH
        lock_path.write_text("run_id=run-1\npid=999999999\nstarted_at=2026-01-08\nmission_type=test\n")
        
        with pytest.raises(StaleLockDetected) as exc_info:
            acquire_run_lock("run-2", "test", temp_repo)
        
        assert exc_info.value.stale_pid == 999999999
    
    def test_release_lock_success(self, temp_repo):
        """Should release lock when we own it."""
        acquire_run_lock("run-1", "test", temp_repo)
        assert (temp_repo / LOCK_FILE_PATH).exists()
        
        result = release_run_lock("run-1", temp_repo)
        assert result is True
        assert not (temp_repo / LOCK_FILE_PATH).exists()
    
    def test_release_lock_fails_if_not_owner(self, temp_repo):
        """Should fail to release lock if run_id doesn't match."""
        acquire_run_lock("run-1", "test", temp_repo)
        
        result = release_run_lock("run-2", temp_repo)
        assert result is False
        # Lock should still exist
        assert (temp_repo / LOCK_FILE_PATH).exists()


class TestRepoClean:
    """Tests for repo clean preconditions per v0.3 §5.6.3."""
    
    def test_repo_clean_passes_on_clean_repo(self, temp_repo):
        """Should pass when git status is clean."""
        # Mock subprocess to return empty output with returncode 0
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            verify_repo_clean(temp_repo)  # Should not raise
    
    def test_repo_dirty_raises_on_staged_changes(self, temp_repo):
        """Should raise when there are staged changes."""
        with patch("subprocess.run") as mock_run:
            def mock_subprocess(*args, **kwargs):
                class Result:
                    returncode = 0
                r = Result()
                if "status" in args[0]:
                    r.stdout = "M  some_file.py"
                else:
                    r.stdout = ""
                return r
            mock_run.side_effect = mock_subprocess
            
            with pytest.raises(RepoDirtyError) as exc_info:
                verify_repo_clean(temp_repo)
            
            assert "some_file.py" in str(exc_info.value)
    
    def test_repo_dirty_raises_on_untracked_files(self, temp_repo):
        """Should raise when there are untracked files."""
        with patch("subprocess.run") as mock_run:
            def mock_subprocess(*args, **kwargs):
                class Result:
                    returncode = 0
                r = Result()
                if "ls-files" in args[0]:
                    r.stdout = "new_untracked.py"
                else:
                    r.stdout = ""
                return r
            mock_run.side_effect = mock_subprocess
            
            with pytest.raises(RepoDirtyError) as exc_info:
                verify_repo_clean(temp_repo)
            
            assert "new_untracked.py" in str(exc_info.value)


class TestGitFailClosed:
    """[v0.3 Fail-Closed] Tests for git command failure handling."""
    
    def test_git_status_nonzero_returncode_raises_halt(self, temp_repo):
        """Git status with non-zero return => HALT via GitCommandError."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128
            mock_run.return_value.stderr = "fatal: not a git repository"
            mock_run.return_value.stdout = ""
            
            with pytest.raises(GitCommandError) as exc_info:
                verify_repo_clean(temp_repo)
            
            assert exc_info.value.returncode == 128
            assert "fail-closed HALT" in str(exc_info.value)
    
    def test_git_not_found_raises_halt(self, temp_repo):
        """Git executable missing => HALT via GitCommandError."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            
            with pytest.raises(GitCommandError) as exc_info:
                verify_repo_clean(temp_repo)
            
            assert "git not found" in str(exc_info.value)
    
    def test_git_rev_parse_failure_raises_halt(self, temp_repo):
        """git rev-parse HEAD failure => HALT."""
        with patch("subprocess.run") as mock_run:
            def mock_subprocess(*args, **kwargs):
                class Result:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                r = Result()
                if "rev-parse" in args[0]:
                    r.returncode = 128
                    r.stderr = "fatal: not a git repository"
                return r
            mock_run.side_effect = mock_subprocess
            
            # Mock script existence and execution
            script_dir = temp_repo / "scripts"
            script_dir.mkdir(exist_ok=True)
            (script_dir / "validate_canon_spine.py").touch()
            
            with patch("subprocess.run", side_effect=mock_subprocess) as mock_run_patch:
                with pytest.raises(GitCommandError) as exc_info:
                    mission_startup_sequence("test-run", "test", temp_repo)
            
            assert "rev-parse" in exc_info.value.command


class TestCanonSpine:
    """Tests for Canon Spine validation."""
    
    def test_verify_canon_spine_passes_on_success(self, temp_repo):
        """Should pass when scripts/validate_canon_spine.py returns 0."""
        # Ensure script path exists (even if empty) to trigger check
        script_dir = temp_repo / "scripts"
        script_dir.mkdir(exist_ok=True)
        (script_dir / "validate_canon_spine.py").touch()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "PASS"
            # verify_canon_spine doesn't raise on success
            verify_canon_spine(temp_repo)

    def test_verify_canon_spine_raises_on_failure(self, temp_repo):
        """Should raise CanonSpineError when script returns non-zero."""
        # Ensure script path exists
        script_dir = temp_repo / "scripts"
        script_dir.mkdir(exist_ok=True)
        (script_dir / "validate_canon_spine.py").touch()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = "FAIL marker missing"
            
            with pytest.raises(CanonSpineError) as exc_info:
                verify_canon_spine(temp_repo)
            
            assert "FAIL marker missing" in str(exc_info.value)

    def test_verify_canon_spine_fails_if_script_missing(self, temp_repo):
        """Should fail validation if scripts/validate_canon_spine.py is not present."""
        # temp_repo won't have the script by default
        with pytest.raises(CanonSpineError) as exc_info:
            verify_canon_spine(temp_repo)
        
        assert "Validator script missing" in str(exc_info.value)
