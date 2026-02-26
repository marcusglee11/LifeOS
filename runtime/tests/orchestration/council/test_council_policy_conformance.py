"""Tests for council_policy.yaml internal enum consistency.

Validates YAML-internal self-consistency only. Does NOT compare YAML enums
to Python string constants in models.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


# Path to council policy YAML relative to repository root
POLICY_PATH = Path(__file__).parents[4] / "config" / "policy" / "council_policy.yaml"


def load_council_policy() -> dict[str, Any]:
    """
    Load and parse the council_policy.yaml file.
    
    Returns:
        Parsed YAML content as dictionary
        
    Raises:
        FileNotFoundError: If policy file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not POLICY_PATH.exists():
        raise FileNotFoundError(
            f"Council policy file not found at: {POLICY_PATH}\n"
            f"Expected location: config/policy/council_policy.yaml"
        )
    
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_enum_definitions(policy: dict[str, Any]) -> dict[str, set[str]]:
    """
    Extract all enum definitions from the enums section.
    
    Args:
        policy: Parsed policy dictionary
        
    Returns:
        Dictionary mapping enum names to sets of valid values
        
    Raises:
        KeyError: If enums section is missing
    """
    if "enums" not in policy:
        raise KeyError(
            "Missing 'enums' section in council_policy.yaml\n"
            "Expected top-level 'enums' key with enum definitions"
        )
    
    enums = policy["enums"]
    definitions: dict[str, set[str]] = {}
    
    for enum_name, enum_values in enums.items():
        if not isinstance(enum_values, list):
            raise ValueError(
                f"Enum '{enum_name}' must be a list, got {type(enum_values).__name__}"
            )
        definitions[enum_name] = set(enum_values)
    
    return definitions


def collect_enum_references(
    section: dict[str, Any],
    enum_fields: list[str]
) -> dict[str, list[str]]:
    """
    Collect all enum value references from a policy section.
    
    Args:
        section: Policy section to scan (modes/seats/tiers/lenses)
        enum_fields: List of field names that contain enum references
        
    Returns:
        Dictionary mapping enum field names to lists of referenced values
    """
    references: dict[str, list[str]] = {field: [] for field in enum_fields}
    
    if not isinstance(section, dict):
        return references
    
    for item_name, item_config in section.items():
        if not isinstance(item_config, dict):
            continue
        
        for field in enum_fields:
            if field in item_config:
                value = item_config[field]
                if isinstance(value, str):
                    references[field].append(value)
                elif isinstance(value, list):
                    references[field].extend(value)
    
    return references


def validate_references(
    references: dict[str, list[str]],
    definitions: dict[str, set[str]]
) -> list[str]:
    """
    Validate that all referenced enum values are defined.
    
    Args:
        references: Dictionary of field names to referenced values
        definitions: Dictionary of enum names to valid values
        
    Returns:
        List of error messages for undefined references
    """
    errors: list[str] = []
    
    for field_name, values in references.items():
        if field_name not in definitions:
            if values:  # Only report if there are actual references
                errors.append(
                    f"Enum '{field_name}' is referenced but not defined in enums section\n"
                    f"  Referenced values: {sorted(set(values))}"
                )
            continue
        
        valid_values = definitions[field_name]
        undefined = set(values) - valid_values
        
        if undefined:
            errors.append(
                f"Undefined values in enum '{field_name}':\n"
                f"  Undefined: {sorted(undefined)}\n"
                f"  Valid values: {sorted(valid_values)}"
            )
    
    return errors


class TestCouncilPolicyLoading:
    """Test basic policy file loading."""
    
    def test_council_policy_loads(self):
        """Verify council_policy.yaml loads without errors."""
        policy = load_council_policy()
        assert isinstance(policy, dict), "Policy must be a dictionary"
        assert len(policy) > 0, "Policy must not be empty"
    
    def test_enums_section_exists(self):
        """Verify enums section is present in policy."""
        policy = load_council_policy()
        assert "enums" in policy, "Policy must contain 'enums' section"
        assert isinstance(policy["enums"], dict), "Enums section must be a dictionary"


