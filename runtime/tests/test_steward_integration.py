"""
Integration tests for StewardMission using real git operations.

These tests use temporary git repositories to verify actual commit behavior,
diff size validation, and push capabilities.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

from runtime.orchestration.missions.base import MissionContext, MissionType
from runtime.orchestration.missions.steward import StewardMission


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with initial commit."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo, check=True, capture_output=True
    )

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo, check=True, capture_output=True
    )

    # Create runtime/ subdirectory (allowed code path)
    (repo / "runtime").mkdir()
    (repo / "runtime" / "__init__.py").write_text("")
    subprocess.run(["git", "add", "runtime/__init__.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add runtime dir"],
        cwd=repo, check=True, capture_output=True
    )

    return repo


@pytest.fixture
def steward_context(tmp_git_repo: Path) -> MissionContext:
    """Create MissionContext pointing at temp repo."""
    # Get current HEAD as baseline
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        capture_output=True,
        text=True,
        check=True
    )
    baseline = result.stdout.strip()

    return MissionContext(
        repo_root=tmp_git_repo,
        baseline_commit=baseline,
        run_id="test-run-123",
        operation_executor=None,
        metadata={},
    )


@pytest.fixture
def valid_review_packet() -> Dict[str, Any]:
    """Create a valid review packet for testing."""
    return {
        "mission_name": "test_mission",
        "summary": "Test changes",
        "payload": {
            "artifacts_produced": []
        }
    }


@pytest.fixture
def approved_decision() -> Dict[str, Any]:
    """Create an approved decision for testing."""
    return {
        "verdict": "approved",
        "rationale": "Looks good"
    }


def test_real_commit_code_changes(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward creates real git commit for code changes."""
    # Create a new file in runtime/
    test_file = steward_context.repo_root / "runtime" / "test_file.py"
    test_file.write_text("# Test file\nprint('hello')\n")

    # Update packet with artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["runtime/test_file.py"]

    # Get pre-commit hash
    pre_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    pre_hash = pre_result.stdout.strip()

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify success
    assert result.success is True
    assert "commit_hash" in result.outputs
    commit_hash = result.outputs["commit_hash"]

    # Verify commit exists in git log
    log_result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    assert commit_hash[:7] in log_result.stdout

    # Verify HEAD advanced
    post_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    post_hash = post_result.stdout.strip()
    assert post_hash != pre_hash
    assert post_hash == commit_hash


