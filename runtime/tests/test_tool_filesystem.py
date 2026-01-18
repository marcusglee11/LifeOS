"""
Tests for Filesystem Tool Handlers.

Per Plan_Tool_Invoke_MVP_v0.2:
- Containment: Path escape blocked with PolicyDenied and no side effects
- Symlink defense: Symlink escape blocked
- Encoding: UTF-8 only, EncodingError on decode failure
- read_file: NotFound for non-existent
- write_file: Empty content creates 0-byte file
- list_dir: Deterministic lexicographic ordering
"""

import hashlib
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from runtime.tools.filesystem import (
    handle_read_file,
    handle_write_file,
    handle_list_dir,
    check_containment,
    ContainmentError,
    compute_file_hash,
)
from runtime.tools.schemas import ToolErrorType


class TestContainment:
    """Tests for path containment checking."""
    
    def test_relative_path_within_sandbox(self, tmp_path):
        """Relative path within sandbox is allowed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = check_containment("test.txt", tmp_path)
        assert result == test_file.resolve()
    
    def test_dotdot_escape_blocked(self, tmp_path):
        """.. escape attempt is blocked with ContainmentError."""
        with pytest.raises(ContainmentError) as exc_info:
            check_containment("../escape.txt", tmp_path)
        
        assert "escapes" in str(exc_info.value).lower() or "escape" in str(exc_info.value).lower()
    
    def test_dotdot_escape_no_side_effects(self, tmp_path):
        """.. escape attempt creates no files."""
        escape_path = tmp_path.parent / "escape.txt"
        
        # Ensure file doesn't exist
        if escape_path.exists():
            escape_path.unlink()
        
        # Attempt containment check (should fail)
        try:
            check_containment("../escape.txt", tmp_path)
        except ContainmentError:
            pass
        
        # Verify no file was created
        assert not escape_path.exists()
    
    def test_symlink_escape_blocked(self, tmp_path):
        """Symlink pointing outside sandbox is blocked."""
        outside_dir = tmp_path.parent / "outside_target"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("secret")
        
        symlink = tmp_path / "escape_link"
        try:
            symlink.symlink_to(outside_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")
        
        with pytest.raises(ContainmentError) as exc_info:
            check_containment("escape_link", tmp_path)
        
        assert "symlink" in str(exc_info.value).lower()
    
    def test_absolute_path_within_sandbox(self, tmp_path):
        """Absolute path within sandbox is allowed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = check_containment(str(test_file), tmp_path)
        assert result == test_file.resolve()
    
    def test_absolute_path_outside_sandbox_blocked(self, tmp_path):
        """Absolute path outside sandbox is blocked."""
        outside_path = str(tmp_path.parent / "outside.txt")
        
        with pytest.raises(ContainmentError):
            check_containment(outside_path, tmp_path)


