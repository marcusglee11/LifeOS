"""
T1: Includes Resolution Tests

Tests for deterministic includes resolution per P0.4:
- Include order deterministic
- Duplicate includes fail
- Path traversal rejected
- Unknown keys rejected
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import yaml

# Import the policy loader
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.governance.policy_loader import PolicyLoader, PolicyLoadError


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir)


def write_yaml(path: Path, data):
    """Write YAML to file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)


class TestIncludesResolution:
    """T1: Includes resolution tests."""
    
    def test_include_order_deterministic(self, temp_config_dir):
        """Include order matches includes array order."""
        # Create master config with ordered includes
        master = {
            "schema_version": "1.2",
            "includes": ["tool_rules.yaml", "loop_rules.yaml"],
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        # Create tool_rules with marker
        tool_rules = [
            {"rule_id": "tool.first", "decision": "ALLOW", "priority": 100, 
             "path_scope": "WORKSPACE", "match": {"tool": "filesystem", "action": "read_file"}}
        ]
        write_yaml(temp_config_dir / "tool_rules.yaml", tool_rules)
        
        # Create loop_rules with marker
        loop_rules = [
            {"rule_id": "loop.first", "decision": "RETRY", "priority": 100, 
             "match": {"failure_class": "test_failure"}}
        ]
        write_yaml(temp_config_dir / "loop_rules.yaml", loop_rules)
        
        # Create minimal schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "schema_version": {"type": "string"},
                "policy_metadata": {"type": "object"},
                "posture": {"type": "object"},
                "tool_rules": {"type": "array"},
                "loop_rules": {"type": "array"}
            }
        }
        import json
        with open(temp_config_dir / "policy_schema.json", 'w') as f:
            json.dump(schema, f)
        
        # Load
        loader = PolicyLoader(temp_config_dir)
        effective = loader.load()
        
        # Verify order preserved
        assert len(effective["tool_rules"]) == 1
        assert effective["tool_rules"][0]["rule_id"] == "tool.first"
        assert len(effective["loop_rules"]) == 1
        assert effective["loop_rules"][0]["rule_id"] == "loop.first"
    
    def test_duplicate_include_fails(self, temp_config_dir):
        """Duplicate includes cause fail-closed error."""
        master = {
            "schema_version": "1.2",
            "includes": ["tool_rules.yaml", "tool_rules.yaml"],  # Duplicate!
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        write_yaml(temp_config_dir / "tool_rules.yaml", [])
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="Duplicate"):
            loader.load()
    
    def test_path_traversal_rejected(self, temp_config_dir):
        """Path traversal in includes is rejected."""
        master = {
            "schema_version": "1.2",
            "includes": ["../evil.yaml"],  # Path traversal!
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="traversal"):
            loader.load()
    
    def test_absolute_path_rejected(self, temp_config_dir):
        """Absolute paths in includes are rejected."""
        master = {
            "schema_version": "1.2",
            "includes": ["/etc/passwd"],  # Absolute path!
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="Absolute"):
            loader.load()
    
    def test_unknown_keys_rejected(self, temp_config_dir):
        """Unknown keys in master config are rejected."""
        master = {
            "schema_version": "1.2",
            "unknown_key": "bad",  # Unknown!
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="Unknown keys"):
            loader.load()