def test_diff_size_validation_blocks_oversized(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward rejects changes exceeding max_lines budget."""
    # Create a file with >300 lines of changes
    test_file = steward_context.repo_root / "runtime" / "large_file.py"
    large_content = "\n".join([f"# Line {i}" for i in range(400)])
    test_file.write_text(large_content)

    # Update packet with artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["runtime/large_file.py"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify failure
    assert result.success is False
    assert "Diff size exceeds budget" in result.error
    assert "diff_size" in result.evidence
    assert result.evidence["diff_size"]["total_delta"] > 300


def test_diff_size_validation_allows_within_budget(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward allows changes within max_lines budget."""
    # Create a small file (<300 lines)
    test_file = steward_context.repo_root / "runtime" / "small_file.py"
    small_content = "\n".join([f"# Line {i}" for i in range(50)])
    test_file.write_text(small_content)

    # Update packet with artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["runtime/small_file.py"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify success
    assert result.success is True
    assert "commit_hash" in result.outputs
    assert "diff_size" in result.evidence
    assert result.evidence["diff_size"]["total_delta"] <= 300


def test_protected_path_blocked(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward blocks changes to protected paths."""
    # Create protected path directory structure
    protected_dir = steward_context.repo_root / "docs" / "00_foundations"
    protected_dir.mkdir(parents=True)

    # Create a file in protected path
    protected_file = protected_dir / "test_doc.md"
    protected_file.write_text("# Protected doc\n")

    # Update packet with protected artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["docs/00_foundations/test_doc.md"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify failure
    assert result.success is False
    assert "BLOCKED: Protected root paths" in result.error
    assert "docs/00_foundations/test_doc.md" in result.error


def test_disallowed_path_blocked(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward blocks changes to disallowed paths."""
    # Create a file outside allowed scope
    disallowed_file = steward_context.repo_root / "random_file.txt"
    disallowed_file.write_text("Random content\n")

    # Update packet with disallowed artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["random_file.txt"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify failure
    assert result.success is False
    assert "BLOCKED: Disallowed paths" in result.error
    assert "random_file.txt" in result.error


def test_clean_repo_after_commit(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify repo is clean after successful commit."""
    # Create a new file in runtime/
    test_file = steward_context.repo_root / "runtime" / "clean_test.py"
    test_file.write_text("# Clean test\n")

    # Update packet with artifact
    valid_review_packet["payload"]["artifacts_produced"] = ["runtime/clean_test.py"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify success
    assert result.success is True

    # Verify repo is clean
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    assert status_result.stdout.strip() == ""


def test_push_to_remote(
    tmp_path: Path,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify git push works when push flag is set."""
    # Create bare repo as remote
    bare_repo = tmp_path / "bare_repo"
    bare_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=bare_repo, check=True, capture_output=True)

    # Create working repo
    work_repo = tmp_path / "work_repo"
    work_repo.mkdir()
    subprocess.run(["git", "init"], cwd=work_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=work_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=work_repo, check=True, capture_output=True
    )

    # Create initial commit and add remote
    (work_repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=work_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=work_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare_repo)],
        cwd=work_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "master"],
        cwd=work_repo, check=True, capture_output=True
    )

    # Create runtime/ directory
    (work_repo / "runtime").mkdir()
    (work_repo / "runtime" / "__init__.py").write_text("")
    subprocess.run(["git", "add", "runtime/__init__.py"], cwd=work_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add runtime"],
        cwd=work_repo, check=True, capture_output=True
    )
    subprocess.run(["git", "push"], cwd=work_repo, check=True, capture_output=True)

    # Get baseline commit
    baseline_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=work_repo,
        capture_output=True,
        text=True,
        check=True
    )
    baseline = baseline_result.stdout.strip()

    # Create context with push enabled
    context = MissionContext(
        repo_root=work_repo,
        baseline_commit=baseline,
        run_id="test-run-123",
        operation_executor=None,
        metadata={"push": True},  # Enable push
    )

    # Create new file
    test_file = work_repo / "runtime" / "push_test.py"
    test_file.write_text("# Push test\n")

    # Update packet
    valid_review_packet["payload"]["artifacts_produced"] = ["runtime/push_test.py"]

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(context, inputs)

    # Verify success
    assert result.success is True

    # Verify push happened by checking remote
    remote_log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=bare_repo,
        capture_output=True,
        text=True,
        check=True
    )
    assert "test_mission" in remote_log.stdout


def test_empty_artifacts_no_commit(
    steward_context: MissionContext,
    valid_review_packet: Dict[str, Any],
    approved_decision: Dict[str, Any]
):
    """Verify steward returns success with no commit for empty artifact list."""
    # Empty artifact list
    valid_review_packet["payload"]["artifacts_produced"] = []

    # Get pre-commit hash
    pre_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    pre_hash = pre_result.stdout.strip()

    # Run steward mission
    mission = StewardMission()
    inputs = {
        "review_packet": valid_review_packet,
        "approval": approved_decision,
    }
    result = mission.run(steward_context, inputs)

    # Verify success with no commit
    assert result.success is True
    assert result.outputs["commit_hash"] is None
    assert "No artifacts to commit" in result.outputs["commit_message"]

    # Verify HEAD did not advance
    post_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=steward_context.repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    post_hash = post_result.stdout.strip()
    assert post_hash == pre_hash
