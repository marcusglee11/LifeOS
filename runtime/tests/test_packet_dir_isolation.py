"""
Regression tests for packet directory isolation (Gate 2 / Article XIX enforcement).

Tests that validate_return_packet_preflight.py correctly enforces:
- ALLOW: packet_dir outside repo
- ALLOW: packet_dir inside repo AND gitignored
- FAIL: packet_dir inside repo but NOT gitignored (no writes allowed)
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def repo_root():
    """Get repository root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True
    )
    return Path(result.stdout.strip())


@pytest.fixture
def safe_packet_dir(repo_root):
    """Get a safe (gitignored) packet directory for testing."""
    # Use artifacts/for_ceo which should be gitignored
    safe_dir = repo_root / "artifacts" / "for_ceo"
    safe_dir.mkdir(parents=True, exist_ok=True)

    # Verify it's actually gitignored
    probe = safe_dir / ".lifeos_ignore_probe"
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--stdin"],
        cwd=repo_root,
        input=str(probe) + "\n",
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        pytest.skip(f"artifacts/for_ceo is not gitignored (rc={result.returncode})")

    return safe_dir


def test_packet_dir_unsafe_repo_root_fails(repo_root):
    """
    UNSAFE case: packet_dir = repo root (not gitignored)

    Expected: script exits non-zero, NO report files created in repo root
    """
    # Use repo root as packet_dir (definitely not gitignored)
    packet_dir = repo_root

    # Create minimal args (we expect early failure before stage_dir is used)
    cmd = [
        sys.executable,
        "-m",
        "scripts.packaging.validate_return_packet_preflight",
        "--repo-root",
        str(repo_root),
        "--packet-dir",
        str(packet_dir),
        "--stage-dir",
        "/tmp/stage_test",  # Won't be checked due to early failure
    ]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should FAIL
    assert result.returncode != 0, "Script should fail for unsafe packet_dir"
    assert "isolation violation" in result.stderr.lower() or "not gitignored" in result.stderr.lower(), \
        f"Should report isolation violation. stderr: {result.stderr}"

    # Verify NO report files created in repo root
    report_json = repo_root / "preflight_report.json"
    report_md = repo_root / "preflight_report.md"

    assert not report_json.exists(), f"Report JSON should not exist at {report_json}"
    assert not report_md.exists(), f"Report MD should not exist at {report_md}"


def test_packet_dir_safe_ignored_succeeds(repo_root, safe_packet_dir, tmp_path):
    """
    SAFE case: packet_dir is gitignored inside repo

    Expected: script succeeds (or fails for other reasons, but NOT isolation),
              report files created in packet_dir
    """
    # Create a test packet in the safe directory
    packet_test_dir = safe_packet_dir / "test_packet"
    packet_test_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal required files for the packet
    manifest = packet_test_dir / "00_manifest.json"
    manifest.write_text('{"version": "1.0", "test": true}')

    patch = packet_test_dir / "07_git_diff.patch"
    patch.write_text("# Empty patch for test\n")

    evidence = packet_test_dir / "08_evidence_manifest.sha256"
    evidence.write_text("# Empty manifest for test\n")

    narrative = packet_test_dir / "README.md"
    narrative.write_text("Test narrative\n\n__EOF_SENTINEL__\n")

    # Use a temp stage_dir outside repo
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    cmd = [
        sys.executable,
        "-m",
        "scripts.packaging.validate_return_packet_preflight",
        "--repo-root",
        str(repo_root),
        "--packet-dir",
        str(packet_test_dir),
        "--stage-dir",
        str(stage_dir),
    ]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should NOT fail due to isolation (may fail for other validation reasons)
    if result.returncode != 0:
        # If it failed, ensure it's NOT an isolation violation
        assert "isolation violation" not in result.stderr.lower(), \
            f"Should not fail on isolation for gitignored dir. stderr: {result.stderr}"
        # For this test, we accept validation failures (we're testing isolation, not full validation)

    # Check that report was written to packet_dir (regardless of pass/fail outcome)
    report_json = packet_test_dir / "preflight_report.json"
    assert report_json.exists(), \
        f"Report JSON should be written to packet_dir. stderr: {result.stderr}"


def test_packet_dir_outside_repo_succeeds(repo_root, tmp_path):
    """
    SAFE case: packet_dir outside repo

    Expected: script succeeds (isolation-wise), report written to packet_dir
    """
    # Create packet_dir outside repo
    packet_dir = tmp_path / "external_packet"
    packet_dir.mkdir()

    # Create minimal required files
    manifest = packet_dir / "00_manifest.json"
    manifest.write_text('{"version": "1.0", "test": true}')

    patch = packet_dir / "07_git_diff.patch"
    patch.write_text("# Empty patch for test\n")

    evidence = packet_dir / "08_evidence_manifest.sha256"
    evidence.write_text("# Empty manifest for test\n")

    narrative = packet_dir / "README.md"
    narrative.write_text("Test narrative\n\n__EOF_SENTINEL__\n")

    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    cmd = [
        sys.executable,
        "-m",
        "scripts.packaging.validate_return_packet_preflight",
        "--repo-root",
        str(repo_root),
        "--packet-dir",
        str(packet_dir),
        "--stage-dir",
        str(stage_dir),
    ]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should NOT fail due to isolation
    if result.returncode != 0:
        assert "isolation violation" not in result.stderr.lower(), \
            f"Should not fail on isolation for outside-repo dir. stderr: {result.stderr}"

    # Report should exist in packet_dir
    report_json = packet_dir / "preflight_report.json"
    assert report_json.exists(), \
        f"Report JSON should be written to packet_dir. stderr: {result.stderr}"


def test_cleanliness_gate_check():
    """Test that cleanliness_gate.py check command works."""
    result = subprocess.run(
        [sys.executable, "scripts/cleanliness_gate.py", "check"],
        capture_output=True,
        text=True
    )

    # Should exit cleanly (0 if clean, non-zero if dirty)
    # We don't assert on exit code since repo might be dirty during testing
    # Just verify the script runs without error
    assert "Repository is clean" in result.stdout or "Repository is dirty" in result.stderr, \
        f"Cleanliness gate should report status. stdout: {result.stdout}, stderr: {result.stderr}"
