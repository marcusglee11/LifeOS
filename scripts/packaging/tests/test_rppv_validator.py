#!/usr/bin/env python3
"""
Tests for Return-Packet Preflight Validator (RPPV v2.6a)

Covers:
- PASS happy path
- FAIL: sentinel missing
- FAIL: patch mismatch
- BLOCK: waiver skip without valid waiver
- Idempotence: skip on digest match, rerun on change
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the validator module
from scripts.packaging.validate_return_packet_preflight import (
    EOF_SENTINEL,
    REQUIRED_FILES,
    OPTIONAL_FILES,
    NARRATIVE_PRECEDENCE,
    CheckResult,
    PreflightResult,
    compute_packet_digest,
    compute_env_digest,
    get_primary_narrative,
    check_rppv_001,
    check_rppv_004,
    check_rppv_006,
    check_rppv_009,
    check_waiver_skip,
    run_preflight,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as repo_root:
        with tempfile.TemporaryDirectory() as stage_dir:
            with tempfile.TemporaryDirectory() as packet_dir:
                yield {
                    "repo_root": Path(repo_root),
                    "stage_dir": Path(stage_dir),
                    "packet_dir": Path(packet_dir),
                }


@pytest.fixture
def valid_packet(temp_dirs):
    """Create a valid packet with all required files."""
    packet_dir = temp_dirs["packet_dir"]
    repo_root = temp_dirs["repo_root"]
    
    # Create required files
    (packet_dir / "00_manifest.json").write_text('{"version": "1.0"}')
    (packet_dir / "07_git_diff.patch").write_text("diff --git a/test.py b/test.py\n+x=1\n")
    (packet_dir / "08_evidence_manifest.sha256").write_text("")
    (packet_dir / "README.md").write_text(f"# Test\n\n{EOF_SENTINEL}\n")
    
    # Create allowlist config
    config_dir = repo_root / "config" / "packaging"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "preflight_allowlist.yaml").write_text("allowlist:\n  - test.py\n")
    
    return temp_dirs


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestGetPrimaryNarrative:
    """Tests for primary narrative file detection."""
    
    def test_returns_fix_return_first(self, temp_dirs):
        """FIX_RETURN.md has highest precedence."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "FIX_RETURN.md").write_text("fix")
        (packet_dir / "README.md").write_text("readme")
        
        assert get_primary_narrative(packet_dir) == "FIX_RETURN.md"
    
    def test_returns_readme_if_no_fix_return(self, temp_dirs):
        """README.md comes second."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "README.md").write_text("readme")
        (packet_dir / "RESULT.md").write_text("result")
        
        assert get_primary_narrative(packet_dir) == "README.md"
    
    def test_returns_result_if_no_others(self, temp_dirs):
        """RESULT.md is last resort."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "RESULT.md").write_text("result")
        
        assert get_primary_narrative(packet_dir) == "RESULT.md"
    
    def test_returns_none_if_none_exist(self, temp_dirs):
        """No narrative file returns None."""
        assert get_primary_narrative(temp_dirs["packet_dir"]) is None


class TestCheckRPPV001:
    """Tests for stage_dir outside repo_root check."""
    
    def test_pass_when_outside(self, temp_dirs):
        """PASS when stage_dir is outside repo_root."""
        result = check_rppv_001(temp_dirs["stage_dir"], temp_dirs["repo_root"])
        assert result.status == "PASS"
    
    def test_fail_when_inside(self, temp_dirs):
        """FAIL when stage_dir is inside repo_root."""
        inside_dir = temp_dirs["repo_root"] / "stage"
        inside_dir.mkdir()
        
        result = check_rppv_001(inside_dir, temp_dirs["repo_root"])
        assert result.status == "FAIL"


class TestCheckRPPV004:
    """Tests for required files check."""
    
    def test_fail_when_missing_manifest(self, temp_dirs):
        """FAIL when 00_manifest.json missing."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "07_git_diff.patch").write_text("diff")
        (packet_dir / "08_evidence_manifest.sha256").write_text("")
        (packet_dir / "README.md").write_text("readme")
        
        result = check_rppv_004(packet_dir)
        assert result.status == "FAIL"
        assert "00_manifest.json" in result.message
    
    def test_fail_when_missing_narrative(self, temp_dirs):
        """FAIL when no narrative file exists."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "00_manifest.json").write_text("{}")
        (packet_dir / "07_git_diff.patch").write_text("diff")
        (packet_dir / "08_evidence_manifest.sha256").write_text("")
        
        result = check_rppv_004(packet_dir)
        assert result.status == "FAIL"
        assert "PRIMARY_NARRATIVE" in result.message


class TestCheckRPPV006:
    """Tests for non-empty patch check."""
    
    def test_pass_with_diff_header(self, temp_dirs):
        """PASS when patch contains diff header."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "07_git_diff.patch").write_text("diff --git a/x b/y\n+line\n")
        
        result = check_rppv_006(packet_dir)
        assert result.status == "PASS"
    
    def test_fail_without_diff_header(self, temp_dirs):
        """FAIL when patch is empty or has no diff header."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "07_git_diff.patch").write_text("no diff here\n")
        
        result = check_rppv_006(packet_dir)
        assert result.status == "FAIL"


