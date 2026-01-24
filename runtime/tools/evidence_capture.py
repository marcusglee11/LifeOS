import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

class CaptureStatus(Enum):
    OK = "OK"
    NONZERO = "NONZERO"
    TIMEOUT = "TIMEOUT"
    EXEC_ERROR = "EXEC_ERROR"

@dataclass
class CaptureResult:
    """Result of command execution with evidence capture. Deterministic version (v0.1)."""
    command: List[str]
    status: CaptureStatus
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    exitcode_sha256: str
    stdout_path: Path
    stderr_path: Path
    exitcode_path: Path
    meta_sha256: str
    meta_path: Path
    
def _compute_sha256(path: Path) -> str:
    """Compute SHA-256 of file on disk (fail-closed)."""
    if not path.exists():
        raise FileNotFoundError(f"evidence_capture missing file: {path.name}")
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def run_command_capture(
    step_name: str,
    cmd: List[str],
    cwd: Path,
    evidence_dir: Path,
    timeout: int = 300
) -> CaptureResult:
    """
    Execute command and capture all outputs to disk with cryptographic hashes.
    
    Required behavior (fail-closed):
    - evidence_dir is created if missing.
    - step_name is deterministically sanitized to a safe filename token.
    - file naming: {token}.stdout, {token}.stderr, {token}.exitcode, {token}.meta.json
    - collision rule: if ANY of these paths already exist, FAIL CLOSED (raise ValueError).
    - streaming rule: execute subprocess with stdout/stderr redirected to binary files.
    """
    # 1. Ensure evidence_dir exists
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # 2. Sanitize step_name
    token = re.sub(r"[^a-zA-Z0-9._-]", "_", step_name)
    token = re.sub(r"_+", "_", token)
    token = token.strip("_")
    if not token:
        token = "step"

    # 3. Define paths
    stdout_path = evidence_dir / f"{token}.stdout"
    stderr_path = evidence_dir / f"{token}.stderr"
    exitcode_path = evidence_dir / f"{token}.exitcode"
    meta_path = evidence_dir / f"{token}.meta.json"

    # 4. Collision Rule
    existing = [p for p in [stdout_path, stderr_path, exitcode_path, meta_path] if p.exists()]
    if existing:
        raise ValueError(f"Collision error: Target evidence files already exist: {[p.name for p in existing]}")

    status = CaptureStatus.OK
    exit_code = 0
    exec_error_msg = None

    # 5. Streaming Execution
    try:
        with open(stdout_path, "wb") as f_stdout, open(stderr_path, "wb") as f_stderr:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    stdout=f_stdout,
                    stderr=f_stderr,
                    timeout=timeout,
                    check=False
                )
                exit_code = proc.returncode
                if exit_code != 0:
                    status = CaptureStatus.NONZERO
                else:
                    status = CaptureStatus.OK
            except subprocess.TimeoutExpired:
                status = CaptureStatus.TIMEOUT
                exit_code = 124
                f_stderr.write(b"\n--- TIMEOUT ---\n")
            except Exception:
                # Includes FileNotFoundError
                status = CaptureStatus.EXEC_ERROR
                exit_code = 127
                # Deterministic marker ONLY (P0.1)
                f_stderr.write(b"\n--- EXEC_ERROR ---\n")

    except Exception as e:
        # File operations failed (e.g. disk full, permission)
        # This is a fatal infrastructure error
        raise RuntimeError(f"Failed to open/write evidence files: {str(e)}")

    # 6. Write exitcode file
    with open(exitcode_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{exit_code}\n")

    # 7. Compute Hashes from Disk
    stdout_sha = _compute_sha256(stdout_path)
    stderr_sha = _compute_sha256(stderr_path)
    exitcode_sha = _compute_sha256(exitcode_path)

    # 8. Write Meta File
    meta_data = {
        "command": cmd,
        "cwd": str(cwd),
        "status": status.value,
        "exit_code": exit_code,
        "filenames": {
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
            "exitcode": exitcode_path.name
        },
        "stdout_sha256": stdout_sha,
        "stderr_sha256": stderr_sha,
        "exitcode_sha256": exitcode_sha
    }
    
    with open(meta_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta_data, f, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    # 9. Compute Meta Hash
    meta_sha = _compute_sha256(meta_path)

    return CaptureResult(
        command=cmd,
        status=status,
        exit_code=exit_code,
        stdout_sha256=stdout_sha,
        stderr_sha256=stderr_sha,
        exitcode_sha256=exitcode_sha,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        exitcode_path=exitcode_path,
        meta_sha256=meta_sha,
        meta_path=meta_path
    )
