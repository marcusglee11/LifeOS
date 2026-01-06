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
import fnmatch
from datetime import datetime

# ============================================================================
# CONFIGURATION (mirrored from CCP denylist_surfaces)
# ============================================================================
ALLOWED_ROOTS = ["docs/", "artifacts/review_packets/"]
DENYLIST_PATTERNS = [
    {"pattern": "docs/00_foundations/**", "action": "modify", "requires_override": True},
    {"pattern": "config/**", "action": "any", "requires_override": False},
    {"pattern": "scripts/**", "action": "modify", "requires_override": False},
    {"pattern": "**/*.py", "action": "modify", "requires_override": False},
    {"pattern": "GEMINI.md", "action": "modify", "requires_override": False},
]
EVIDENCE_DIR = "artifacts/evidence/"  # READ-ONLY for steward
REVIEW_PACKETS_DIR = "artifacts/review_packets/"

# Review Packet schema requirements
REQUIRED_PACKET_SECTIONS = [
    r"##\s*(Summary|Executive Summary)",
    r"##\s*(Changes|Evidence)",
    r"##\s*Appendix",
]
REQUIRED_PACKET_METADATA = ["packet_id", "packet_type", "version", "mission_name", "author", "status", "date"]

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
    prefix = {"info": "->", "ok": "[OK]", "error": "[ERROR]", "warn": "[WARN]", "gov": "[GOVERNANCE-ALERT]"}
    color = {"info": Colors.BLUE, "ok": Colors.GREEN, "error": Colors.RED, "warn": Colors.YELLOW, "gov": Colors.YELLOW}
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        print(f"{color.get(level, '')}{prefix.get(level, '')} [{timestamp}] {msg}{Colors.RESET}", flush=True)
    except UnicodeEncodeError:
        print(f"{prefix.get(level, '')} [{timestamp}] {msg}", flush=True)

# ============================================================================
# INPUT VALIDATION (P0.1 - JSON-Only)
# ============================================================================
def validate_task_input(task_str):
    """Validate task is JSON with required schema. Reject free-text."""
    try:
        task = json.loads(task_str)
    except json.JSONDecodeError:
        log("Free-text input rejected. Phase 2 requires JSON-structured tasks.", "error")
        log('Expected format: {"files":["path1"],"action":"create|modify|delete|archive","instruction":"..."}', "error")
        return None
    
    # Validate required keys
    required = ["files", "action", "instruction"]
    for key in required:
        if key not in task:
            log(f"Missing required key in task JSON: {key}", "error")
            return None
    
    # Validate action
    valid_actions = ["create", "modify", "delete"]
    if task["action"] not in valid_actions:
        log(f"Invalid action: {task['action']}. Must be one of {valid_actions}", "error")
        return None
    
    # Validate files is list
    if not isinstance(task["files"], list):
        log("'files' must be a list of paths.", "error")
        return None
    
    return task

# ============================================================================
# PATH SAFETY (P0.4 - Symlink Defense + Canonicalization)
# ============================================================================
def check_path_safety(path, repo_root):
    """Check path is safe: no symlinks, no traversal, within allowed roots."""
    # Reject absolute paths
    if os.path.isabs(path):
        log(f"Absolute path rejected: {path}", "error")
        return False
    
    # Reject traversal
    if ".." in path:
        log(f"Path traversal rejected: {path}", "error")
        return False
    
    # Normalize path
    norm_path = os.path.normpath(path).replace("\\", "/")
    full_path = os.path.join(repo_root, norm_path)
    
    # Filesystem-level symlink check (each component)
    parts = norm_path.split("/")
    check_path = repo_root
    for part in parts[:-1]:  # All parent components
        check_path = os.path.join(check_path, part)
        if os.path.islink(check_path):
            log(f"Symlink in path component rejected: {check_path}", "error")
            return False
    
    # Realpath containment
    try:
        real = os.path.realpath(full_path)
        real_repo = os.path.realpath(repo_root)
        if not real.startswith(real_repo):
            log(f"Realpath escapes repo: {real}", "error")
            return False
    except Exception as e:
        log(f"Realpath check failed: {e}", "error")
        return False
    
    # Check within allowed roots
    in_allowed = False
    for root in ALLOWED_ROOTS:
        if norm_path.startswith(root) or norm_path == root.rstrip("/"):
            in_allowed = True
            break
    
    if not in_allowed:
        log(f"Path outside allowed roots: {norm_path}", "error")
        return False
    
    return True

