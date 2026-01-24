"""
T2: Schema Validation Tests

Tests for effective config schema validation per P0.5:
- Validating effective config passes with correct config
- Missing required key fails
- Invalid decision-in-context fails
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import yaml
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.governance.policy_loader import PolicyLoader, PolicyLoadError


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory with valid schema."""
    tmpdir = Path(tempfile.mkdtemp())
    
    # Create the real schema
    schema_path = Path("config/policy/policy_schema.json")
    if schema_path.exists():
        shutil.copy(schema_path, tmpdir / "policy_schema.json")
    else:
        # Minimal schema for testing
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["schema_version", "policy_metadata", "posture"],
            "properties": {
                "schema_version": {"type": "string", "pattern": "^1\\.2$"},
                "policy_metadata": {"type": "object"},
                "posture": {"type": "object"},
                "tool_rules": {"type": "array"},
                "loop_rules": {"type": "array"}
            }
        }
        with open(tmpdir / "policy_schema.json", 'w') as f:
            json.dump(schema, f)
    
    yield tmpdir
    shutil.rmtree(tmpdir)


def write_yaml(path: Path, data):
    """Write YAML to file."""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)


class TestSchemaValidation:
    """T2: Schema validation tests."""
    
    def test_valid_effective_config_passes(self, temp_config_dir):
        """Validating effective config passes with correct config."""
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
        
        tool_rules = [
            {"rule_id": "tool.fs.read", "decision": "ALLOW", "priority": 100,
             "path_scope": "WORKSPACE", "match": {"tool": "filesystem", "action": "read_file"}}
        ]
        write_yaml(temp_config_dir / "tool_rules.yaml", tool_rules)
        
        loop_rules = [
            {"rule_id": "loop.test", "decision": "RETRY", "priority": 100,
             "match": {"failure_class": "test_failure"}}
        ]
        write_yaml(temp_config_dir / "loop_rules.yaml", loop_rules)
        
        loader = PolicyLoader(temp_config_dir)
        effective = loader.load()
        
        assert effective["schema_version"] == "1.2"
        assert len(effective["tool_rules"]) == 1
        assert len(effective["loop_rules"]) == 1
    
    def test_missing_required_key_fails(self, temp_config_dir):
        """Missing required key (schema_version) causes failure."""
        master = {
            # Missing schema_version!
            "includes": [],
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
        
        # Should fail on schema validation
        with pytest.raises(PolicyLoadError):
            loader.load()
    
    def test_invalid_tool_decision_fails(self, temp_config_dir):
        """Invalid tool decision (RETRY in tool rule) fails."""
        master = {
            "schema_version": "1.2",
            "includes": ["tool_rules.yaml"],
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        # RETRY is invalid for tool rules!
        tool_rules = [
            {"rule_id": "tool.bad", "decision": "RETRY", "priority": 100,
             "match": {"tool": "filesystem", "action": "read_file"}}
        ]
        write_yaml(temp_config_dir / "tool_rules.yaml", tool_rules)
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="not one of"):
            loader.load()
    
    def test_invalid_loop_decision_fails(self, temp_config_dir):
        """Invalid loop decision (ALLOW in loop rule) fails."""
        master = {
            "schema_version": "1.2",
            "includes": ["loop_rules.yaml"],
            "policy_metadata": {
                "version": "1.0",
                "effective_date": "2026-01-01",
                "author": "test",
                "description": "test"
            },
            "posture": {"mode": "PRIMARY"},
        }
        write_yaml(temp_config_dir / "policy_rules.yaml", master)
        
        # ALLOW is invalid for loop rules!
        loop_rules = [
            {"rule_id": "loop.bad", "decision": "ALLOW", "priority": 100,
             "match": {"failure_class": "test_failure"}}
        ]
        write_yaml(temp_config_dir / "loop_rules.yaml", loop_rules)
        
        loader = PolicyLoader(temp_config_dir)
        
        with pytest.raises(PolicyLoadError, match="not one of"):
            loader.load()