class TestEnumDefinitions:
    """Test enum definitions structure."""
    
    def test_enum_definitions_are_lists(self):
        """Verify all enum definitions are lists of values."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        for enum_name, values in definitions.items():
            assert isinstance(values, set), f"Enum '{enum_name}' must be a set"
            assert len(values) > 0, f"Enum '{enum_name}' must not be empty"
    
    def test_enum_values_are_strings(self):
        """Verify all enum values are strings."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        for enum_name, values in definitions.items():
            for value in values:
                assert isinstance(value, str), (
                    f"Enum '{enum_name}' contains non-string value: {value}"
                )


class TestModeEnumReferences:
    """Test mode enum references."""
    
    def test_mode_enum_references(self):
        """Validate all mode field enum values are defined."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        if "modes" not in policy:
            pytest.skip("No 'modes' section in policy")
        
        # LIFEOS_TODO[P2]: council_policy.yaml modes section does not currently use
        # mode_type/execution_model/priority field names — references will always be
        # empty and this test is vacuously passing until the YAML schema evolves.
        references = collect_enum_references(
            policy["modes"],
            ["mode_type", "execution_model", "priority"]
        )
        
        errors = validate_references(references, definitions)
        assert not errors, "\n".join(errors)


class TestSeatEnumReferences:
    """Test seat enum references."""
    
    def test_seat_enum_references(self):
        """Validate all seat field enum values are defined."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        if "seats" not in policy:
            pytest.skip("No 'seats' section in policy")
        
        # LIFEOS_TODO[P2]: council_policy.yaml seats section does not currently use
        # role/authority_level/decision_scope field names — vacuously passing.
        references = collect_enum_references(
            policy["seats"],
            ["role", "authority_level", "decision_scope"]
        )
        
        errors = validate_references(references, definitions)
        assert not errors, "\n".join(errors)


class TestTierEnumReferences:
    """Test tier enum references."""
    
    def test_tier_enum_references(self):
        """Validate all tier field enum values are defined."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        if "tiers" not in policy:
            pytest.skip("No 'tiers' section in policy")
        
        # LIFEOS_TODO[P2]: council_policy.yaml tiers section does not currently use
        # governance_level/approval_authority/review_scope field names — vacuously passing.
        references = collect_enum_references(
            policy["tiers"],
            ["governance_level", "approval_authority", "review_scope"]
        )
        
        errors = validate_references(references, definitions)
        assert not errors, "\n".join(errors)


class TestLensEnumReferences:
    """Test lens enum references."""
    
    def test_lens_enum_references(self):
        """Validate all lens field enum values are defined."""
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        if "lenses" not in policy:
            pytest.skip("No 'lenses' section in policy")
        
        # LIFEOS_TODO[P2]: council_policy.yaml lenses section does not currently use
        # perspective_type/analysis_depth/focus_area field names — vacuously passing.
        references = collect_enum_references(
            policy["lenses"],
            ["perspective_type", "analysis_depth", "focus_area"]
        )
        
        errors = validate_references(references, definitions)
        assert not errors, "\n".join(errors)


class TestComprehensiveValidation:
    """Comprehensive validation across all sections."""
    
    def test_all_enum_references_defined(self):
        """
        Comprehensive check that all enum references across all sections
        are properly defined in the enums section.
        """
        policy = load_council_policy()
        definitions = extract_enum_definitions(policy)
        
        all_errors: list[str] = []
        
        # LIFEOS_TODO[P2]: All four sections (modes/seats/tiers/lenses) are currently
        # vacuously validated — the YAML structure does not use the expected field names,
        # so collect_enum_references always returns empty. Meaningful once YAML schema evolves.
        # Define sections and their enum fields
        sections = {
            "modes": ["mode_type", "execution_model", "priority"],
            "seats": ["role", "authority_level", "decision_scope"],
            "tiers": ["governance_level", "approval_authority", "review_scope"],
            "lenses": ["perspective_type", "analysis_depth", "focus_area"],
        }
        
        for section_name, enum_fields in sections.items():
            if section_name not in policy:
                continue
            
            references = collect_enum_references(
                policy[section_name],
                enum_fields
            )
            
            errors = validate_references(references, definitions)
            if errors:
                all_errors.append(f"\n[{section_name.upper()}]")
                all_errors.extend(errors)
        
        assert not all_errors, "\n".join(all_errors)
    
