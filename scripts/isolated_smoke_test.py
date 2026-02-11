#!/usr/bin/env python3
import sys
import subprocess
import shutil
import tempfile
import json
import os
from pathlib import Path

def run_cmd(cmd, cwd=None, capture=True, env=None):
    """Run a command safely and return result."""
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            check=False,
            env=env
        )
        return res
    except Exception as e:
        print(f"ERROR executing {cmd}: {e}")
        return None

def run_cmd_ok(cmd, cwd=None, env=None):
    """Run a command and exit on failure with detailed feedback."""
    res = run_cmd(cmd, cwd=cwd, env=env)
    if not res or res.returncode != 0:
        print(f"\nFATAL: Command failed: {' '.join(cmd)}")
        if res:
            print(f"EXIT CODE: {res.returncode}")
            if res.stdout:
                print("--- STDOUT ---")
                print(res.stdout.strip()[-2000:]) # last 2000 chars
            if res.stderr:
                print("--- STDERR ---")
                print(res.stderr.strip()[-2000:]) # last 2000 chars
        sys.exit(1)
    return res

def main():
    # 1. Determine repo root
    repo_root_res = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if not repo_root_res or repo_root_res.returncode != 0:
        print("ERROR: Could not determine repo root.")
        sys.exit(1)
    repo_root = Path(repo_root_res.stdout.strip())

    # 2. Create temp dir and detached worktree
    temp_dir = Path(tempfile.mkdtemp(prefix="lifeos_smoke_"))
    print(f"INFO: Creating isolated worktree at {temp_dir}")
    
    run_cmd_ok(["git", "worktree", "add", "--detach", str(temp_dir), "HEAD"], cwd=repo_root)
    
    try:
        # 3. Inside the worktree: Setup environment
        print("INFO: Setting up virtual environment in worktree...")
        venv_dir = temp_dir / ".venv_smoke"
        run_cmd_ok([sys.executable, "-m", "venv", str(venv_dir)], cwd=temp_dir)
        
        # Determine paths to venv binaries (OS dependent)
        if sys.platform == "win32":
            pip_path = venv_dir / "Scripts" / "pip.exe"
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"

        # Update pip and install editable
        print("INFO: Updating pip...")
        run_cmd_ok([str(python_path), "-m", "pip", "install", "-U", "pip"], cwd=temp_dir)
        
        # Install dependencies if requirements.txt exists
        requirements_txt = repo_root / "requirements.txt"
        if requirements_txt.exists():
            print("INFO: Installing requirements.txt...")
            run_cmd_ok([str(pip_path), "install", "-r", str(requirements_txt)], cwd=temp_dir)
        
        print("INFO: Installing package in editable mode...")
        run_cmd_ok([str(pip_path), "install", "-e", "."], cwd=temp_dir)

        # 4. Run deterministic CLI invocation (E2E-1: noop mission)
        print("INFO: Running smoke test (noop mission)...")
        # Command from E2E-1: ["mission", "run", "noop", "--params", "{}", "--json"]
        smoke_cmd = [str(python_path), "-m", "runtime.cli", "mission", "run", "noop", "--params", "{}", "--json"]
        
        smoke_res = run_cmd_ok(smoke_cmd, cwd=temp_dir)

        # Parse JSON and assert required fields
        try:
            data = json.loads(smoke_res.stdout)
        except json.JSONDecodeError:
            print("ERROR: Failed to parse CLI output as JSON")
            print(f"Raw output: {smoke_res.stdout}")
            sys.exit(1)

        # Assertions
        required_fields = [
            "acceptance_token_path",
            "acceptance_record_path",
            "acceptance_token_sha256",
            "evidence_manifest_sha256"
        ]
        
        errors = []
        if not data.get("success"):
            errors.append("success == False in JSON output")
            
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif "path" in field:
                val = data[field]
                if not val:
                    errors.append(f"Field {field} is empty or null")
                else:
                    p = Path(val)
                    if not p.is_absolute():
                        p = (temp_dir / p).resolve()
                    if not p.exists():
                        errors.append(f"Path field {field} points to non-existent file: {p}")

        if errors:
            print("\nERROR: Smoke test assertions failed:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

        print("\nSUCCESS: Isolated smoke test passes (deterministic proof validated).")
        sys.exit(0)

    finally:
        # 5. Cleanup ALWAYS
        print(f"INFO: Cleaning up worktree at {temp_dir}")
        run_cmd(["git", "worktree", "remove", "--force", str(temp_dir)], cwd=repo_root)
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
