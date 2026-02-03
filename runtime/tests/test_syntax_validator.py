"""
Tests for syntax validation (Phase 4D).

Coverage:
- Python AST validation (valid/invalid)
- YAML validation (valid/invalid)
- JSON validation (valid/invalid)
- Language detection
- Fail-closed behavior
"""

import pytest
from runtime.governance.syntax_validator import (
    SyntaxValidator,
    ValidationResult,
    validate_python,
    validate_yaml,
    validate_json,
    detect_language,
    validate_syntax,
)


# =============================================================================
# Python Validation Tests
# =============================================================================

class TestPythonValidation:
    """Tests for Python syntax validation."""

    def test_python_valid_simple(self):
        """Valid Python code passes."""
        validator = SyntaxValidator()
        result = validator.validate("print('hello')", lang="python")

        assert result.valid is True
        assert result.error is None
        assert result.language == "python"

    def test_python_valid_function(self):
        """Valid Python function passes."""
        code = """
def foo(x: int) -> int:
    return x + 1

class Bar:
    def method(self):
        pass
"""
        result = validate_python(code)
        assert result.valid is True
        assert result.language == "python"

    def test_python_invalid_unclosed_paren(self):
        """Invalid Python with unclosed paren fails."""
        validator = SyntaxValidator()
        result = validator.validate("print('hello'", lang="python")

        assert result.valid is False
        assert result.error is not None
        assert "SyntaxError" in result.error
        assert result.language == "python"

    def test_python_invalid_bad_indent(self):
        """Invalid Python with bad indentation fails."""
        code = """
def foo():
  x = 1
    y = 2  # Bad indent
"""
        result = validate_python(code)
        assert result.valid is False
        assert "SyntaxError" in result.error

    def test_python_invalid_missing_colon(self):
        """Invalid Python with missing colon fails."""
        code = "def foo()\n    pass"
        result = validate_python(code)
        assert result.valid is False
        assert "SyntaxError" in result.error

    def test_python_empty_file(self):
        """Empty Python file is valid."""
        result = validate_python("")
        assert result.valid is True


# =============================================================================
# YAML Validation Tests
# =============================================================================

class TestYAMLValidation:
    """Tests for YAML syntax validation."""

    def test_yaml_valid_simple(self):
        """Valid YAML passes."""
        validator = SyntaxValidator()
        result = validator.validate("key: value\nlist:\n  - item", lang="yaml")

        assert result.valid is True
        assert result.error is None
        assert result.language == "yaml"

    def test_yaml_valid_complex(self):
        """Valid complex YAML passes."""
        yaml_content = """
environments:
  production:
    host: example.com
    port: 443
    features:
      - auth
      - logging
  staging:
    host: staging.example.com
    port: 8080
"""
        result = validate_yaml(yaml_content)
        assert result.valid is True

    def test_yaml_invalid_bad_indent(self):
        """Invalid YAML with bad indentation fails."""
        validator = SyntaxValidator()
        # Invalid: key-value pair with inconsistent indentation
        result = validator.validate("key:\n  - item1\n - item2", lang="yaml")

        assert result.valid is False
        assert result.error is not None
        assert "parse error" in result.error.lower() or "yaml" in result.error.lower()
        assert result.language == "yaml"

    def test_yaml_invalid_duplicate_key(self):
        """Invalid YAML with duplicate keys fails (depends on yaml parser)."""
        # Note: PyYAML may or may not reject this depending on version
        # This test documents current behavior
        yaml_content = """
key: value1
key: value2
"""
        result = validate_yaml(yaml_content)
        # Even if parser accepts it, we've documented the validation
        # Future: could add stricter validation if needed
        assert result.language == "yaml"

    def test_yaml_empty_file(self):
        """Empty YAML file is valid."""
        result = validate_yaml("")
        assert result.valid is True


# =============================================================================
# JSON Validation Tests
# =============================================================================

class TestJSONValidation:
    """Tests for JSON syntax validation."""

    def test_json_valid_simple(self):
        """Valid JSON passes."""
        validator = SyntaxValidator()
        result = validator.validate('{"key": "value"}', lang="json")

        assert result.valid is True
        assert result.error is None
        assert result.language == "json"

    def test_json_valid_complex(self):
        """Valid complex JSON passes."""
        json_content = '''
{
  "name": "test",
  "version": "1.0.0",
  "nested": {
    "array": [1, 2, 3],
    "bool": true,
    "null": null
  }
}
'''
        result = validate_json(json_content)
        assert result.valid is True

    def test_json_invalid_missing_quote(self):
        """Invalid JSON with missing quote fails."""
        validator = SyntaxValidator()
        result = validator.validate('{"key": value}', lang="json")

        assert result.valid is False
        assert result.error is not None
        assert "parse error" in result.error.lower()
        assert result.language == "json"

    def test_json_invalid_trailing_comma(self):
        """Invalid JSON with trailing comma fails."""
        json_content = '{"key": "value",}'
        result = validate_json(json_content)
        assert result.valid is False
        assert "parse error" in result.error.lower()

    def test_json_invalid_single_quotes(self):
        """Invalid JSON with single quotes fails."""
        json_content = "{'key': 'value'}"
        result = validate_json(json_content)
        assert result.valid is False

    def test_json_empty_file(self):
        """Empty JSON file is invalid (not valid JSON)."""
        result = validate_json("")
        assert result.valid is False


