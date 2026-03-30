"""
Test validation for Designer agent output format.

Validates that Designer outputs conform to the expected YAML schema:
- Required top-level fields
- Deliverables structure
- No markdown code fences
- Valid YAML syntax
"""

from __future__ import annotations

import sys

import yaml


def validate_designer_output(content: str) -> tuple[bool, list[str]]:
    """
    Validate Designer output against schema requirements.

    Args:
        content: Raw YAML content from Designer

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: list[str] = []

    # Check for markdown code fences
    if "```" in content:
        errors.append("Output contains markdown code fences - must be pure YAML")

    # Parse YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")
        return False, errors

    if not isinstance(data, dict):
        errors.append("Output must be a YAML dictionary")
        return False, errors

    # Check required top-level fields
    required_fields = [
        "goal",
        "design_type",
        "summary",
        "deliverables",
        "constraints",
        "verification",
        "dependencies",
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate deliverables structure
    if "deliverables" in data:
        deliverables = data["deliverables"]
        if not isinstance(deliverables, list):
            errors.append("'deliverables' must be a list")
        else:
            for idx, item in enumerate(deliverables):
                if not isinstance(item, dict):
                    errors.append(f"Deliverable {idx} must be a dictionary")
                    continue

                required_deliverable_fields = ["file", "action", "description"]
                for field in required_deliverable_fields:
                    if field not in item:
                        errors.append(f"Deliverable {idx} missing required field: {field}")

                # Validate action values
                if "action" in item and item["action"] not in ["create", "modify", "delete"]:
                    errors.append(f"Deliverable {idx} has invalid action: {item['action']}")

    # Validate design_type
    if "design_type" in data:
        valid_types = [
            "implementation_plan",
            "architecture_design",
            "api_specification",
            "data_model",
        ]
        if data["design_type"] not in valid_types:
            errors.append(
                f"Invalid design_type: {data['design_type']}. Must be one of {valid_types}"
            )

    return len(errors) == 0, errors


def run_tests() -> int:
    """
    Run validation tests on sample Designer outputs.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    print("Running Designer output validation tests...")

    # Test 1: Valid output
    valid_output = """
goal: Create a test module
design_type: implementation_plan
summary: Test implementation
deliverables:
  - file: runtime/test.py
    action: create
    description: Test file
constraints:
  - Use standard library only
verification:
  - Run pytest
dependencies:
  - sys
"""

    is_valid, errors = validate_designer_output(valid_output)
    if not is_valid:
        print("FAIL: Valid output rejected")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("PASS: Valid output accepted")

    # Test 2: Output with markdown fences (truncated — incomplete spine output)
    markdown_output = """\
```yaml
goal: test
```
"""
    is_valid, errors = validate_designer_output(markdown_output)
    if is_valid:
        print("FAIL: Markdown fences should be rejected")
        return 1
    print("PASS: Markdown fences rejected")
    return 0


class TestValidateDesignerOutput:
    """Pytest tests for Designer output validation."""

    def test_validate_designer_output_valid(self) -> None:
        """Pytest-compatible: valid designer output passes validation."""
        content = """\
goal: Test
design_type: implementation_plan
summary: Summary
deliverables:
  - file: runtime/test.py
    action: create
    description: Test file
constraints:
  - Use stdlib
verification:
  - Run pytest
dependencies:
  - sys
"""
        is_valid, errors = validate_designer_output(content)
        assert is_valid, f"Valid output rejected: {errors}"

    def test_validate_designer_output_rejects_markdown_fences(self) -> None:
        """Pytest-compatible: markdown fences in output fail validation."""
        content = "```yaml\ngoal: test\n```\n"
        is_valid, _ = validate_designer_output(content)
        assert not is_valid


if __name__ == "__main__":
    sys.exit(run_tests())
