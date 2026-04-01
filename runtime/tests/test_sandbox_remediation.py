import os
import tempfile
from pathlib import Path

import pytest

from project_builder.config import settings
from project_builder.sandbox.workspace import (
    SecurityViolation,
    materialize_workspace,
    verify_hardlink_defense,
)


def test_unicode_safety_combining_marks():
    """Test that paths with combining marks are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 'e' + combining acute accent
        path = "t" + "\u0301" + "est.txt"

        with pytest.raises(SecurityViolation, match="invalid_artifact_path.*combining marks"):
            materialize_workspace(root, [(path, b"content", "2023-01-01")])


def test_unicode_safety_normalization():
    """Test that paths are normalized to NFC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 'e' + combining acute accent (NFD)
        nfd_path = "e" + "\u0301"
        # NFC equivalent
        nfc_path = "\u00e9"

        # Should be normalized and written as NFC
        materialize_workspace(root, [(nfd_path, b"content", "2023-01-01")])

        assert (root / nfc_path).exists()
        # NFD path string check might fail depending on OS filesystem normalization,
        # but we check if the file exists under the NFC name.


def test_resource_limit_file_size():
    """Test that files exceeding MAX_FILE_SIZE_BYTES are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create content larger than limit (10MB)
        # We'll mock the setting to be small for test speed
        original_limit = settings.MAX_FILE_SIZE_BYTES
        settings.MAX_FILE_SIZE_BYTES = 100  # 100 bytes

        try:
            large_content = b"a" * 101
            with pytest.raises(SecurityViolation, match="resource_limit_exceeded"):
                materialize_workspace(root, [("large.txt", large_content, "2023-01-01")])
        finally:
            settings.MAX_FILE_SIZE_BYTES = original_limit


@pytest.mark.skipif(os.name == "nt", reason="POSIX only")
def test_hardlink_defense_posix_same_device_fails():
    """POSIX must reject workspace/output directories on the same device."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ws = root / "workspace"
        out = root / "output"

        with pytest.raises(SecurityViolation, match="hardlink_defense_failure"):
            verify_hardlink_defense(ws, out)


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_hardlink_defense_windows_same_device_warns():
    """Windows keeps the weaker same-device tolerance path for local dev."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ws = root / "workspace"
        out = root / "output"

        verify_hardlink_defense(ws, out)


def test_unicode_percent_rejection():
    """Test that paths with % are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        with pytest.raises(SecurityViolation, match="invalid_artifact_path.*%"):
            materialize_workspace(root, [("test%20file.txt", b"content", "2023-01-01")])
