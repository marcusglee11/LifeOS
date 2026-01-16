
import os
import shutil
import pytest
from pathlib import Path
import tempfile
from runtime.safety.path_guard import PathGuard, SafetyError

@pytest.fixture
def temp_sandbox():
    """Create a temporary directory for testing."""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    if tmp.exists():
        shutil.rmtree(tmp)

def test_path_guard_blocks_repo_root(temp_sandbox):
    """Test that repo root destruction is blocked."""
    repo_root = temp_sandbox / "repo"
    repo_root.mkdir()
    
    # Try to destroy repo root
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(repo_root, sandbox_root=temp_sandbox, repo_root=repo_root)
    
    assert "Cannot destroy repo root" in str(excinfo.value)

def test_path_guard_blocks_unmarked_directory(temp_sandbox):
    """Test that unmarked directory destruction is blocked."""
    target = temp_sandbox / "target"
    target.mkdir()
    
    # Try to verify without marker
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(target, sandbox_root=temp_sandbox)
    
    assert "Safety marker .lifeos_sandbox_marker missing" in str(excinfo.value)

def test_path_guard_allows_marked_sandbox(temp_sandbox):
    """Test that properly marked sandbox is allowed."""
    target = temp_sandbox / "valid_sandbox"
    # Create valid sandbox
    PathGuard.create_sandbox(target)
    
    # Should not raise
    PathGuard.verify_safe_for_destruction(target, sandbox_root=target)
    
    # Should work for strict descendant too
    child = target / "child"
    child.mkdir()
    PathGuard.verify_safe_for_destruction(child, sandbox_root=target)

def test_path_guard_blocks_non_descendant(temp_sandbox):
    """Test that path outside sandbox root is blocked."""
    sandbox = temp_sandbox / "sandbox"
    PathGuard.create_sandbox(sandbox)
    
    outside = temp_sandbox / "outside"
    outside.mkdir()
    (outside / ".lifeos_sandbox_marker").touch() # Even if marked!
    
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(outside, sandbox_root=sandbox)
    
    assert "not within sandbox" in str(excinfo.value)

def test_path_guard_blocks_prefix_collision(temp_sandbox):
    """P0.1: Test that prefix collisions are blocked (e.g. /tmp/foo vs /tmp/foobar)."""
    # Create /tmp/foo (sandbox)
    sandbox = temp_sandbox / "foo"
    PathGuard.create_sandbox(sandbox)
    
    # Create /tmp/foobar (target) in same parent
    target = temp_sandbox / "foobar"
    target.mkdir()
    # Mark it to ensure we fail on containment, not marker
    (target / ".lifeos_sandbox_marker").touch()
    
    # Old startswith logic would allow this since "foobar" starts with "foo"
    # New logic should block
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(target, sandbox_root=sandbox)
    
    # Message should mention containment failure
    assert "not within sandbox" in str(excinfo.value)

def test_path_guard_blocks_home_directory(monkeypatch):
    """Test that home directory destruction is blocked."""
    home = Path.home().resolve()
    
    with pytest.raises(SafetyError):
        PathGuard.verify_safe_for_destruction(home, sandbox_root=home)

def test_would_have_deleted_scenario_regression(temp_sandbox):
    """
    Regression test for the 'aggressive cleanup' scenario.
    Simulate ci_runner behavior where config_dir equals repo_root (via error).
    """
    repo_root = temp_sandbox / "repo"
    repo_root.mkdir()
    
    # Simulate config_dir resolution failing and defaulting to repo_root (hypothetically)
    bad_config_dir = repo_root
    
    # It should fail because:
    # 1. It matches repo_root (if passed)
    # 2. It misses the marker
    
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(bad_config_dir, sandbox_root=bad_config_dir, repo_root=repo_root)
    
    assert "Cannot destroy repo root" in str(excinfo.value)
    
    # Even if we don't pass repo_root (e.g. strict sandbox mode), it fails marker check
    with pytest.raises(SafetyError) as excinfo:
        PathGuard.verify_safe_for_destruction(bad_config_dir, sandbox_root=bad_config_dir)
    assert "Safety marker" in str(excinfo.value)
