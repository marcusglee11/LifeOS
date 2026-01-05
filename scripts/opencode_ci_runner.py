#!/usr/bin/env python3
"""
OpenCode CI Runner
==================

This script acts as the "controller" for OpenCode running in a CI environment (headless).
It connects to a running OpenCode server, starts a session, issues a prompt to
make a commit, and verifies the outcome.

Usage:
    python opencode_ci_runner.py [--port 4096] [--model google/gemini-2.0-flash-001]
"""

import argparse
import time
import requests
import subprocess
import sys
import os
import json

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level="info"):
    prefix = {"info": "→", "ok": "✓", "error": "✗"}
    color = {"info": Colors.BLUE, "ok": Colors.GREEN, "error": Colors.RED}
    print(f"{color.get(level, '')}{prefix.get(level, '')} {msg}{Colors.RESET}")

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

def run_ci_mission(base_url, model):
    log("Starting CI mission...", "info")
    
    # 1. Create Session
    try:
        resp = requests.post(
            f"{base_url}/session",
            json={"title": "CI Integration Test", "model": model},
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
        
    # 2. Send Prompt
    prompt_text = (
        "You are running in a CI environment. "
        "Perform the following task exactly:\n"
        "1. Create a file named 'ci_proof.txt' containing the text 'Verified'.\n"
        "2. Configure git user.email to 'robot@lifeos.local' and user.name to 'OpenCode Robot' if not set.\n"
        "3. Git add the file.\n"
        "4. Git commit with message 'CI: OpenCode verification commit'.\n"
        "Do not ask for permission, just execute. Return 'MISSION_COMPLETE' when done."
    )
    
    log(f"Sending prompt...", "info")
    try:
        resp = requests.post(
            f"{base_url}/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": prompt_text}]},
            headers={"Content-Type": "application/json"},
            timeout=120 # Give it time to work
        )
        
        if resp.status_code != 200:
            log(f"Prompt failed: {resp.text}", "error")
            return False
            
        # Parse response to see if it agreed
        result = resp.json()
        log("Agent responded.", "ok")
        
    except Exception as e:
        log(f"Prompt execution error: {e}", "error")
        return False
        
    return session_id

def verify_outcome():
    log("Verifying outcome...", "info")
    
    # Check file
    if os.path.exists("ci_proof.txt"):
        with open("ci_proof.txt", "r") as f:
            content = f.read().strip()
        if "Verified" in content:
            log("File 'ci_proof.txt' created correctly", "ok")
        else:
            log(f"File content mismatch: {content}", "error")
            return False
    else:
        log("File 'ci_proof.txt' NOT found", "error")
        return False
        
    # Check commit
    try:
        log_proc = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"], 
            capture_output=True, text=True
        )
        last_commit_msg = log_proc.stdout.strip()
        if "CI: OpenCode verification commit" in last_commit_msg:
            log("Git commit verified", "ok")
        else:
            log(f"Git commit mismatch. Last commit: {last_commit_msg}", "error")
            return False
    except Exception as e:
        log(f"Git verification failed: {e}", "error")
        return False
        
    return True

def cleanup(base_url, session_id):
    if session_id:
        requests.delete(f"{base_url}/session/{session_id}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4096)
    parser.add_argument("--model", type=str, default="google/gemini-2.0-flash-001")
    args = parser.parse_args()
    
    base_url = f"http://127.0.0.1:{args.port}"
    
    if not wait_for_server(base_url):
        sys.exit(1)
        
    session_id = run_ci_mission(base_url, args.model)
    if not session_id:
        sys.exit(1)
        
    # Give fs slightly a moment to settle if needed, though requests blocks
    time.sleep(1)
    
    success = verify_outcome()
    
    cleanup(base_url, session_id)
    
    if success:
        log("CI INTEGRATION TEST PASSED", "ok")
        sys.exit(0)
    else:
        log("CI INTEGRATION TEST FAILED", "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