def check_git_index_symlink(path):
    """Check git index for symlink mode (120000)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", path],
            capture_output=True, text=True
        )
        if result.stdout:
            mode = result.stdout.split()[0]
            if mode == "120000":
                log(f"Git index symlink rejected (mode 120000): {path}", "error")
                return False
    except Exception:
        pass
    return True

# ============================================================================
# DENYLIST ENFORCEMENT (P0.3)
# ============================================================================
def check_denylist(path, action, override_foundations=False):
    """Check path against denylist patterns."""
    norm_path = path.replace("\\", "/")
    
    for rule in DENYLIST_PATTERNS:
        pattern = rule["pattern"]
        rule_action = rule["action"]
        requires_override = rule.get("requires_override", False)
        
        # Match pattern
        if fnmatch.fnmatch(norm_path, pattern):
            # Check action match
            if rule_action == "any" or rule_action == action:
                if requires_override:
                    if override_foundations:
                        log(f"override-foundations triggered at {datetime.now().isoformat()}", "gov")
                        return True  # Allowed with override
                    else:
                        log(f"Denylist match: {norm_path} ({pattern}) - requires --override-foundations", "error")
                        return False
                else:
                    log(f"Denylist match: {norm_path} ({pattern}) - unconditionally denied", "error")
                    return False
    
    return True

def check_evidence_readonly(path):
    """Ensure artifacts/evidence/** is read-only."""
    norm_path = path.replace("\\", "/")
    if norm_path.startswith(EVIDENCE_DIR):
        log(f"Evidence directory is READ-ONLY: {path}", "error")
        return False
    return True

# ============================================================================
# REVIEW PACKET VALIDATION (P0.2, P1.1)
# ============================================================================
def check_packet_required(task, override_foundations=False):
    """Determine if Review Packet is required."""
    # Any delete
    if task["action"] == "delete":
        return True
    # Any modify (conservative Phase 2 policy)
    if task["action"] in ["modify", "archive"]:
        return True
    # Override used
    if override_foundations:
        return True
    # >1 file (superseded by "any modify" but kept for clarity)
    if len(task["files"]) > 1:
        return True
    return False

def validate_review_packet(packet_path):
    """Validate Review Packet schema."""
    if not os.path.exists(packet_path):
        log(f"Review Packet not found: {packet_path}", "error")
        return False
    
    with open(packet_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for ellipses
    if "..." in content or "[truncated]" in content:
        log(f"Review Packet contains ellipses/truncation: {packet_path}", "error")
        return False
    
    # Check required sections
    for pattern in REQUIRED_PACKET_SECTIONS:
        if not re.search(pattern, content, re.IGNORECASE):
            log(f"Review Packet missing required section ({pattern}): {packet_path}", "error")
            return False
    
    # Check YAML frontmatter
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx > 0:
            frontmatter = content[3:end_idx]
            for field in REQUIRED_PACKET_METADATA:
                if field + ":" not in frontmatter:
                    log(f"Review Packet missing metadata field '{field}': {packet_path}", "error")
                    return False
    else:
        log(f"Review Packet missing YAML frontmatter: {packet_path}", "error")
        return False
    
    return True

def check_staged_packet():
    """Check if a Review Packet is staged and is Added-only."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        capture_output=True, text=True
    )
    
    packet_found = False
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[1]
        
        if path.startswith("artifacts/review_packets/Review_Packet_") and path.endswith(".md"):
            if status == "A":
                packet_found = True
                if not validate_review_packet(path):
                    return False
            else:
                log(f"Review Packet must be Added-only (status={status}): {path}", "error")
                return False
    
    return packet_found

# ============================================================================
# OPENCODE SERVER INTERFACE
# ============================================================================
def wait_for_server(base_url, timeout=30):
    log(f"Waiting for OpenCode server at {base_url}...", "info")
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{base_url}/global/health", timeout=1)
            if resp.status_code == 200:
                log("Server ready", "ok")
                return True
        except:
            pass
        time.sleep(1)
    
    log("Server timeout", "error")
    return False

def run_mission(base_url, model, instruction):
    """Send instruction to OpenCode server."""
    log("Starting mission...", "info")
    
    try:
        resp = requests.post(
            f"{base_url}/session",
            json={"title": "Steward Mission", "model": model},
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code != 200:
            log(f"Failed to create session: {resp.text}", "error")
            return False
        
        session_id = resp.json()["id"]
        log(f"Session created: {session_id}", "ok")
        
    except Exception as e:
        log(f"Session creation error: {e}", "error")
        return False
    
    log("Sending instruction...", "info")
    try:
        resp = requests.post(
            f"{base_url}/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": instruction}]},
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        if resp.status_code != 200:
            log(f"Instruction failed: {resp.text}", "error")
            return False
        
        log("Agent responded.", "ok")
        
    except Exception as e:
        log(f"Instruction execution error: {e}", "error")
        return False
    
    return session_id

def cleanup(base_url, session_id):
    if session_id:
        requests.delete(f"{base_url}/session/{session_id}")

# ============================================================================
# MAIN
# ============================================================================
# ============================================================================
# ARCHIVE ENFORCEMENT (P1.1)
# ============================================================================
def validate_archive_outcome(task_files):
    """Ensure 'archive' action moved files to docs/99_archive/."""
    # Check git status for moves
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    
    # Expected: Original files Deleted (or Renamed from), New files in docs/99_archive/
    # Simplified check: verify the target files are gone from original location
    # and equivalent files exist in docs/99_archive/
    
    success = True
    for original_path in task_files:
        if os.path.exists(original_path):
            log(f"Archive failed: Original file still exists: {original_path}", "error")
            success = False
            continue
        
        filename = os.path.basename(original_path)
        # Check recursively in 99_archive? Or just immediate?
        # Standard: docs/99_archive/<filename> or docs/99_archive/<rel_path>
        # Let's check generally if it ended up in 99_archive
        archive_root = "docs/99_archive"
        
        # We need to find where it went. 
        # Git Detects Renames.
        # "R  docs/foo.md -> docs/99_archive/foo.md"
        
        found_in_archive = False
        for line in result.stdout.splitlines():
            if "->" in line:
                # Rename detected
                parts = line.split("->")
                src = parts[0].strip().split()[-1] # Handle status flags
                dst = parts[1].strip()
                if src == original_path and dst.startswith(archive_root):
                    found_in_archive = True
                    break
        
        if not found_in_archive:
            # Maybe not a git rename, but a Move?
            # Check if file exists in archive root
            expected_dest = os.path.join(archive_root, filename)
            if os.path.exists(expected_dest):
                found_in_archive = True
            
        if not found_in_archive:
             log(f"Archive failed: File {original_path} not found in {archive_root}", "error")
             success = False

    return success

def rollback():
    """Fail-closed rollback."""
    log("Rolling back changes...", "warn")
    subprocess.run(["git", "reset", "--hard", "HEAD"], check=False)
    subprocess.run(["git", "clean", "-fd"], check=False)

# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="OpenCode CI Runner (Hardened - CT-2 Phase 2)")
    parser.add_argument("--port", type=int, default=62585)
    parser.add_argument("--model", type=str, default="google/gemini-2.0-flash-001")
    parser.add_argument("--task", type=str, required=True, help="JSON-structured task (required)")
    parser.add_argument("--override-foundations", action="store_true", help="Allow access to docs/00_foundations/** (requires confirmation)")
    args = parser.parse_args()
    
    repo_root = os.getcwd()
    base_url = f"http://127.0.0.1:{args.port}"
    
    # ========== INPUT VALIDATION ==========
    task = validate_task_input(args.task)
    if not task:
        sys.exit(1)
    
    # ========== FOUNDATIONS OVERRIDE CONFIRMATION ==========
    if args.override_foundations:
        confirm = input("GOVERNANCE OVERRIDE: Type 'CONFIRM_OVERRIDE' to proceed: ")
        if confirm != "CONFIRM_OVERRIDE":
            log("Override confirmation failed.", "error")
            sys.exit(1)
        log("Foundations override confirmed.", "gov")
    
    # ========== PATH SAFETY & DENYLIST CHECKS ==========
    for path in task["files"]:
        if not check_path_safety(path, repo_root):
            sys.exit(1)
        if not check_git_index_symlink(path):
            sys.exit(1)
        if not check_denylist(path, task["action"], args.override_foundations):
            sys.exit(1)
        if not check_evidence_readonly(path):
            sys.exit(1)
    
    # ========== SERVER CONNECTION ==========
    if not wait_for_server(base_url):
        sys.exit(1)
    
    # ========== EXECUTE MISSION ==========
    session_id = run_mission(base_url, args.model, task["instruction"])
    if not session_id:
        sys.exit(1)
    
    time.sleep(1)  # Allow fs to settle
    
    # ========== REVIEW PACKET GATE ==========
    if check_packet_required(task, args.override_foundations):
        log("Review Packet required. Checking staged files...", "info")
        if not check_staged_packet():
            log("Review Packet gate FAILED. Mission aborted.", "error")
            rollback() # Fail-Closed
            cleanup(base_url, session_id)
            sys.exit(1)
        log("Review Packet validated.", "ok")
    
    cleanup(base_url, session_id)
    log("MISSION SUCCESS", "ok")
    sys.exit(0)

if __name__ == "__main__":
    main()
