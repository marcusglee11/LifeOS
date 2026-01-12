"""
OpenCode Governance Service Phase 1 — TDD Contract Tests
"""
import sys
import json
import subprocess
import pytest
from pathlib import Path

# Sentinel-based REPO_ROOT finding (P1-6)
def find_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    while current != current.parent:
        if (current / "doc_steward").exists() or (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find REPO_ROOT (doc_steward/ not found)")

REPO_ROOT = find_repo_root(Path(__file__))
sys.path.insert(0, str(REPO_ROOT))

# Fix YAML path escapes for Windows
import os

from opencode_governance import invoke
from opencode_governance.errors import (
    INVALID_VERSION,
    MISSING_REQUEST_ID,
    INVALID_PAYLOAD,
    INTERNAL_ERROR
)

# T1: Service boots (Smoke)
def test_t1_service_boots_smoke():
    """T1: Service accepts valid input and returns OK."""
    req = {
        "version": "1.0",
        "request_id": "test-t1",
        "payload": {"key": "value"}
    }
    resp = invoke(req)
    assert resp["status"] == "OK"
    assert resp["request_id"] == "test-t1"
    assert "output" in resp
    assert "output_hash" in resp

# T2: Contract rejects invalid input
def test_t2_rejects_missing_field():
    """T2: Missing request_id -> MISSING_REQUEST_ID."""
    req = {"version": "1.0", "payload": {}}
    resp = invoke(req)
    assert resp["status"] == "ERROR"
    assert resp["error"]["code"] == MISSING_REQUEST_ID

def test_t2_rejects_invalid_version():
    """T2: Wrong version -> INVALID_VERSION."""
    req = {
        "version": "0.9", 
        "request_id": "test-t2", 
        "payload": {}
    }
    resp = invoke(req)
    assert resp["status"] == "ERROR"
    assert resp["error"]["code"] == INVALID_VERSION

def test_t2_rejects_missing_payload():
    """T2: Missing payload -> INVALID_PAYLOAD."""
    req = {
        "version": "1.0", 
        "request_id": "test-t2"
    }
    resp = invoke(req)
    assert resp["status"] == "ERROR"
    assert resp["error"]["code"] == INVALID_PAYLOAD

def test_t2_rejects_invalid_payload_type():
    """T2: Payload not a dict -> INVALID_PAYLOAD (P0-2)."""
    req = {
        "version": "1.0",
        "request_id": "test-t2-type",
        "payload": "not-a-dict"
    }
    resp = invoke(req)
    assert resp["status"] == "ERROR"
    assert resp["error"]["code"] == INVALID_PAYLOAD

# T2-b: Internal Error Guard (P0-1)
def test_t2b_internal_error_guard():
    """T2b: Invoke catches exception and returns INTERNAL_ERROR."""
    # We mock _canonical_json to raise an exception to trigger the guard
    import opencode_governance.service as service_module
    
    original = service_module._canonical_json
    try:
        def raise_err(_):
            raise ValueError("Simulated crash")
        service_module._canonical_json = raise_err
        
        req = {
            "version": "1.0", 
            "request_id": "test-guard", 
            "payload": {"a": 1}
        }
        resp = invoke(req)
        assert resp["status"] == "ERROR"
        assert resp["request_id"] == "test-guard"
        assert resp["error"]["code"] == INTERNAL_ERROR
        # P0-1: No traceback in message
        assert resp["error"]["message"] == "Internal error"
    finally:
        service_module._canonical_json = original

# T3: Determinism
def test_t3_determinism():
    """T3: Output hash is stable for identical inputs."""
    req = {
        "version": "1.0",
        "request_id": "test-t3",
        "payload": {"a": 1, "b": 2}
    }
    resp1 = invoke(req)
    resp2 = invoke(req)
    
    assert resp1["output_hash"] == resp2["output_hash"]
    # Ensure hash is actually present and looks like SHA256
    assert len(resp1["output_hash"]) == 64

# T4: Doc Steward Rules
def test_t4_steward_opencode_validate(tmp_path):
    """T4: opencode-validate checks for artifacts/opencode existence."""
    # Case 1: Missing directory -> Fail
    cmd = [
        sys.executable, "-m", "doc_steward.cli", "opencode-validate", str(tmp_path)
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Missing required directory" in res.stdout

    # Case 2: Exists -> Pass
    artifacts = tmp_path / "artifacts" / "opencode"
    artifacts.mkdir(parents=True)
    
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 0
    assert "PASSED" in res.stdout or "Passed" in res.stdout or "passed" in res.stdout

# T5: Evidence Capture
def test_t5_canonical_evidence_capture(tmp_path):
    """T5: steward_runner captures multiline output without elision (Isolated)."""
    
    # 1. Setup Isolated Logging (P0-4)
    # Using tmp_path for isolation. 
    # Absolute paths required for steward_runner config when running from REPO_ROOT.
    log_dir = tmp_path / "logs"
    streams_dir = log_dir / "streams"
    
    # Generate unique run ID for contamination proofing (P0-5)
    run_id = f"test_t5_{tmp_path.name}"
    
    log_dir_str = str(log_dir).replace(os.sep, '/')
    streams_dir_str = str(streams_dir).replace(os.sep, '/')
    
    config_content = f"""
logging:
  log_dir: "{log_dir_str}"
  streams_dir: "{streams_dir_str}"
determinism:
  timestamps: false
"""
    config_file = tmp_path / "t5_config.yaml"
    config_file.write_text(config_content, encoding="utf-8")
    
    # 2. Create a script that prints multiline output
    script_content = """
for i in range(100):
    print(f"Line {i}: This is a test line for evidence capture verification.")
"""
    script_file = tmp_path / "print_huge.py"
    script_file.write_text(script_content, encoding="utf-8")
    
    # 3. Invoke steward_runner manually via subprocess
    
    full_config_content = f"""
logging:
  log_dir: "{log_dir_str}"
  streams_dir: "{streams_dir_str}"
validators:
  commands:
    - ["{sys.executable.replace(os.sep, '/')}", "{str(script_file).replace(os.sep, '/')}"]
"""
    config_file.write_text(full_config_content, encoding="utf-8")
    
    runner_path = REPO_ROOT / "scripts" / "steward_runner.py"
    
    cmd = [
        sys.executable, str(runner_path),
        "--config", str(config_file),
        "--run-id", run_id,
        "--step", "validators"
    ]
    
    # Run it
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"STDOUT: {res.stdout}")
        print(f"STDERR: {res.stderr}")
    assert res.returncode == 0, f"Runner failed with code {res.returncode}"
    
    # 4. Verification
    # Check that logs were created in the ISOLATED directory
    assert streams_dir.exists(), "Streams dir not created in tmp_path"
    
    # Find the stream file (P0-5: Assert against THIS run's stream)
    # Since streams_dir is in tmp_path and fresh, any file here is ours.
    found_content = False
    for stream_file in streams_dir.iterdir():
        content = stream_file.read_text(encoding="utf-8")
        if "Line 0:" in content and "Line 99:" in content:
            found_content = True
            # Verify no elision markers
            assert "..." not in content
            assert "<truncated>" not in content
            # Explicitly count lines
            lines = content.strip().splitlines()
            count = sum(1 for line in lines if "This is a test line" in line)
            assert count == 100
            break
            
    assert found_content, "Did not find full output in stream files in tmp_path"
