"""
Syntax Validator - Fail-closed syntax validation for code autonomy.

Per Phase 4D specification:
- Validates Python (via AST parsing)
- Validates YAML (via yaml.safe_load)
- Validates JSON (via json.loads)
- Fail-closed: any parse error blocks the write

v1.0: Initial implementation
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ValidationResult:
    """
    Result of syntax validation.

    Attributes:
        valid: True if syntax is valid
        error: Error message if invalid (None if valid)
        language: Language that was validated
    """
    valid: bool
    error: Optional[str] = None
    language: Optional[str] = None

    def __bool__(self) -> bool:
        """Allow boolean checks: if result: ..."""
        return self.valid


# =============================================================================
# Language Detection
# =============================================================================

def detect_language(path: str) -> Optional[str]:
    """
    Detect language from file extension.

    Args:
        path: File path

    Returns:
        Language name ("python", "yaml", "json") or None if unknown
    """
    suffix = Path(path).suffix.lower()

    if suffix in [".py"]:
        return "python"
    elif suffix in [".yaml", ".yml"]:
        return "yaml"
    elif suffix in [".json"]:
        return "json"

    return None


# =============================================================================
# Validators
# =============================================================================

def validate_python(content: str) -> ValidationResult:
    """
    Validate Python syntax using AST parsing.

    Args:
        content: Python source code

    Returns:
        ValidationResult with valid=True or error details
    """
    try:
        ast.parse(content)
        return ValidationResult(valid=True, language="python")
    except SyntaxError as e:
        error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"
        return ValidationResult(
            valid=False,
            error=error_msg,
            language="python"
        )
    except Exception as e:
        # Catch unexpected parse errors (e.g., encoding issues)
        return ValidationResult(
            valid=False,
            error=f"Parse error: {type(e).__name__}: {e}",
            language="python"
        )


def validate_yaml(content: str) -> ValidationResult:
    """
    Validate YAML syntax using yaml.safe_load.

    Args:
        content: YAML source

    Returns:
        ValidationResult with valid=True or error details
    """
    if not YAML_AVAILABLE:
        # Fail-closed: if YAML library not available, we can't validate
        return ValidationResult(
            valid=False,
            error="YAML validation unavailable (PyYAML not installed)",
            language="yaml"
        )

    try:
        yaml.safe_load(content)
        return ValidationResult(valid=True, language="yaml")
    except yaml.YAMLError as e:
        error_msg = f"YAML parse error: {e}"
        return ValidationResult(
            valid=False,
            error=error_msg,
            language="yaml"
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Parse error: {type(e).__name__}: {e}",
            language="yaml"
        )


def validate_json(content: str) -> ValidationResult:
    """
    Validate JSON syntax using json.loads.

    Args:
        content: JSON source

    Returns:
        ValidationResult with valid=True or error details
    """
    try:
        json.loads(content)
        return ValidationResult(valid=True, language="json")
    except json.JSONDecodeError as e:
        error_msg = f"JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}"
        return ValidationResult(
            valid=False,
            error=error_msg,
            language="json"
        )
    except Exception as e:
        return ValidationResult(
            valid=False,
            error=f"Parse error: {type(e).__name__}: {e}",
            language="json"
        )


# =============================================================================
# Main Validator Interface
# =============================================================================

class SyntaxValidator:
    """
    Syntax validator for multiple languages.

    Usage:
        validator = SyntaxValidator()
        result = validator.validate(content, lang="python")
        if not result.valid:
            raise SyntaxError(result.error)
    """

    def validate(
        self,
        content: str,
        lang: Optional[str] = None,
        path: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate syntax for the given content.

        Args:
            content: Source code to validate
            lang: Language ("python", "yaml", "json") - auto-detected if None
            path: File path (used for auto-detection if lang not specified)

        Returns:
            ValidationResult
        """
        # Auto-detect language if not specified
        if lang is None and path is not None:
            lang = detect_language(path)

        # Fail-closed: if language unknown, we can't validate
        if lang is None:
            return ValidationResult(
                valid=False,
                error="Cannot validate: unknown language (no lang or path provided)",
                language=None
            )

        # Route to appropriate validator
        lang_lower = lang.lower()

        if lang_lower == "python":
            return validate_python(content)
        elif lang_lower in ["yaml", "yml"]:
            return validate_yaml(content)
        elif lang_lower == "json":
            return validate_json(content)
        else:
            # Fail-closed: unknown language
            return ValidationResult(
                valid=False,
                error=f"Cannot validate: unsupported language '{lang}'",
                language=lang
            )

    def validate_file(self, path: str) -> ValidationResult:
        """
        Validate syntax of a file.

        Args:
            path: File path to validate

        Returns:
            ValidationResult
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            return self.validate(content, path=path)
        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                error=f"File not found: {path}",
                language=detect_language(path)
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Cannot read file: {type(e).__name__}: {e}",
                language=detect_language(path)
            )


# =============================================================================
# Convenience Functions
# =============================================================================

def validate_syntax(
    content: str,
    lang: Optional[str] = None,
    path: Optional[str] = None
) -> ValidationResult:
    """
    Convenience function for syntax validation.

    Args:
        content: Source code to validate
        lang: Language ("python", "yaml", "json")
        path: File path (for auto-detection)

    Returns:
        ValidationResult
    """
    validator = SyntaxValidator()
    return validator.validate(content, lang=lang, path=path)
