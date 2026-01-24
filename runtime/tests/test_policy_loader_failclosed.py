"""
Tests for PolicyLoader - workspace-root anchoring and fail-closed validation.
"""
import pytest
from pathlib import Path
from runtime.governance.policy_loader import PolicyLoader, PolicyLoadError


class TestPolicyLoaderFailClosed:
    """Test P0.3 fail-closed requirements."""
    
    def test_missing_jsonschema_authoritative_fails(self, tmp_path, monkeypatch):
        """Authoritative mode fails if jsonschema missing."""
        # Create minimal valid config
        config_dir = tmp_path / "config" / "policy"
        config_dir.mkdir(parents=True)
        
        (config_dir / "policy_rules.yaml").write_text("""
schema_version: "1.0"
includes: []
""")
        
        (config_dir / "policy_schema.json").write_text("{}")
        
        # Monkeypatch to simulate missing jsonschema
        import runtime.governance.policy_loader as loader_module
        monkeypatch.setattr(loader_module, "HAS_JSONSCHEMA", False)
        
        # Should fail in authoritative mode
        loader = PolicyLoader(config_dir=config_dir, authoritative=True)
        
        with pytest.raises(PolicyLoadError, match="jsonschema module required"):
            loader.load()
    
    def test_missing_jsonschema_non_authoritative_succeeds(self, tmp_path, monkeypatch):
        """Non-authoritative mode allows missing jsonschema."""
        # Create minimal valid config
        config_dir = tmp_path / "config" / "policy"
        config_dir.mkdir(parents=True)
        
        (config_dir / "policy_rules.yaml").write_text("""
schema_version: "1.0"
includes: []
""")
        
        # No schema file needed for non-authoritative
        
        # Monkeypatch to simulate missing jsonschema
        import runtime.governance.policy_loader as loader_module
        monkeypatch.setattr(loader_module, "HAS_JSONSCHEMA", False)
        
        # Should succeed (best-effort)
        loader = PolicyLoader(config_dir=config_dir, authoritative=False)
        config = loader.load()
        
        assert config["schema_version"] == "1.0"
    
    def test_unknown_top_level_keys_fails(self, tmp_path):
        """Unknown keys in master config are rejected."""
        config_dir = tmp_path / "config" / "policy"
        config_dir.mkdir(parents=True)
        
        (config_dir / "policy_rules.yaml").write_text("""
schema_version: "1.0"
includes: []
unknown_key: "invalid"
""")
        
        loader = PolicyLoader(config_dir=config_dir)
        
        with pytest.raises(PolicyLoadError, match="Unknown keys"):
            loader.load()
    
    def test_duplicate_includes_fails(self, tmp_path):
        """Duplicate includes are rejected."""
        config_dir = tmp_path / "config" / "policy"
        config_dir.mkdir(parents=True)
        
        (config_dir / "policy_rules.yaml").write_text("""
schema_version: "1.0"
includes:
  - tool_rules.yaml
  - tool_rules.yaml
""")
        
        # Create the include file
        (config_dir / "tool_rules.yaml").write_text("[]")
        
        loader = PolicyLoader(config_dir=config_dir)
        
        with pytest.raises(PolicyLoadError, match="Duplicate include"):
            loader.load()
    
    def test_path_traversal_in_includes_fails(self, tmp_path):
        """Path traversal in includes is rejected."""
        config_dir = tmp_path / "config" / "policy"
        config_dir.mkdir(parents=True)
        
        (config_dir / "policy_rules.yaml").write_text("""
schema_version: "1.0"
includes:
  - ../evil.yaml
""")
        
        loader = PolicyLoader(config_dir=config_dir)
        
        with pytest.raises(PolicyLoadError, match="Path traversal"):
            loader.load()