class TestReadFile:
    """Tests for filesystem.read_file handler."""
    
    def test_read_existing_file_success(self, tmp_path):
        """Read existing file returns content and correct hash."""
        test_file = tmp_path / "test.txt"
        content = "Hello, World!"
        test_file.write_text(content, encoding="utf-8")
        
        result = handle_read_file({"path": "test.txt"}, tmp_path)
        
        assert result.ok is True
        assert result.output.stdout == content
        assert result.effects is not None
        assert len(result.effects.files_read) == 1
        assert result.effects.files_read[0].size_bytes == len(content.encode("utf-8"))
        assert result.effects.files_read[0].sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def test_read_nonexistent_file_returns_not_found(self, tmp_path):
        """Read non-existent file returns NotFound error."""
        result = handle_read_file({"path": "nonexistent.txt"}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.NOT_FOUND
    
    def test_read_binary_file_returns_encoding_error(self, tmp_path):
        """Read binary (non-UTF8) file returns EncodingError."""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x80\x81\x82\x83\xff\xfe")
        
        result = handle_read_file({"path": "binary.bin"}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.ENCODING_ERROR
    
    def test_read_missing_path_arg_returns_schema_error(self, tmp_path):
        """Missing path argument returns SchemaError."""
        result = handle_read_file({}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.SCHEMA_ERROR
    
    def test_read_path_escape_returns_policy_denied(self, tmp_path):
        """Path escape attempt returns PolicyDenied."""
        result = handle_read_file({"path": "../escape.txt"}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.POLICY_DENIED


class TestWriteFile:
    """Tests for filesystem.write_file handler."""
    
    def test_write_file_success(self, tmp_path):
        """Write file creates file with correct content and hash."""
        content = "Test content"
        
        result = handle_write_file({"path": "output.txt", "content": content}, tmp_path)
        
        assert result.ok is True
        assert result.effects is not None
        assert len(result.effects.files_written) == 1
        
        written_file = tmp_path / "output.txt"
        assert written_file.exists()
        assert written_file.read_text(encoding="utf-8") == content
        
        # Verify hash
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.effects.files_written[0].sha256 == expected_hash
        assert result.effects.files_written[0].size_bytes == len(content.encode("utf-8"))
    
    def test_write_empty_content_success(self, tmp_path):
        """Write empty content creates 0-byte file successfully."""
        result = handle_write_file({"path": "empty.txt", "content": ""}, tmp_path)
        
        assert result.ok is True
        assert result.effects is not None
        assert result.effects.files_written[0].size_bytes == 0
        
        empty_file = tmp_path / "empty.txt"
        assert empty_file.exists()
        assert empty_file.stat().st_size == 0
        
        # Verify hash of empty content
        expected_hash = hashlib.sha256(b"").hexdigest()
        assert result.effects.files_written[0].sha256 == expected_hash
    
    def test_write_creates_parent_directories(self, tmp_path):
        """Write file creates parent directories as needed."""
        result = handle_write_file({
            "path": "nested/dir/file.txt",
            "content": "nested content"
        }, tmp_path)
        
        assert result.ok is True
        
        nested_file = tmp_path / "nested" / "dir" / "file.txt"
        assert nested_file.exists()
        assert nested_file.read_text() == "nested content"
    
    def test_write_path_escape_returns_policy_denied(self, tmp_path):
        """Path escape attempt returns PolicyDenied."""
        result = handle_write_file({
            "path": "../escape.txt",
            "content": "should not write"
        }, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.POLICY_DENIED
    
    def test_write_path_escape_no_side_effects(self, tmp_path):
        """Path escape attempt creates no file outside sandbox."""
        escape_path = tmp_path.parent / "escape.txt"
        
        # Ensure file doesn't exist
        if escape_path.exists():
            escape_path.unlink()
        
        # Attempt write (should fail)
        result = handle_write_file({
            "path": "../escape.txt",
            "content": "should not write"
        }, tmp_path)
        
        assert result.ok is False
        assert not escape_path.exists()


class TestListDir:
    """Tests for filesystem.list_dir handler."""
    
    def test_list_dir_success(self, tmp_path):
        """List directory returns entries."""
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.txt").write_text("2")
        (tmp_path / "subdir").mkdir()
        
        result = handle_list_dir({"path": "."}, tmp_path)
        
        assert result.ok is True
        assert "file1.txt" in result.output.stdout
        assert "file2.txt" in result.output.stdout
        assert "subdir" in result.output.stdout
    
    def test_list_dir_deterministic_ordering(self, tmp_path):
        """List directory returns lexicographically sorted entries."""
        # Create files in non-sorted order
        (tmp_path / "zebra.txt").write_text("z")
        (tmp_path / "apple.txt").write_text("a")
        (tmp_path / "banana.txt").write_text("b")
        
        result = handle_list_dir({"path": "."}, tmp_path)
        
        assert result.ok is True
        lines = result.output.stdout.strip().split("\n")
        
        # Verify sorted order
        assert lines == sorted(lines)
        assert "apple.txt" in lines[0] or lines[0] == "apple.txt"
    
    def test_list_dir_nonexistent_returns_not_found(self, tmp_path):
        """List non-existent directory returns NotFound."""
        result = handle_list_dir({"path": "nonexistent"}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.NOT_FOUND
    
    def test_list_dir_path_escape_returns_policy_denied(self, tmp_path):
        """Path escape attempt returns PolicyDenied."""
        result = handle_list_dir({"path": ".."}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.POLICY_DENIED
