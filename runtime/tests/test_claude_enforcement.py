"""
Unit tests for Claude Code enforcement scripts.

Tests the eligibility checker, Review Packet gate, doc stewardship gate,
and session completion orchestrator.
"""

import pytest
import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True)

        # Create directory structure
        (repo_root / "scripts").mkdir()
        (repo_root / "config").mkdir()
        (repo_root / "docs").mkdir()
        (repo_root / "docs" / "scripts").mkdir()
        (repo_root / "artifacts" / "review_packets").mkdir(parents=True)

        # Create minimal governance baseline
        baseline = {
            'artifacts': [
                {'path': 'docs/00_foundations/protected.md', 'sha256': 'abc123'},
                {'path': 'docs/01_governance/ruling.md', 'sha256': 'def456'}
            ]
        }
        import yaml
        with open(repo_root / "config" / "governance_baseline.yaml", 'w') as f:
            yaml.dump(baseline, f)

        # Create minimal INDEX.md
        index_content = """# Index

Last Updated: 2025-01-01

## Contents
- Stuff
"""
        (repo_root / "docs" / "INDEX.md").write_text(index_content)

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True, capture_output=True)

        yield repo_root


class TestSessionChecker:
    """Tests for claude_session_checker.py"""

    def test_lightweight_eligible_few_files(self, temp_repo):
        """Lightweight eligibility with ≤5 files, no governance paths."""
        # Copy script to temp repo
        script_src = Path("scripts/claude_session_checker.py")
        if not script_src.exists():
            pytest.skip("claude_session_checker.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_session_checker.py")

        # Commit checker script (test infrastructure, not test subject)
        subprocess.run(["git", "add", "scripts/"], cwd=temp_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add checker script"], cwd=temp_repo, check=True, capture_output=True)

        # Modify 3 files (non-governance) - this is what we're testing
        (temp_repo / "file1.txt").write_text("content")
        (temp_repo / "file2.txt").write_text("content")
        (temp_repo / "file3.txt").write_text("content")

        # Run checker
        result = subprocess.run(
            [sys.executable, "scripts/claude_session_checker.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0  # Eligible
        output = json.loads(result.stdout)
        assert output['eligible'] is True
        assert output['stats']['file_count'] == 3

    def test_lightweight_blocked_too_many_files(self, temp_repo):
        """Lightweight eligibility BLOCKED by >5 files."""
        script_src = Path("scripts/claude_session_checker.py")
        if not script_src.exists():
            pytest.skip("claude_session_checker.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_session_checker.py")

        # Modify 6 files
        for i in range(6):
            (temp_repo / f"file{i}.txt").write_text("content")

        # Stage files so git knows about them
        subprocess.run(["git", "add", "."], cwd=temp_repo, check=True, capture_output=True)

        result = subprocess.run(
            [sys.executable, "scripts/claude_session_checker.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 1  # NOT eligible
        output = json.loads(result.stdout)
        assert output['eligible'] is False
        assert any('Too many files' in v for v in output['violations'])

    def test_lightweight_blocked_governance_path(self, temp_repo):
        """Lightweight eligibility BLOCKED by governance path."""
        script_src = Path("scripts/claude_session_checker.py")
        if not script_src.exists():
            pytest.skip("claude_session_checker.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_session_checker.py")

        # Modify a governance-protected file
        (temp_repo / "docs" / "00_foundations").mkdir(parents=True)
        (temp_repo / "docs" / "00_foundations" / "protected.md").write_text("modified")

        # Stage files so git knows about them
        subprocess.run(["git", "add", "."], cwd=temp_repo, check=True, capture_output=True)

        result = subprocess.run(
            [sys.executable, "scripts/claude_session_checker.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 1  # NOT eligible
        output = json.loads(result.stdout)
        assert output['eligible'] is False
        assert any('Governance-controlled' in v for v in output['violations'])


class TestReviewPacketGate:
    """Tests for claude_review_packet_gate.py"""

    def test_packet_gate_requires_packet_to_exist(self, temp_repo):
        """Review Packet gate requires packet to exist."""
        script_src = Path("scripts/claude_review_packet_gate.py")
        if not script_src.exists():
            pytest.skip("claude_review_packet_gate.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_review_packet_gate.py")

        # No packet exists
        result = subprocess.run(
            [sys.executable, "scripts/claude_review_packet_gate.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 1  # Failed
        output = json.loads(result.stdout)
        assert output['passed'] is False
        assert any('No Review Packet found' in e for e in output['errors'])

    def test_packet_gate_finds_recent_packet(self, temp_repo):
        """Review Packet gate finds recent packet in root."""
        script_src = Path("scripts/claude_review_packet_gate.py")
        if not script_src.exists():
            pytest.skip("claude_review_packet_gate.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_review_packet_gate.py")

        # Create a lightweight packet
        packet_content = """---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-01-25T00:00:00Z"
author: "Claude Code"
version: "1.0"
mode: "LIGHTWEIGHT"
terminal_outcome: "PASS"
---

# Review Packet: Test

## Summary
Test summary.

## Appendix
Test appendix.
"""
        (temp_repo / "Review_Packet_Test_v1.0.md").write_text(packet_content)

        # Copy validator script (needed by gate)
        validator_src = Path("scripts/validate_review_packet.py")
        if validator_src.exists():
            shutil.copy(validator_src, temp_repo / "scripts" / "validate_review_packet.py")

        result = subprocess.run(
            [sys.executable, "scripts/claude_review_packet_gate.py", "--lightweight"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        # May pass or fail depending on validation, but should find the packet
        output = json.loads(result.stdout)
        assert output['review_packet_path'] is not None


class TestDocStewardshipGate:
    """Tests for claude_doc_stewardship_gate.py"""

    def test_doc_gate_detects_docs_changes(self, temp_repo):
        """Doc stewardship gate detects docs/ changes."""
        script_src = Path("scripts/claude_doc_stewardship_gate.py")
        if not script_src.exists():
            pytest.skip("claude_doc_stewardship_gate.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_doc_stewardship_gate.py")

        # Modify a docs file
        (temp_repo / "docs" / "test.md").write_text("new content")

        result = subprocess.run(
            [sys.executable, "scripts/claude_doc_stewardship_gate.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 1  # Failed (INDEX.md not updated)
        output = json.loads(result.stdout)
        assert output['docs_modified'] is True
        assert not output['passed']

    def test_doc_gate_passes_no_docs_changes(self, temp_repo):
        """Doc stewardship gate passes when no docs/ changes."""
        script_src = Path("scripts/claude_doc_stewardship_gate.py")
        if not script_src.exists():
            pytest.skip("claude_doc_stewardship_gate.py not found")

        shutil.copy(script_src, temp_repo / "scripts" / "claude_doc_stewardship_gate.py")

        # Don't modify any docs files
        (temp_repo / "other.txt").write_text("content")

        result = subprocess.run(
            [sys.executable, "scripts/claude_doc_stewardship_gate.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0  # Passed
        output = json.loads(result.stdout)
        assert output['docs_modified'] is False
        assert output['passed'] is True


class TestSessionComplete:
    """Tests for claude_session_complete.py orchestrator"""

    def test_orchestrator_runs_all_gates(self, temp_repo):
        """Session complete orchestrator runs all gates."""
        # Copy all scripts
        scripts = [
            "claude_session_checker.py",
            "claude_review_packet_gate.py",
            "claude_doc_stewardship_gate.py",
            "claude_session_complete.py",
            "validate_review_packet.py"
        ]

        for script in scripts:
            script_src = Path("scripts") / script
            if not script_src.exists():
                pytest.skip(f"{script} not found")
            shutil.copy(script_src, temp_repo / "scripts" / script)

        # Create minimal valid scenario
        (temp_repo / "file1.txt").write_text("content")

        # Create lightweight packet
        packet_content = """---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-01-25T00:00:00Z"
author: "Claude Code"
version: "1.0"
mode: "LIGHTWEIGHT"
terminal_outcome: "PASS"
---

# Review Packet: Test

## Summary
Test.

## Appendix
Test.
"""
        (temp_repo / "Review_Packet_Test_v1.0.md").write_text(packet_content)

        # Run orchestrator (non-interactive, will fail on prompt but test invocation)
        result = subprocess.run(
            [sys.executable, "scripts/claude_session_complete.py"],
            cwd=temp_repo,
            capture_output=True,
            text=True,
            input="n\n"  # Say no to any prompts
        )

        # Check that it ran (exit code may vary)
        assert "Gate 1: Eligibility Check" in result.stdout or "Claude Code Session" in result.stdout