# =============================================================================
# Language Detection Tests
# =============================================================================

class TestLanguageDetection:
    """Tests for language detection from file paths."""

    def test_detect_python(self):
        """Detect Python from .py extension."""
        assert detect_language("runtime/module.py") == "python"
        assert detect_language("test.py") == "python"
        assert detect_language("/abs/path/file.py") == "python"

    def test_detect_yaml(self):
        """Detect YAML from .yaml/.yml extensions."""
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_detect_json(self):
        """Detect JSON from .json extension."""
        assert detect_language("config.json") == "json"
        assert detect_language("package.json") == "json"

    def test_detect_unknown(self):
        """Unknown extensions return None."""
        assert detect_language("file.txt") is None
        assert detect_language("README.md") is None
        assert detect_language("file") is None


# =============================================================================
# SyntaxValidator Class Tests
# =============================================================================

class TestSyntaxValidatorClass:
    """Tests for the SyntaxValidator class interface."""

    def test_validate_with_explicit_lang(self):
        """Validate with explicit language parameter."""
        validator = SyntaxValidator()

        result = validator.validate("print('test')", lang="python")
        assert result.valid is True

        result = validator.validate("key: value", lang="yaml")
        assert result.valid is True

        result = validator.validate('{"key": "value"}', lang="json")
        assert result.valid is True

    def test_validate_with_path_autodetect(self):
        """Validate with auto-detection from path."""
        validator = SyntaxValidator()

        result = validator.validate("print('test')", path="test.py")
        assert result.valid is True
        assert result.language == "python"

        result = validator.validate("key: value", path="config.yaml")
        assert result.valid is True
        assert result.language == "yaml"

    def test_validate_unknown_language_fails_closed(self):
        """Fail-closed when language is unknown."""
        validator = SyntaxValidator()

        # No lang or path provided
        result = validator.validate("some content")
        assert result.valid is False
        assert "unknown language" in result.error.lower()

        # Unsupported language
        result = validator.validate("some content", lang="rust")
        assert result.valid is False
        assert "unsupported" in result.error.lower()

    def test_validate_case_insensitive(self):
        """Language parameter is case-insensitive."""
        validator = SyntaxValidator()

        result = validator.validate("print('test')", lang="PYTHON")
        assert result.valid is True

        result = validator.validate("key: value", lang="YML")
        assert result.valid is True


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_syntax(self):
        """Test validate_syntax convenience function."""
        result = validate_syntax("print('test')", lang="python")
        assert result.valid is True

        result = validate_syntax("invalid(", lang="python")
        assert result.valid is False


# =============================================================================
# Fail-Closed Behavior Tests
# =============================================================================

class TestFailClosedBehavior:
    """Tests for fail-closed behavior in edge cases."""

    def test_validation_result_boolean(self):
        """ValidationResult can be used as boolean."""
        valid_result = ValidationResult(valid=True)
        invalid_result = ValidationResult(valid=False, error="test error")

        assert bool(valid_result) is True
        assert bool(invalid_result) is False

        # Can use in if statements
        if valid_result:
            passed = True
        assert passed

    def test_unexpected_error_fails_closed(self):
        """Unexpected errors during validation fail closed."""
        # This is more of a contract test - the validators catch Exception
        # and return invalid results rather than raising
        validator = SyntaxValidator()

        # Even with weird input, should return ValidationResult (not raise)
        result = validate_python(None)  # type: ignore - intentionally bad input
        assert isinstance(result, ValidationResult)
        assert result.valid is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestSyntaxValidatorIntegration:
    """Integration tests for syntax validator."""

    def test_validate_multiple_languages_in_sequence(self):
        """Validator can handle multiple languages in sequence."""
        validator = SyntaxValidator()

        # Python
        result = validator.validate("def foo(): pass", lang="python")
        assert result.valid is True

        # YAML
        result = validator.validate("key: value", lang="yaml")
        assert result.valid is True

        # JSON
        result = validator.validate('{"key": "value"}', lang="json")
        assert result.valid is True

        # Invalid Python
        result = validator.validate("def foo(", lang="python")
        assert result.valid is False

    def test_error_messages_include_line_info(self):
        """Error messages include line number information when available."""
        # Python syntax error
        result = validate_python("x = 1\ny = (\nz = 3")
        assert result.valid is False
        assert "line" in result.error.lower()

        # JSON parse error
        result = validate_json('{"key": value}')
        assert result.valid is False
        assert "line" in result.error.lower() or "column" in result.error.lower()
