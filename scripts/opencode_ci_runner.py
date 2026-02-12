#!/usr/bin/env python3
"""
OpenCode CI Runner (CT-2 Phase 3 v2.0)
======================================

Broadened CI runner for doc-steward gate.
All structural operations allowed. Path security checks retained.
"""

import argparse
import time
import requests
import subprocess
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add scripts directory to path for imports if not already there
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Import hardened policy module
import opencode_gate_policy as policy
from opencode_gate_policy import ReasonCode

# Import canonical defaults from single source of truth
# Import canonical defaults from single source of truth
try:
    # Add parent directory to path for runtime imports
    _repo_root = os.path.dirname(_script_dir)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from runtime.agents.models import (
        resolve_model_auto,
        get_api_key_for_role,
        load_model_config,
        validate_config,
    )
    # Default is now 'auto' to trigger resolution logic
    DEFAULT_MODEL = "auto"
except ImportError as e:
    # Fail loud in Phase 3 - we must have runtime access
    print(f"CRITICAL: Failed to import runtime.agents.models: {e}")
    print("This script must be run from within the LifeOS repository.")
    sys.exit(1)

# ============================================================================
# LOGGING
# ============================================================================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

# Global log buffer for evidence bundle
_log_buffer = []

def log(msg, level="info"):
    timestamp = datetime.now().isoformat(sep="T", timespec="seconds")
    color = Colors.RESET
    if level == "error": color = Colors.RED
    elif level == "ok": color = Colors.GREEN
    elif level == "gov": color = Colors.YELLOW
    elif level == "info": color = Colors.BLUE
    
    log_line = f"[{level.upper()}] [{timestamp}] {msg}"
    _log_buffer.append(log_line)
    print(f"{color}{log_line}{Colors.RESET}")

def get_log_buffer() -> str:
    return "\n".join(_log_buffer)

def clear_log_buffer():
    _log_buffer.clear()

def load_api_key(mode: str) -> str:
    """Load the API key for the given mode (steward/builder)."""
    role = "steward" if mode == policy.MODE_STEWARD else "builder"
    
    # Try canonical loading first
    key = get_api_key_for_role(role)
    if key:
        log(f"{role.capitalize()} API Key loaded via config (starts with {key[:8]})", "info")
        return key

    # Fallback to legacy env vars if config/models.yaml lookup failed (shouldn't happen if setup is correct)
    # Priority: ZEN_{ROLE}_KEY > ZEN_STEWARD_KEY
    env_var = f"ZEN_{role.upper()}_KEY"
    key = os.environ.get(env_var)
    if key:
        log(f"{role.capitalize()} API Key loaded via {env_var}", "info")
        return key
        
    log(f"API Key for {role} NOT found", "error")
    return ""

# ============================================================================
# ENVELOPE VALIDATION (POST-DIFF)
# ============================================================================
def validate_all_diff_entries(parsed_diff: List[tuple], mode: str) -> List[Tuple[str, str, str]]:
    """
    Validate all parsed diff entries using policy.validate_operation.
    
    Returns list of (path, operation, reason_code) for blocked entries.
    """
    blocked = []
    
    # Restore Legacy parity: Structural ops blocked in Steward mode
    if mode == policy.MODE_STEWARD:
        blocked_ops = policy.detect_blocked_ops(parsed_diff)
        if blocked_ops:
            return blocked_ops
            
    for entry in parsed_diff:
        if len(entry) == 2:
            status, path = entry
            old_path = None
        else:
            status, old_path, path = entry  # R/C have old and new paths
        
        # Check primary path (new path or modified path)
        allowed, reason = policy.validate_operation(status, path, mode)
        if not allowed:
            blocked.append((path, status, reason))
            
        # For R/C, also check the old path (treat as deletion/touch)
        if old_path:
            # Use status D to imply "removal/modification of this path"
            allowed_old, reason_old = policy.validate_operation("D", old_path, mode)
            if not allowed_old:
                blocked.append((old_path, status, reason_old))
    
    return blocked

