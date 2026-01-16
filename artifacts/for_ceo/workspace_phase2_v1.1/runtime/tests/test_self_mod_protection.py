"""
Tests for Self-Modification Protection.

Per Phase 2 implementation plan.
"""

import pytest
from pathlib import Path

from runtime.governance.self_mod_protection import (
    is_protected,
    check_self_modification,
    get_protected_paths,
    SelfModProtector,
    PROTECTED_PATHS,
)


class TestProtectedPaths:
    """Test protected path detection."""
    
    def test_governance_baseline_protected(self):
        """config/governance_baseline.yaml is protected."""
        assert is_protected("config/governance_baseline.yaml") is True
    
    def test_models_yaml_protected(self):
        """config/models.yaml is protected."""
        assert is_protected("config/models.yaml") is True
    
    def test_agent_roles_protected(self):
        """config/agent_roles/* are protected."""
        assert is_protected("config/agent_roles/designer.md") is True
        assert is_protected("config/agent_roles/builder.md") is True
    
    def test_gate_policy_protected(self):
        """scripts/opencode_gate_policy.py is protected."""
        assert is_protected("scripts/opencode_gate_policy.py") is True
    
    def test_self_mod_protection_protected(self):
        """runtime/governance/self_mod_protection.py is protected."""
        assert is_protected("runtime/governance/self_mod_protection.py") is True
    
    def test_architecture_docs_protected(self):
        """Architecture docs are protected."""
        assert is_protected("docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md") is True
        assert is_protected("docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.2.md") is True
    
    def test_constitutions_protected(self):
        """Agent constitutions are protected."""
        assert is_protected("GEMINI.md") is True
        assert is_protected("CLAUDE.md") is True
    
    def test_transforms_protected(self):
        """runtime/orchestration/transforms/* are protected."""
        assert is_protected("runtime/orchestration/transforms/to_build_packet.py") is True
    
    def test_regular_file_not_protected(self):
        """Regular files are not protected."""
        assert is_protected("docs/README.md") is False
        assert is_protected("runtime/agents/api.py") is False
        assert is_protected("src/main.py") is False
    
    def test_path_normalization(self):
        """Backslashes are normalized to forward slashes."""
        assert is_protected("config\\governance_baseline.yaml") is True
        assert is_protected(".\\GEMINI.md") is True


class TestCheckSelfModification:
    """Test self-modification check function."""
    
    def test_protected_path_rejected(self):
        """Protected path returns allowed=False."""
        result = check_self_modification(
            path="config/governance_baseline.yaml",
            agent_role="builder",
        )
        
        assert result.allowed is False
        assert "protected" in result.reason.lower()
    
    def test_non_protected_path_allowed(self):
        """Non-protected path returns allowed=True."""
        result = check_self_modification(
            path="docs/notes.md",
            agent_role="builder",
        )
        
        assert result.allowed is True
    
    def test_evidence_includes_matching_patterns(self):
        """Evidence includes which patterns matched."""
        result = check_self_modification(
            path="config/agent_roles/designer.md",
            agent_role="steward",
        )
        
        assert result.allowed is False
        assert "matching_patterns" in result.evidence


class TestSelfModProtector:
    """Test SelfModProtector class."""
    
    @pytest.fixture
    def protector(self, tmp_path):
        return SelfModProtector(tmp_path)
    
    def test_validate_protected_path(self, protector):
        """validate() rejects protected paths."""
        result = protector.validate(
            path="config/governance_baseline.yaml",
            agent_role="builder",
        )
        
        assert result.allowed is False
    
    def test_validate_relative_path(self, protector):
        """validate() handles relative paths."""
        result = protector.validate(
            path="GEMINI.md",
            agent_role="steward",
        )
        
        assert result.allowed is False
    
    def test_validate_absolute_path(self, protector, tmp_path):
        """validate() handles absolute paths within repo."""
        abs_path = tmp_path / "GEMINI.md"
        result = protector.validate(
            path=str(abs_path),
            agent_role="builder",
        )
        
        assert result.allowed is False
    
    def test_path_outside_repo_allowed(self, protector):
        """Paths outside repo are allowed (not our concern)."""
        result = protector.validate(
            path="/tmp/external.txt",
            agent_role="builder",
        )
        
        # Path outside repo and not matching protected patterns = allowed
        assert result.allowed is True


class TestGetProtectedPaths:
    """Test get_protected_paths() function."""
    
    def test_returns_list(self):
        """get_protected_paths() returns list."""
        paths = get_protected_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
    
    def test_includes_expected_paths(self):
        """List includes expected protected paths."""
        paths = get_protected_paths()
        assert "config/governance_baseline.yaml" in paths
        assert "GEMINI.md" in paths
