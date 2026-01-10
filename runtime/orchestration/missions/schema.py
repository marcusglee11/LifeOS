"""
Phase 3 Mission Types - Schema Validation

Provides mission definition schema validation using jsonschema.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from jsonschema import Draft7Validator


# Schema location
SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "config" / "schemas"
MISSION_SCHEMA_FILE = "mission.yaml"


class MissionSchemaError(Exception):
    """
    Raised when mission definition fails schema validation.
    
    Provides deterministic error messages sorted by path.
    """
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def load_mission_schema() -> Dict[str, Any]:
    """
    Load the mission YAML schema.
    
    Returns:
        The schema as a dict.
        
    Raises:
        MissionSchemaError: If schema file not found or invalid.
    """
    schema_path = SCHEMA_ROOT / MISSION_SCHEMA_FILE
    if not schema_path.exists():
        raise MissionSchemaError([f"Mission schema not found: {schema_path}"])
    
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise MissionSchemaError([f"Failed to parse mission schema: {e}"])


def validate_mission_definition(definition: Dict[str, Any]) -> None:
    """
    Validate a mission definition against the schema.
    
    Fail-closed: Raises MissionSchemaError if validation fails.
    Error messages are deterministic (sorted by path).
    
    Args:
        definition: The mission definition dict to validate.
        
    Raises:
        MissionSchemaError: If validation fails, with sorted error messages.
    """
    schema = load_mission_schema()
    validator = Draft7Validator(schema)
    
    # Collect all errors
    errors_raw = list(validator.iter_errors(definition))
    
    if not errors_raw:
        return  # Valid
    
    # Sort errors by path for deterministic output
    errors_raw.sort(key=lambda e: (list(e.path), e.message))
    
    # Format error messages
    messages = []
    for e in errors_raw:
        path_str = "/".join(str(p) for p in e.path) if e.path else "<root>"
        messages.append(f"{path_str}: {e.message}")
    
    raise MissionSchemaError(messages)


def validate_mission_type(mission_type: str) -> None:
    """
    Validate that a mission type string is valid.
    
    Fail-closed: Raises MissionSchemaError if type is unknown.
    
    Args:
        mission_type: The mission type string to validate.
        
    Raises:
        MissionSchemaError: If type is not in allowed enum.
    """
    # Load schema to get allowed types
    schema = load_mission_schema()
    
    # Extract allowed types from schema
    type_schema = schema.get("properties", {}).get("type", {})
    allowed_types = type_schema.get("enum", [])
    
    if mission_type not in allowed_types:
        raise MissionSchemaError([
            f"type: '{mission_type}' is not one of {sorted(allowed_types)}"
        ])