# ============================================================================
# EVIDENCE GENERATION
# ============================================================================
def generate_evidence_bundle(status: str, reason: Optional[str], mode: str, task: Dict[str, Any], 
                            parsed_diff: List[tuple] = None, blocked_entries: List[tuple] = None):
    """Generate the deterministic evidence bundle for the mission."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mission_id = f"mission_{timestamp}"
    evidence_path = os.path.join(policy.EVIDENCE_ROOT, mission_id)
    os.makedirs(evidence_path, exist_ok=True)
    
    # exit_report.json
    report = {
        "status": status,
        "reason_code": reason,
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "blocked_entries": blocked_entries or []
    }
    with open(os.path.join(evidence_path, "exit_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    
    # changed_files.json (sorted by path for determinism)
    changed = []
    if parsed_diff:
        for entry in parsed_diff:
            if len(entry) == 2:
                changed.append({"status": entry[0], "path": entry[1]})
            else:
                changed.append({"status": entry[0], "old_path": entry[1], "new_path": entry[2]})
    # Sort by path (or new_path for renames/copies) for deterministic output
    changed.sort(key=lambda x: policy.normalize_path(x.get("path") or x.get("new_path", "")))
    
    with open(os.path.join(evidence_path, "changed_files.json"), "w") as f:
        json.dump(changed, f, indent=2)
    
    # classification.json
    classification = {
        "is_governance": any(policy.matches_denylist(path)[0] for path in task.get("files", [])),
        "risk_level": "P0" if any(policy.matches_denylist(path)[0] for path in task.get("files", [])) else "P1",
        "envelope_violations": len(blocked_entries) if blocked_entries else 0
    }
    with open(os.path.join(evidence_path, "classification.json"), "w") as f:
        json.dump(classification, f, indent=2)
    
    # runner.log
    log_content = get_log_buffer()
    truncated_log, _ = policy.truncate_log(log_content)
    with open(os.path.join(evidence_path, "runner.log"), "w") as f:
        f.write(truncated_log)
    
    # hashes.json
    hashes = {}
    for filename in ["exit_report.json", "changed_files.json", "classification.json", "runner.log"]:
        p = os.path.join(evidence_path, filename)
        if os.path.exists(p):
            hashes[filename] = policy.compute_file_hash(p)
            
    with open(os.path.join(evidence_path, "hashes.json"), "w") as f:
        json.dump(hashes, f, indent=2)
        
    log(f"Evidence bundle generated: {evidence_path}", "ok")
    return evidence_path

# ============================================================================
# INPUT VALIDATION
# ============================================================================
def validate_task_input(task_str):
    """Validate task is JSON with required schema. Reject free-text."""
    try:
        task = json.loads(task_str)
    except json.JSONDecodeError:
        log("Free-text input rejected. Phase 3 requires JSON-structured tasks.", "error")
        return None
    
    required = ["files", "action", "instruction"]
    for key in required:
        if key not in task:
            log(f"Missing required key in task JSON: {key}", "error")
            return None
    
    # Phase 3: All operations allowed.
    valid_actions = ["create", "modify", "delete", "rename", "move", "copy"]
    if task["action"] not in valid_actions:
        log(f"Invalid action: {task['action']}. Valid actions: {valid_actions}", "error")
        return None
    
    return task

# ============================================================================
# EPHEMERAL SERVER LIFECYCLE
# ============================================================================
import tempfile
import shutil
import threading

def create_isolated_config(api_key, model):
    temp_dir = tempfile.mkdtemp(prefix="opencode_steward_")
    config_subdir = os.path.join(temp_dir, "opencode")
    os.makedirs(config_subdir, exist_ok=True)
    data_subdir = os.path.join(temp_dir, ".local", "share", "opencode")
    os.makedirs(data_subdir, exist_ok=True)
    
    # Determine provider based on model naming or defaults
    if "minimax" in model.lower():
        provider = "zen" # Zen endpoint often maps to 'zen' or 'anthropic' internal logic in server
        # For our environment, we'll provide keys for both to be safe
        auth_data = {
            "zen": {"type": "api", "key": api_key},
            "openrouter": {"type": "api", "key": api_key}
        }
    else:
        auth_data = {"openrouter": {"type": "api", "key": api_key}}

    with open(os.path.join(data_subdir, "auth.json"), "w") as f:
        json.dump(auth_data, f, indent=2)
    
    config_data = {
        "model": model, 
        "$schema": "https://opencode.ai/config.json"
    }
    
    # If using Zen, we might need to specify the base URL in config too
    # Using the standard Zen endpoint from models.yaml
    if "minimax" in model.lower():
        config_data["upstream_base_url"] = "https://opencode.ai/zen/v1/messages"

    with open(os.path.join(config_subdir, "opencode.json"), "w") as f:
        json.dump(config_data, f, indent=2)
    
    return temp_dir

# LIFEOS_TODO[P1][area: scripts/opencode_ci_runner.py:cleanup_isolated_config][exit: root cause documented + decision logged in DECISIONS.md] Review OpenCode deletion logic: Understand why cleanup uses shutil.rmtree for temp configs. DoD: Root cause documented, safety analysis complete
def cleanup_isolated_config(config_dir):
    if config_dir and os.path.exists(config_dir):
        try:
            shutil.rmtree(config_dir)
        except Exception as e:
            log(f"Failed to cleanup config dir {config_dir}: {e}", "warning")

def start_ephemeral_server(port, config_dir, api_key):
    log(f"Starting ephemeral OpenCode server on port {port}", "info")
    env = os.environ.copy()
    env["APPDATA"], env["XDG_CONFIG_HOME"], env["USERPROFILE"], env["HOME"] = config_dir, config_dir, config_dir, config_dir
    env["OPENROUTER_API_KEY"] = api_key
    env["OPENAI_API_KEY"], env["ANTHROPIC_API_KEY"] = "", ""
    
    try:
        return subprocess.Popen(
            ["opencode", "serve", "--port", str(port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
            shell=True if os.name == "nt" else False
        )
    except Exception as e:
        log(f"Failed to start ephemeral server: {e}", "error")
        return None

def stop_ephemeral_server(process):
    if process:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()


class MissionTimeout(TimeoutError):
    """Raised when a mission helper exceeds the configured timeout."""


def run_with_timeout(func, timeout_seconds: int):
    """
    Run a callable with a hard timeout and propagate exceptions.
    Returns the callable result on success.
    """
    result: Dict[str, Any] = {}
    err: Dict[str, BaseException] = {}

    def _runner():
        try:
            result["value"] = func()
        except BaseException as exc:  # pragma: no cover - propagation path
            err["exc"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise MissionTimeout(f"Mission step exceeded timeout: {timeout_seconds}s")
    if "exc" in err:
        raise err["exc"]
    return result.get("value")

# ============================================================================
# OPENCODE SERVER INTERFACE
# ============================================================================
def wait_for_server(base_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(f"{base_url}/global/health", timeout=1).status_code == 200:
                return True
        except Exception:
            pass  # Expected during server startup
        time.sleep(1)
    return False

def run_mission(base_url, model, instruction):
    try:
        resp = requests.post(f"{base_url}/session", json={"title": "Steward Mission", "model": model}, timeout=10)
        if resp.status_code != 200: return False
        session_id = resp.json()["id"]
        requests.post(f"{base_url}/session/{session_id}/message",
                      json={"parts": [{"type": "text", "text": instruction}]}, timeout=120)
        return session_id
    except Exception as e:
        log(f"Failed to run mission: {e}", "error")
        return False

# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="OpenCode CI Runner (CT-2 Phase 3 v2.0) - Broadened")
    parser.add_argument("--port", type=int, default=62586)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--mode", type=str, choices=policy.VALID_MODES, default=policy.MODE_STEWARD, help="Enforcement mode (steward/builder)")
    parser.add_argument("--task", type=str, required=True, help="JSON-structured task (required)")
    # NO --override-foundations flag. Period.
    args = parser.parse_args()
    
    repo_root = os.getcwd()
    # Load config once
    model_config = load_model_config()

    # Resolve model if auto
    model_id = args.model
    if model_id == "auto":
        role = "steward" if args.mode == policy.MODE_STEWARD else "builder"
        model_id, reason, _ = resolve_model_auto(role, model_config)
        log(f"Resolved model 'auto' to '{model_id}' ({reason})", "info")
    else:
        log(f"Using requested model '{model_id}'", "info")

    api_key = load_api_key(args.mode)
    if not api_key:
        log("No API key available. Requesting user intervention.", "error")
        # Fail loud in Phase 3
        sys.exit(1)
    
    task = validate_task_input(args.task)
    if not task: 
        sys.exit(1)
    
    # ========== PRE-START CHECKS (symlink on declared files) ==========
    for path in task["files"]:
        safe, reason = policy.check_symlink(path, repo_root)
        if not safe:
            generate_evidence_bundle("BLOCK", reason, "PRE_START", task)
            log(f"Symlink rejected: {path}", "error")
            sys.exit(1)
    
    # ========== SERVER SETUP ==========
    config_dir = create_isolated_config(api_key, model_id)
    server_process = start_ephemeral_server(args.port, config_dir, api_key)
    if not server_process:
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    if not wait_for_server(f"http://127.0.0.1:{args.port}"):
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        log("Server timeout", "error")
        sys.exit(1)
    
    # ========== EXECUTE MISSION ==========
    log("Executing mission", "info")
    session_id = run_mission(f"http://127.0.0.1:{args.port}", model_id, task["instruction"])
    
    # ========== POST-EXECUTION: GET DIFF AND VALIDATE ENVELOPE ==========
    log("Validating post-execution diff against envelope", "info")
    parsed, mode, error = policy.execute_diff_and_parse(repo_root)
    
    if error:
        generate_evidence_bundle("BLOCK", error, mode, task)
        log(f"Diff acquisition failed: {error}", "error")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    if not parsed:
        parsed = []
    
    # Validate ALL diff entries against envelope
    blocked_entries = validate_all_diff_entries(parsed, mode=args.mode)
    
    if blocked_entries:
        first_block = blocked_entries[0]
        generate_evidence_bundle("BLOCK", first_block[2], mode, task, parsed, blocked_entries)
        log(f"Envelope violation: {first_block[0]} ({first_block[1]}) - {first_block[2]}", "error")
        for entry in blocked_entries[1:5]:  # Log up to 5
            log(f"  Additional violation: {entry[0]} ({entry[1]}) - {entry[2]}", "error")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    # Check symlinks again for new files
    for entry in parsed:
        path = entry[1] if len(entry) == 2 else entry[2]
        safe, reason = policy.check_symlink(path, repo_root)
        if not safe:
            generate_evidence_bundle("BLOCK", reason, mode, task, parsed)
            log(f"New symlink detected: {path}", "error")
            subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
            stop_ephemeral_server(server_process)
            cleanup_isolated_config(config_dir)
            sys.exit(1)

    # Success
    generate_evidence_bundle("PASS", None, mode, task, parsed)
    log("MISSION SUCCESS - All changes within envelope", "ok")
    
    # Cleanup
    stop_ephemeral_server(server_process)
    cleanup_isolated_config(config_dir)

if __name__ == "__main__":
    main()
