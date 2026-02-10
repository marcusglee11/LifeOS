"""
Tests for runtime/config/loader.py — Config file loading

Test Coverage:
- File existence validation
- YAML parsing (valid/malformed)
- Root type validation (dict required)
- Key type validation (string keys required)
- Edge cases (empty, null, nested structures)
"""

import pytest
import tempfile
from pathlib import Path
from runtime.config.loader import load_config


class TestFileExistenceValidation:
    """Test suite for file existence validation."""

    def test_load_nonexistent_file(self):
        """load_config raises ValueError for missing file."""
        nonexistent = Path("/tmp/nonexistent_config_12345.yaml")
        with pytest.raises(ValueError) as exc:
            load_config(nonexistent)
        assert "Config file not found" in str(exc.value)
        assert str(nonexistent) in str(exc.value)

    def test_load_nonexistent_path_error_message(self):
        """Error message includes the full path for missing files."""
        test_path = Path("/tmp/test/nested/missing.yaml")
        with pytest.raises(ValueError) as exc:
            load_config(test_path)
        assert str(test_path) in str(exc.value)


class TestYAMLParsing:
    """Test suite for YAML parsing."""

    def test_load_valid_yaml(self):
        """load_config successfully loads valid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("key: value\n")
            f.write("number: 42\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {"key": "value", "number": 42}
        finally:
            temp_path.unlink()

    def test_load_malformed_yaml(self):
        """load_config raises ValueError for malformed YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("key: value\n")
            f.write("  bad indentation:\n")
            f.write("malformed\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Malformed YAML" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_invalid_yaml_syntax(self):
        """load_config raises ValueError for invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("key: [unclosed list\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Malformed YAML" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_empty_file(self):
        """load_config returns empty dict for empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Write nothing
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {}
        finally:
            temp_path.unlink()

    def test_load_yaml_with_comments(self):
        """load_config handles YAML comments correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("key: value  # inline comment\n")
            f.write("# Another comment\n")
            f.write("number: 42\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {"key": "value", "number": 42}
        finally:
            temp_path.unlink()


class TestRootTypeValidation:
    """Test suite for root type validation."""

    def test_load_dict_root_valid(self):
        """load_config accepts dictionary root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("key1: value1\n")
            f.write("key2: value2\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert isinstance(config, dict)
            assert config == {"key1": "value1", "key2": "value2"}
        finally:
            temp_path.unlink()

    def test_load_list_root_invalid(self):
        """load_config rejects list root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- item1\n")
            f.write("- item2\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config root must be a mapping (dict)" in str(exc.value)
            assert "list" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_string_root_invalid(self):
        """load_config rejects string root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("just a string\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config root must be a mapping (dict)" in str(exc.value)
            assert "str" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_number_root_invalid(self):
        """load_config rejects number root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("42\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config root must be a mapping (dict)" in str(exc.value)
            assert "int" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_bool_root_invalid(self):
        """load_config rejects boolean root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("true\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config root must be a mapping (dict)" in str(exc.value)
            assert "bool" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_null_root_returns_empty_dict(self):
        """load_config returns empty dict for null/None root."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("null\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {}
        finally:
            temp_path.unlink()


class TestKeyTypeValidation:
    """Test suite for key type validation."""

    def test_load_string_keys_valid(self):
        """load_config accepts string keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("string_key: value\n")
            f.write("another_key: value2\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert "string_key" in config
            assert "another_key" in config
        finally:
            temp_path.unlink()

    def test_load_integer_keys_invalid(self):
        """load_config rejects integer keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("123: value\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config keys must be strings" in str(exc.value)
            assert "int" in str(exc.value)
        finally:
            temp_path.unlink()

    def test_load_mixed_key_types_invalid(self):
        """load_config rejects mixed key types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("valid_key: value1\n")
            f.write("123: value2\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc:
                load_config(temp_path)
            assert "Config keys must be strings" in str(exc.value)
        finally:
            temp_path.unlink()


class TestNestedStructures:
    """Test suite for nested structures."""

    def test_load_nested_dict(self):
        """load_config handles nested dictionaries."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("outer:\n")
            f.write("  inner:\n")
            f.write("    deep: value\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["outer"]["inner"]["deep"] == "value"
        finally:
            temp_path.unlink()

    def test_load_dict_with_list_values(self):
        """load_config handles dictionaries with list values."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("items:\n")
            f.write("  - item1\n")
            f.write("  - item2\n")
            f.write("  - item3\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["items"] == ["item1", "item2", "item3"]
        finally:
            temp_path.unlink()

    def test_load_complex_nested_structure(self):
        """load_config handles complex nested structures."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("database:\n")
            f.write("  host: localhost\n")
            f.write("  port: 5432\n")
            f.write("  credentials:\n")
            f.write("    username: admin\n")
            f.write("    password: secret\n")
            f.write("  features:\n")
            f.write("    - ssl\n")
            f.write("    - backup\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432
            assert config["database"]["credentials"]["username"] == "admin"
            assert "ssl" in config["database"]["features"]
        finally:
            temp_path.unlink()


class TestEncoding:
    """Test suite for file encoding."""

    def test_load_utf8_encoding(self):
        """load_config handles UTF-8 encoded files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write("message: Hello 世界 🌍\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["message"] == "Hello 世界 🌍"
        finally:
            temp_path.unlink()

    def test_load_special_characters(self):
        """load_config handles special characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            # Use single quotes to avoid escape issues in YAML
            f.write("special: '@#$%^&*()_+-={}[]|:;<>?,./'\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert "@#$%^&*()" in config["special"]
        finally:
            temp_path.unlink()


class TestEdgeCases:
    """Test suite for edge cases."""

    def test_load_whitespace_only_file(self):
        """load_config handles whitespace-only files as empty."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # Only use spaces, not tabs (tabs can cause YAML parsing errors)
            f.write("   \n  \n   \n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {}
        finally:
            temp_path.unlink()

    def test_load_single_key_value(self):
        """load_config handles single key-value pair."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("single: value\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == {"single": "value"}
        finally:
            temp_path.unlink()

    def test_load_various_value_types(self):
        """load_config preserves various value types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("string: hello\n")
            f.write("integer: 42\n")
            f.write("float: 3.14\n")
            f.write("boolean: true\n")
            f.write("null_value: null\n")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config["string"] == "hello"
            assert config["integer"] == 42
            assert config["float"] == 3.14
            assert config["boolean"] is True
            assert config["null_value"] is None
        finally:
            temp_path.unlink()
