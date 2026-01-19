import pytest
import shutil
import os
import hashlib
import json
from pathlib import Path
from runtime.tools.evidence_capture import run_command_capture, CaptureStatus, CaptureResult

def test_successful_command_capture(tmp_path):
    """
    D0.1.2: test_successful_command_capture
    - runs a small deterministic command
    - asserts stdout/stderr/exitcode files exist
    - asserts exitcode file content is exactly "{code}\n"
    - asserts sha256 fields match hashing the on-disk bytes (re-hash in test)
    """
    evidence_dir = tmp_path / "evidence"
    # Using python to print deterministic output
    cmd = ["python", "-c", "import sys; print('hello stdout'); print('hello stderr', file=sys.stderr); sys.exit(0)"]
    
    result = run_command_capture(
        step_name="success_test",
        cmd=cmd,
        cwd=tmp_path,
        evidence_dir=evidence_dir
    )
    
    assert result.status == CaptureStatus.OK
    assert result.exit_code == 0
    
    # Assert files exist
    assert result.stdout_path.exists()
    assert result.stderr_path.exists()
    assert result.exitcode_path.exists()
    assert result.meta_path.exists()
    
    # Assert exitcode file content
    assert result.exitcode_path.read_text(encoding="utf-8") == "0\n"
    
    # Verify hashes against disk
    def compute_sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    
    assert result.stdout_sha256 == compute_sha256(result.stdout_path)
    assert result.stderr_sha256 == compute_sha256(result.stderr_path)
    assert result.exitcode_sha256 == compute_sha256(result.exitcode_path)
    
    # Verify meta file
    with open(result.meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["status"] == "OK"
    assert meta["exit_code"] == 0
    assert meta["stdout_sha256"] == result.stdout_sha256

def test_nonzero_exit_capture(tmp_path):
    """
    D0.1.2: test_nonzero_exit_capture
    - command returns nonzero; status reflects NONZERO; exit_code preserved
    """
    evidence_dir = tmp_path / "evidence"
    cmd = ["python", "-c", "import sys; sys.exit(42)"]
    
    result = run_command_capture("nonzero_test", cmd, tmp_path, evidence_dir)
    
    assert result.status == CaptureStatus.NONZERO
    assert result.exit_code == 42
    assert result.exitcode_path.read_text(encoding="utf-8") == "42\n"

def test_timeout_handling(tmp_path):
    """
    D0.1.2: test_timeout_handling
    - enforce a short timeout; status reflects TIMEOUT; exit_code is 124
    - asserts stderr file contains a deterministic timeout marker string
    """
    evidence_dir = tmp_path / "evidence"
    # Sleep to trigger timeout
    cmd = ["python", "-c", "import time; time.sleep(10)"]
    
    result = run_command_capture("timeout_test", cmd, tmp_path, evidence_dir, timeout=1)
    
    assert result.status == CaptureStatus.TIMEOUT
    assert result.exit_code == 124
    assert "TIMEOUT" in result.stderr_path.read_text(encoding="utf-8")

def test_exec_error_handling(tmp_path):
    """
    D0.1.2: test_exec_error_handling
    - non-existent executable; status reflects EXEC_ERROR; exit_code is 127
    - stderr file contains deterministic marker string
    """
    evidence_dir = tmp_path / "evidence"
    cmd = ["non_existent_command_xyz_123"]
    
    result = run_command_capture("exec_error_test", cmd, tmp_path, evidence_dir)
    
    assert result.status == CaptureStatus.EXEC_ERROR
    assert result.exit_code == 127
    
    # Check deterministic stderr marker (P0.1)
    with open(result.stderr_path, "rb") as f:
        err_content = f.read()
    
    expected_marker = b"\n--- EXEC_ERROR ---\n"
    assert err_content.endswith(expected_marker)
    # Ensure NO exception strings leaked
    assert b"No such file" not in err_content
    assert b"FileNotFoundError" not in err_content

def test_unicode_bytes_preserved(tmp_path):
    """
    D0.1.2: test_unicode_bytes_preserved
    - produce non-ASCII bytes; ensure raw bytes preserved (no decoding)
    """
    evidence_dir = tmp_path / "evidence"
    # Using python to write raw bytes to stdout
    # Heart emoji in UTF-8: \xe2\x9d\xa4
    cmd = ["python", "-c", "import sys; sys.stdout.buffer.write(b'\\xe2\\x9d\\xa4'); sys.stdout.buffer.flush()"]
    
    result = run_command_capture("unicode_test", cmd, tmp_path, evidence_dir)
    
    assert result.status == CaptureStatus.OK
    stdout_bytes = result.stdout_path.read_bytes()
    assert b'\xe2\x9d\xa4' in stdout_bytes

def test_large_output_streaming(tmp_path):
    """
    D0.1.2: test_large_output_streaming
    - produce large stdout; ensure capture completes without truncation
    - assert file size exceeds a meaningful threshold (e.g., > 1MB)
    """
    evidence_dir = tmp_path / "evidence"
    # Write 2MB of data
    size_mb = 2
    cmd = ["python", "-c", f"import sys; sys.stdout.buffer.write(b'A' * {size_mb} * 1024 * 1024)"]
    
    result = run_command_capture("large_test", cmd, tmp_path, evidence_dir)
    
    assert result.status == CaptureStatus.OK
    file_size = result.stdout_path.stat().st_size
    assert file_size >= size_mb * 1024 * 1024

def test_collision_rule(tmp_path):
    """
    D0.2.2: Collision rule
    - if ANY of these paths already exist, FAIL CLOSED (raise ValueError)
    """
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "collision_test.stdout").touch()
    
    cmd = ["python", "-c", "print('hello')"]
    
    with pytest.raises(ValueError) as excinfo:
        run_command_capture("collision_test", cmd, tmp_path, evidence_dir)
    
    assert "already exist" in str(excinfo.value)

def test_missing_file_hashing_fail_closed(tmp_path):
    """Test fail-closed hashing if file is missing (P0.2)."""
    from runtime.tools.evidence_capture import _compute_sha256
    
    missing_path = tmp_path / "does_not_exist.txt"
    
    with pytest.raises(FileNotFoundError) as excinfo:
        _compute_sha256(missing_path)
    
    # Assert exact message requirement (D0.2.1)
    assert f"evidence_capture missing file: {missing_path.name}" in str(excinfo.value)
