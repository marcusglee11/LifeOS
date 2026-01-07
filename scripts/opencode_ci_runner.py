#!/usr/bin/env python3
"""
OpenCode CI Runner (Hardened - CT-2 Phase 2)
=============================================

This script enforces governance boundaries for OpenCode steward operations.
It validates JSON-structured tasks, enforces path safety, denylist rules,
and Review Packet requirements per Plan_OpenCode_Steward_Hardening_v1.3.

Usage:
    python opencode_ci_runner.py --port 62585 --task '{"files":["docs/example.md"],"action":"modify","instruction":"..."}'
    python opencode_ci_runner.py --port 62585 --task '...' --override-foundations  # For docs/00_foundations/** access
"""

import argparse
import time
import requests
import subprocess
import sys
import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import hardened policy module
import opencode_gate_policy as policy
from opencode_gate_policy import ReasonCode

# ============================================================================
# LOGGING
# ============================================================================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def log(msg, level="info"):
    timestamp = datetime.now().isoformat(sep="T", timespec="seconds")
    color = Colors.RESET
    if level == "error": color = Colors.RED
    elif level == "ok": color = Colors.GREEN
    elif level == "gov": color = Colors.YELLOW
    elif level == "info": color = Colors.BLUE
    print(f"{color}[{level.upper()}] [{timestamp}] {msg}{Colors.RESET}")

def load_steward_key():
    """Load the steward API key from env or .env file."""
    key = os.environ.get("STEWARD_OPENROUTER_KEY")
    if not key:
        try:
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("STEWARD_OPENROUTER_KEY="):
                        key = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    
    if key:
        log(f"Steward API Key loaded (starts with {key[:8]}...)", "info")
    else:
        log("Steward API Key NOT found", "warn")
    return key

