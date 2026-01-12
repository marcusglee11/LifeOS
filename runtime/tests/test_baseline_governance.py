"""
Tests for Governance Baseline Checker.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §2.5
"""

import pytest
from pathlib import Path

from runtime.governance.baseline_checker import (
    GOVERNANCE_BASELINE_PATH,
    BaselineMissingError,
    BaselineMismatchError,
    verify_governance_baseline,
)


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary directory simulating a repo."""
    return tmp_path


class TestBaselineMissing:
    """Tests for baseline missing scenario per v0.3 §2.5.3."""
    
    def test_raises_when_baseline_missing(self, temp_repo):
        """Should raise BaselineMissingError when baseline file doesn't exist."""
        with pytest.raises(BaselineMissingError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        assert "Governance baseline missing" in str(exc_info.value)
        assert "CEO-authorised" in str(exc_info.value)
    
    def test_error_includes_expected_path(self, temp_repo):
        """Error should include the expected baseline path."""
        with pytest.raises(BaselineMissingError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        # The path should contain the baseline filename
        assert "governance_baseline.yaml" in exc_info.value.expected_path


class TestBaselineMismatch:
    """Tests for baseline mismatch scenario per v0.3 §2.5.3."""
    
    def test_raises_when_file_hash_mismatch(self, temp_repo):
        """Should raise BaselineMismatchError when file hash doesn't match."""
        # Create a governance surface file
        (temp_repo / "config").mkdir()
        surface_file = temp_repo / "config" / "test_surface.yaml"
        surface_file.write_text("content: original")
        
        # Create baseline with different hash
        baseline_path = temp_repo / GOVERNANCE_BASELINE_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text("""
baseline_version: "2026-01-08T12:00:00Z"
approved_by: "CEO"
hash_algorithm: "SHA-256"
path_normalization: "relpath_from_repo_root"
artifacts:
  - path: "config/test_surface.yaml"
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
""")
        
        with pytest.raises(BaselineMismatchError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        assert len(exc_info.value.mismatches) == 1
        assert exc_info.value.mismatches[0].path == "config/test_surface.yaml"
    
    def test_raises_when_file_missing(self, temp_repo):
        """Should raise mismatch error when governance surface file is missing."""
        # Create baseline referencing non-existent file
        baseline_path = temp_repo / GOVERNANCE_BASELINE_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text("""
baseline_version: "2026-01-08T12:00:00Z"
approved_by: "CEO"
hash_algorithm: "SHA-256"
path_normalization: "relpath_from_repo_root"
artifacts:
  - path: "config/missing_file.yaml"
    sha256: "abc123"
""")
        
        with pytest.raises(BaselineMismatchError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        assert exc_info.value.mismatches[0].actual_hash == "FILE_NOT_FOUND"
    
    def test_error_includes_resolution_options(self, temp_repo):
        """Error should explain CEO resolution options."""
        baseline_path = temp_repo / GOVERNANCE_BASELINE_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text("""
baseline_version: "2026-01-08T12:00:00Z"
approved_by: "CEO"
hash_algorithm: "SHA-256"
path_normalization: "relpath_from_repo_root"
artifacts:
  - path: "missing.yaml"
    sha256: "abc"
""")
        
        with pytest.raises(BaselineMismatchError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        error_msg = str(exc_info.value)
        assert "CEO action" in error_msg
        assert "Option A" in error_msg
        assert "Option B" in error_msg
    
    def test_mismatch_error_contains_full_hashes(self, temp_repo):
        """[v0.3 Audit-Grade] Error should contain full SHA256, no truncation."""
        # Create a governance surface file
        import hashlib
        (temp_repo / "config").mkdir()
        surface_file = temp_repo / "config" / "test_surface.yaml"
        surface_content = b"content: test\n"
        surface_file.write_bytes(surface_content)
        actual_hash = hashlib.sha256(surface_content).hexdigest()
        
        # Create baseline with different (but full) hash
        expected_hash = "0" * 64  # Full 64-char hash
        baseline_path = temp_repo / GOVERNANCE_BASELINE_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(f"""
baseline_version: "2026-01-08T12:00:00Z"
approved_by: "CEO"
hash_algorithm: "SHA-256"
path_normalization: "relpath_from_repo_root"
artifacts:
  - path: "config/test_surface.yaml"
    sha256: "{expected_hash}"
""")
        
        with pytest.raises(BaselineMismatchError) as exc_info:
            verify_governance_baseline(temp_repo)
        
        error_msg = str(exc_info.value)
        # Verify full 64-char hashes appear (no truncation)
        assert expected_hash in error_msg, "Expected hash should appear in full"
        assert actual_hash in error_msg, "Actual hash should appear in full"
        # Should NOT contain "..." truncation
        assert "..." not in error_msg


class TestBaselineValid:
    """Tests for successful baseline verification."""
    
    def test_passes_when_all_hashes_match(self, temp_repo):
        """Should return manifest when all governance surface hashes match."""
        import hashlib
        
        # Create governance surface file using binary mode for consistent hashes
        (temp_repo / "config").mkdir()
        surface_file = temp_repo / "config" / "test_surface.yaml"
        surface_content = b"governance: surface\n"
        surface_file.write_bytes(surface_content)
        
        # Compute correct hash
        correct_hash = hashlib.sha256(surface_content).hexdigest()
        
        # Create baseline with correct hash
        baseline_path = temp_repo / GOVERNANCE_BASELINE_PATH
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(f"""
baseline_version: "2026-01-08T12:00:00Z"
approved_by: "CEO"
council_ruling_ref: "CR-TEST-001"
hash_algorithm: "SHA-256"
path_normalization: "relpath_from_repo_root"
artifacts:
  - path: "config/test_surface.yaml"
    sha256: "{correct_hash}"
""")
        
        manifest = verify_governance_baseline(temp_repo)
        
        assert manifest.approved_by == "CEO"
        assert manifest.council_ruling_ref == "CR-TEST-001"
        assert len(manifest.artifacts) == 1
