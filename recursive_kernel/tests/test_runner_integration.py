# -*- coding: utf-8 -*-
"""
Tests for recursive_kernel/runner.py (Autonomous Mode)
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from recursive_kernel.runner import AutonomousRunner


def write_backlog(path: Path, content: str) -> None:
    """Write content to path with explicit UTF-8 encoding."""
    path.write_bytes(content.encode('utf-8'))


class TestAutonomousRunnerDryRun:
    """Tests for dry-run mode (zero side effects)."""
    
    def test_dry_run_no_dispatch(self, tmp_path: Path):
        """Dry-run does not dispatch mission."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=True)
        runner.backlog_path = backlog
        
        with patch.object(runner, '_dispatch_mission') as mock_dispatch:
            exit_code = runner.run()
        
        # Should not call dispatch in dry-run
        mock_dispatch.assert_not_called()
        assert exit_code == 0
    
    def test_dry_run_no_backlog_mutation(self, tmp_path: Path):
        """Dry-run does not modify backlog file."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        original_content = """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
"""
        write_backlog(backlog, original_content)
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=True)
        runner.backlog_path = backlog
        
        exit_code = runner.run()
        
        # Backlog should be unchanged
        assert backlog.read_text(encoding='utf-8') == original_content
        assert exit_code == 0
    
    def test_dry_run_no_artifact_creation(self, tmp_path: Path):
        """Dry-run does not create artifacts."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        artifacts_dir = tmp_path / "artifacts" / "packets"
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=True)
        runner.backlog_path = backlog
        runner.artifacts_dir = artifacts_dir
        
        exit_code = runner.run()
        
        # No artifacts should be created
        if artifacts_dir.exists():
            assert len(list(artifacts_dir.glob("*.json"))) == 0
        assert exit_code == 0


class TestAutonomousRunnerSelection:
    """Tests for item selection logic."""
    
    def test_selects_p0_over_p1(self, tmp_path: Path):
        """Selection prefers P0 items."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P1 (High)

- [ ] **P1 Task** -- DoD: Done -- Owner: dev

### P0 (Critical)

- [ ] **P0 Task** -- DoD: Done -- Owner: dev
""")
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=True)
        runner.backlog_path = backlog
        
        # Capture stdout to verify selection
        import io
        import sys
        captured = io.StringIO()
        sys.stdout = captured
        try:
            runner.run()
        finally:
            sys.stdout = sys.__stdout__
        
        output = captured.getvalue()
        assert "P0 Task" in output
        assert "Priority: P0" in output
    
    def test_returns_zero_when_no_eligible(self, tmp_path: Path):
        """Exits cleanly when no P0/P1 items exist."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P2 (Normal)

- [ ] **P2 Task** -- DoD: Done -- Owner: dev
""")
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=True)
        runner.backlog_path = backlog
        
        exit_code = runner.run()
        
        assert exit_code == 0


class TestAutonomousRunnerOutcomes:
    """Tests for outcome handling."""
    
    def test_escalation_emits_artifact(self, tmp_path: Path):
        """Escalation result emits artifact and halts."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        artifacts_dir = tmp_path / "artifacts" / "packets"
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=False)
        runner.backlog_path = backlog
        runner.artifacts_dir = artifacts_dir
        
        # Mock dispatch to return escalation
        with patch.object(runner, '_dispatch_mission') as mock_dispatch, \
             patch.object(runner, '_is_git_dirty', return_value=False):
            mock_dispatch.return_value = {
                "success": False,
                "escalation_reason": "Test escalation"
            }
            
            exit_code = runner.run()
        
        # Should create escalation artifact
        escalation_files = list(artifacts_dir.glob("ESCALATION_*.json"))
        assert len(escalation_files) == 1
        assert exit_code == 2  # Escalation exit code
    
    def test_waiver_emits_artifact(self, tmp_path: Path):
        """Waiver result emits artifact and halts."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        artifacts_dir = tmp_path / "artifacts" / "packets"
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=False)
        runner.backlog_path = backlog
        runner.artifacts_dir = artifacts_dir
        
        # Mock dispatch to return waiver
        with patch.object(runner, '_dispatch_mission') as mock_dispatch, \
             patch.object(runner, '_is_git_dirty', return_value=False):
            mock_dispatch.return_value = {
                "success": False,
                "error": "WAIVER_REQUESTED for dangerous operation"
            }
            
            exit_code = runner.run()
        
        # Should create waiver artifact
        waiver_files = list(artifacts_dir.glob("WAIVER_REQUEST_*.json"))
        assert len(waiver_files) == 1
        assert exit_code == 3  # Waiver exit code
    
    def test_success_marks_item_done(self, tmp_path: Path):
        """Success result marks item done in backlog."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=False)
        runner.backlog_path = backlog
        
        # Mock dispatch to return success
        with patch.object(runner, '_dispatch_mission') as mock_dispatch, \
             patch.object(runner, '_is_git_dirty', return_value=False):
            mock_dispatch.return_value = {
                "success": True,
                "outputs": {"commit_hash": "abc123"}
            }
            
            exit_code = runner.run()
        
        # Backlog should be updated
        content = backlog.read_text(encoding='utf-8')
        assert "[x] **Test Task**" in content
        assert exit_code == 0


class TestAutonomousRunnerFailClosed:
    """Tests for fail-closed behavior."""
    
    def test_blocks_on_malformed_backlog(self, tmp_path: Path):
        """Blocks when P0/P1 item is missing required fields."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Missing Owner Task** -- DoD: Something
""")
        
        artifacts_dir = tmp_path / "artifacts" / "packets"
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=False)
        runner.backlog_path = backlog
        runner.artifacts_dir = artifacts_dir
        
        exit_code = runner.run()
        
        # Should block and emit artifact
        blocked_files = list(artifacts_dir.glob("BLOCKED_*.json"))
        assert len(blocked_files) == 1
        assert exit_code == 1
    
    def test_blocks_on_git_dirty(self, tmp_path: Path):
        """Blocks when repository is dirty (non-dry-run)."""
        backlog = tmp_path / "docs" / "11_admin" / "BACKLOG.md"
        backlog.parent.mkdir(parents=True, exist_ok=True)
        write_backlog(backlog, """### P0 (Critical)

- [ ] **Test Task** -- DoD: Done -- Owner: dev
""")
        
        artifacts_dir = tmp_path / "artifacts" / "packets"
        
        runner = AutonomousRunner(repo_root=tmp_path, dry_run=False)
        runner.backlog_path = backlog
        runner.artifacts_dir = artifacts_dir
        
        # Mock git dirty check
        with patch.object(runner, '_is_git_dirty', return_value=True):
            exit_code = runner.run()
        
        # Should block
        blocked_files = list(artifacts_dir.glob("BLOCKED_*.json"))
        assert len(blocked_files) == 1
        
        # Verify reason in artifact
        content = json.loads(blocked_files[0].read_text())
        assert "uncommitted changes" in content["reason"]
        assert exit_code == 1
