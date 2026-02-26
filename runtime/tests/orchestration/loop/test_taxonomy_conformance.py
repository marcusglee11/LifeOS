"""
Taxonomy conformance tests for FailureClass enum and failure_classes.yaml.

This test suite validates that:
1. Every entry in the YAML taxonomy has a corresponding enum member
2. The case normalization strategy (lowercase YAML → uppercase enum) works correctly
3. Enum-only members (without YAML counterparts) are documented

The intentional asymmetry exists because some failure classes are used only
internally by the runtime and don't require policy configuration.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.orchestration.loop.taxonomy import FailureClass


def test_yaml_entries_have_enum_members() -> None:
    """
    Verify that every entry in failure_classes.yaml has a corresponding FailureClass enum member.
    
    This test loads the YAML taxonomy, normalizes keys to uppercase, and confirms
    that each key maps to a valid enum member. This ensures the policy configuration
    is synchronized with the runtime's failure classification system.
    """
    # Resolve path relative to this test file
    yaml_path = Path(__file__).parents[4] / "config" / "policy" / "failure_classes.yaml"
    
    # Load the YAML taxonomy
    with open(yaml_path, "r") as f:
        taxonomy = yaml.safe_load(f)
    
    # Extract failure class entries from nested list under "failure_classes" key
    yaml_keys = list(taxonomy.get("failure_classes", []))
    
    # Verify each YAML key has a corresponding enum member
    for yaml_key in yaml_keys:
        # Normalize: lowercase YAML → uppercase for enum comparison
        enum_name = yaml_key.upper()
        
        # Assert the enum member exists
        assert hasattr(FailureClass, enum_name), (
            f"YAML key '{yaml_key}' (normalized to '{enum_name}') "
            f"does not have a corresponding FailureClass enum member"
        )
        
        # Verify the enum member can be accessed
        enum_member = getattr(FailureClass, enum_name)
        assert isinstance(enum_member, FailureClass), (
            f"FailureClass.{enum_name} is not a valid enum member"
        )


def test_document_enum_only_members() -> None:
    """
    Document FailureClass enum members that do not have YAML counterparts.
    
    The following enum members exist for internal runtime use and do not
    require policy configuration entries in failure_classes.yaml:
    
    1. TEST_TIMEOUT - Test execution exceeded time limit
    2. LINT_ERROR - Code failed linting checks
    3. TEST_FLAKE - Test passed on retry (flaky test detected)
    4. TYPO - Simple typographical error detected
    5. FORMATTING_ERROR - Code formatting violation
    
    These are typically handled by default policies or are transient conditions
    that don't require explicit policy configuration. This test serves as
    documentation of this intentional asymmetry.
    """
    # Verify these enum members exist
    enum_only_members = [
        "TEST_TIMEOUT",
        "LINT_ERROR",
        "TEST_FLAKE",
        "TYPO",
        "FORMATTING_ERROR",
    ]
    
    for member_name in enum_only_members:
        assert hasattr(FailureClass, member_name), (
            f"Expected enum-only member FailureClass.{member_name} not found"
        )

        # Verify it's a valid enum member
        member = getattr(FailureClass, member_name)
        assert isinstance(member, FailureClass), (
            f"FailureClass.{member_name} is not a valid enum member"
        )

    # Verify the asymmetry: none of the enum-only members appear in the YAML.
    # If one is added to failure_classes.yaml, it must be removed from enum_only_members.
    yaml_path = Path(__file__).parents[4] / "config" / "policy" / "failure_classes.yaml"
    with open(yaml_path, "r") as f:
        taxonomy = yaml.safe_load(f)
    yaml_keys_upper = {k.upper() for k in taxonomy.get("failure_classes", [])}
    for member_name in enum_only_members:
        assert member_name not in yaml_keys_upper, (
            f"FailureClass.{member_name} was added to failure_classes.yaml — "
            f"remove it from enum_only_members or update this test"
        )