class TestCheckRPPV009:
    """Tests for EOF sentinel check."""
    
    def test_pass_with_sentinel(self, temp_dirs):
        """PASS when sentinel is present."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "README.md").write_text(f"# Title\n\n{EOF_SENTINEL}\n")
        
        result = check_rppv_009(packet_dir)
        assert result.status == "PASS"
    
    def test_fail_without_sentinel(self, temp_dirs):
        """FAIL when sentinel is missing."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "README.md").write_text("# Title\n\nNo sentinel here\n")
        
        result = check_rppv_009(packet_dir)
        assert result.status == "FAIL"
    
    def test_fail_when_no_narrative(self, temp_dirs):
        """FAIL when no narrative file exists."""
        result = check_rppv_009(temp_dirs["packet_dir"])
        assert result.status == "FAIL"


class TestWaiverBinding:
    """Tests for waiver skip validation."""
    
    def test_returns_none_when_skip_not_requested(self, temp_dirs):
        """Returns None when skip is not requested."""
        result = check_waiver_skip(
            temp_dirs["packet_dir"],
            temp_dirs["repo_root"],
            skip_requested=False
        )
        assert result is None
    
    def test_block_when_no_review_packet(self, temp_dirs):
        """BLOCK when skip requested but no review_packet.json."""
        result = check_waiver_skip(
            temp_dirs["packet_dir"],
            temp_dirs["repo_root"],
            skip_requested=True
        )
        assert result is not None
        assert result.status == "BLOCK"
        assert "review_packet.json" in result.message
    
    def test_block_when_no_run_id(self, temp_dirs):
        """BLOCK when review_packet.json missing run_id."""
        packet_dir = temp_dirs["packet_dir"]
        (packet_dir / "review_packet.json").write_text('{"other": "field"}')
        
        result = check_waiver_skip(packet_dir, temp_dirs["repo_root"], True)
        assert result.status == "BLOCK"
        assert "run_id" in result.message
    
    def test_block_when_waiver_not_approved(self, temp_dirs):
        """BLOCK when waiver decision is not APPROVE."""
        packet_dir = temp_dirs["packet_dir"]
        repo_root = temp_dirs["repo_root"]
        
        (packet_dir / "review_packet.json").write_text('{"run_id": "test123"}')
        
        waiver_dir = repo_root / "artifacts" / "loop_state"
        waiver_dir.mkdir(parents=True, exist_ok=True)
        (waiver_dir / "WAIVER_DECISION_test123.json").write_text('{"decision": "REJECT"}')
        
        result = check_waiver_skip(packet_dir, repo_root, True)
        assert result.status == "BLOCK"
        assert "REJECT" in result.message


class TestIdempotence:
    """Tests for idempotence skip behavior."""
    
    def test_skip_on_matching_digests_and_prior_pass(self, valid_packet):
        """Skip when prior PASS and digests match."""
        packet_dir = valid_packet["packet_dir"]
        repo_root = valid_packet["repo_root"]
        stage_dir = valid_packet["stage_dir"]
        
        # First run
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result1 = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result1.outcome == "PASS"
        assert result1.skipped is False
        
        # Manually write report (simulating main() behavior)
        report_path = packet_dir / "preflight_report.json"
        report_data = {
            "outcome": result1.outcome,
            "packet_digest": result1.packet_digest,
            "env_digest": result1.env_digest,
            "timestamp": result1.timestamp,
            "skipped": result1.skipped,
            "context": result1.context,
            "results": [],
            "failed_ids": result1.failed_ids,
            "skipped_ids": result1.skipped_ids,
            "blocked_ids": result1.blocked_ids
        }
        with open(report_path, "w") as f:
            json.dump(report_data, f)
        
        # Second run with same content - should skip
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result2 = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result2.outcome == "PASS"
        assert result2.skipped is True, "Should skip when digests match prior PASS"
    
    def test_rerun_when_file_changes(self, valid_packet):
        """Rerun when a validated file changes."""
        packet_dir = valid_packet["packet_dir"]
        repo_root = valid_packet["repo_root"]
        stage_dir = valid_packet["stage_dir"]
        
        # First run
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result1 = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result1.skipped is False
        
        # Modify a file
        (packet_dir / "README.md").write_text(f"# Modified\n\n{EOF_SENTINEL}\n")
        
        # Second run - should NOT skip due to digest change
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result2 = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result2.skipped is False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full preflight runs."""
    
    def test_full_pass_scenario(self, valid_packet):
        """Full PASS scenario with mocked git commands."""
        packet_dir = valid_packet["packet_dir"]
        repo_root = valid_packet["repo_root"]
        stage_dir = valid_packet["stage_dir"]
        
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result.outcome == "PASS"
        assert "RPPV-003" not in result.failed_ids
    
    def test_fail_sentinel_missing(self, valid_packet):
        """FAIL when sentinel missing from narrative."""
        packet_dir = valid_packet["packet_dir"]
        repo_root = valid_packet["repo_root"]
        stage_dir = valid_packet["stage_dir"]
        
        # Remove sentinel
        (packet_dir / "README.md").write_text("# No sentinel here\n")
        
        with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_003") as mock:
            mock.return_value = CheckResult("RPPV-003", "Coherence", "PASS", "ok")
            with patch("scripts.packaging.validate_return_packet_preflight.check_rppv_014") as mock2:
                mock2.return_value = CheckResult("RPPV-014", "Replay", "PASS", "ok")
                result = run_preflight(repo_root, packet_dir, stage_dir, None)
        
        assert result.outcome == "FAIL"
        assert "RPPV-009" in result.failed_ids