# ============================================================================
# EVIDENCE GENERATION
# ============================================================================
def generate_evidence_bundle(status: str, reason: Optional[str], mode: str, task: Dict[str, Any], parsed_diff: List[tuple] = None):
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
        "task": task
    }
    with open(os.path.join(evidence_path, "exit_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    
    # changed_files.json
    changed = []
    if parsed_diff:
        for entry in parsed_diff:
            if len(entry) == 2:
                changed.append({"status": entry[0], "path": entry[1]})
            else:
                changed.append({"status": entry[0], "old_path": entry[1], "new_path": entry[2]})
    
    with open(os.path.join(evidence_path, "changed_files.json"), "w") as f:
        json.dump(changed, f, indent=2)
    
    # classification.json (Mock for now)
    classification = {
        "is_governance": any(policy.matches_denylist(path)[0] for path in task.get("files", [])),
        "risk_level": "P0" if any(policy.matches_denylist(path)[0] for path in task.get("files", [])) else "P1"
    }
    with open(os.path.join(evidence_path, "classification.json"), "w") as f:
        json.dump(classification, f, indent=2)
    
    # hashes.json
    hashes = {}
    for filename in ["exit_report.json", "changed_files.json", "classification.json"]:
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
        log("Free-text input rejected. Phase 2 requires JSON-structured tasks.", "error")
        return None
    
    required = ["files", "action", "instruction"]
    for key in required:
        if key not in task:
            log(f"Missing required key in task JSON: {key}", "error")
            return None
    
    valid_actions = ["create", "modify", "delete"]
    if task["action"] not in valid_actions:
        log(f"Invalid action: {task['action']}", "error")
        return None
    
    return task

# ============================================================================
# EPHEMERAL SERVER LIFECYCLE
# ============================================================================
import tempfile
import shutil

def create_isolated_config(api_key, model):
    temp_dir = tempfile.mkdtemp(prefix="opencode_steward_")
    config_subdir = os.path.join(temp_dir, "opencode")
    os.makedirs(config_subdir, exist_ok=True)
    data_subdir = os.path.join(temp_dir, ".local", "share", "opencode")
    os.makedirs(data_subdir, exist_ok=True)
    
    auth_data = {"openrouter": {"type": "api", "key": api_key}}
    with open(os.path.join(data_subdir, "auth.json"), "w") as f:
        json.dump(auth_data, f, indent=2)
    
    model_id = model.replace("openrouter/", "") if model.startswith("openrouter/") else model
    config_data = {"model": f"openrouter/{model_id}", "$schema": "https://opencode.ai/config.json"}
    with open(os.path.join(config_subdir, "opencode.json"), "w") as f:
        json.dump(config_data, f, indent=2)
    
    return temp_dir

def cleanup_isolated_config(config_dir):
    if config_dir and os.path.exists(config_dir):
        try: shutil.rmtree(config_dir)
        except: pass

def start_ephemeral_server(port, config_dir, api_key):
    log(f"Starting ephemeral OpenCode server on port {port}...", "info")
    env = os.environ.copy()
    env["APPDATA"], env["XDG_CONFIG_HOME"], env["USERPROFILE"], env["HOME"] = config_dir, config_dir, config_dir, config_dir
    env["OPENROUTER_API_KEY"] = api_key
    env["OPENAI_API_KEY"], env["ANTHROPIC_API_KEY"] = "", ""
    
    try:
        return subprocess.Popen(
            ["opencode", "serve", "--port", str(port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True if os.name == "nt" else False
        )
    except Exception as e:
        log(f"Failed to start ephemeral server: {e}", "error")
        return None

def stop_ephemeral_server(process):
    if process:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()

# ============================================================================
# OPENCODE SERVER INTERFACE
# ============================================================================
def wait_for_server(base_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(f"{base_url}/global/health", timeout=1).status_code == 200:
                return True
        except: pass
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
    except: return False

# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=62586)
    parser.add_argument("--model", type=str, default="openrouter/x-ai/grok-4.1-fast")
    parser.add_argument("--task", type=str, required=True)
    parser.add_argument("--override-foundations", action="store_true")
    args = parser.parse_args()
    
    repo_root = os.getcwd()
    steward_api_key = load_steward_key()
    
    task = validate_task_input(args.task)
    if not task: sys.exit(1)
    
    # ========== PRE-START CHECKS ==========
    for path in task["files"]:
        # Symlink check
        is_sym, reason = policy.check_symlink(path, repo_root)
        if is_sym:
            generate_evidence_bundle("BLOCK", reason, "PRE_START", task)
            log(f"Symlink rejected: {path}", "error")
            sys.exit(1)
            
        # Denylist check
        denied, reason = policy.matches_denylist(path)
        if denied:
            if reason == ReasonCode.DENYLIST_ROOT_BLOCKED and "00_foundations" in path and args.override_foundations:
                log("Foundations override used.", "gov")
            else:
                generate_evidence_bundle("BLOCK", reason, "PRE_START", task)
                log(f"Denylist match: {path}", "error")
                sys.exit(1)
                
    # ========== SERVER SETUP ==========
    config_dir = create_isolated_config(steward_api_key, args.model)
    server_process = start_ephemeral_server(args.port, config_dir, steward_api_key)
    if not server_process:
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    if not wait_for_server(f"http://127.0.0.1:{args.port}"):
        stop_ephemeral_server(server_process)
        cleanup_isolated_config(config_dir)
        sys.exit(1)
    
    # ========== EXECUTE MISSION ==========
    session_id = run_mission(f"http://127.0.0.1:{args.port}", args.model, task["instruction"])
    
    # ========== POST-EXECUTION VALIDATION (Diff) ==========
    parsed, mode, error = policy.execute_diff_and_parse(repo_root)
    if error:
        generate_evidence_bundle("BLOCK", error, mode, task)
        log(f"Diff failed: {error}", "error")
        # Rollback
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        sys.exit(1)
        
    blocked = policy.detect_blocked_ops(parsed)
    if blocked:
        generate_evidence_bundle("BLOCK", blocked[0][2], mode, task, parsed)
        log(f"Blocked operation detected: {blocked[0][1]}", "error")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
        sys.exit(1)
        
    # Check symlinks again for new files
    for entry in parsed:
        path = entry[1]
        is_sym, reason = policy.check_symlink(path, repo_root)
        if is_sym:
            generate_evidence_bundle("BLOCK", reason, mode, task, parsed)
            log(f"New symlink detected: {path}", "error")
            subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
            sys.exit(1)

    # Success
    generate_evidence_bundle("PASS", None, mode, task, parsed)
    log("MISSION SUCCESS", "ok")
    
    # Cleanup
    stop_ephemeral_server(server_process)
    cleanup_isolated_config(config_dir)

if __name__ == "__main__":
    main()
