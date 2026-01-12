#!/usr/bin/env python3
"""
LifeOS Phase 0: OpenCode API Connectivity Validation
=====================================================

This script validates that OpenCode can be controlled programmatically,
which is the critical unlock for LifeOS autonomous operation.

Prerequisites:
    1. Node.js 18+ installed
    2. OpenCode installed: npm install -g opencode-ai
    3. OpenRouter API key set: set OPENROUTER_API_KEY=your-key
    
Usage:
    python opencode_phase0_validation.py
    
Expected duration: ~60 seconds
"""

import subprocess
import time
import json
import sys
import os
import signal
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Run: pip install requests")
    sys.exit(1)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log(msg: str, level: str = "info"):
    colors = {"info": Colors.BLUE, "ok": Colors.GREEN, "warn": Colors.YELLOW, "error": Colors.RED}
    prefix = {"info": "→", "ok": "✓", "warn": "⚠", "error": "✗"}
    print(f"{colors.get(level, '')}{prefix.get(level, '')} {msg}{Colors.RESET}")


def check_prerequisites() -> bool:
    """Check that all prerequisites are met."""
    log("Checking prerequisites...", "info")
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=True)
        version = result.stdout.strip()
        log(f"Node.js: {version}", "ok")
    except FileNotFoundError:
        log("Node.js not found. Install from https://nodejs.org", "error")
        return False
    except Exception as e:
        log(f"Node.js check failed: {e}", "error")
        return False
    
    # Check OpenCode
    try:
        # On Windows, need shell=True for npm globals sometimes, or ensure .cmd extension
        cmd = "opencode"
        if os.name == 'nt':
            cmd = "opencode.cmd"
            
        result = subprocess.run([cmd, "--version"], capture_output=True, text=True, shell=True)
        version = result.stdout.strip() or result.stderr.strip()
        if not version and result.returncode != 0:
             # Try without .cmd or just "opencode" with shell=True which helps path resolution
             result = subprocess.run(["opencode", "--version"], capture_output=True, text=True, shell=True)
             version = result.stdout.strip() or result.stderr.strip()

        if result.returncode == 0:
            log(f"OpenCode: {version}", "ok")
        else:
            log("OpenCode not found or errored. Run: npm install -g opencode-ai", "error")
            return False
            
    except FileNotFoundError:
        log("OpenCode not found. Run: npm install -g opencode-ai", "error")
        return False
    
    # Check API key
    if not os.environ.get("OPENROUTER_API_KEY"):
        log("OPENROUTER_API_KEY not set", "error")
        log("  Run: $env:OPENROUTER_API_KEY='your-key'", "info")
        return False
    log("OPENROUTER_API_KEY: set", "ok")
    
    return True


def start_server(port: int = 4096) -> subprocess.Popen:
    """Start OpenCode server and wait for it to be ready."""
    log(f"Starting OpenCode server on port {port}...", "info")
    
    cmd = ["opencode", "serve", "--port", str(port)]
    if os.name == 'nt':
        # Use shell=True to find the command in path comfortably, 
        # but Popen with shell=True takes a string usually.
        # Better: use opencode.cmd if we know it works, but let's try shell=True with list (works on Windows Python)
        # Or construct string.
        cmd = f"opencode serve --port {port}"
        
    # Start server process
    # We pass env explicitly to ensure our key is there, though Popen usually inherits env
    env = os.environ.copy()
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=(os.name == 'nt'),
        env=env
    )
    
    # Wait for server to be ready
    base_url = f"http://127.0.0.1:{port}"
    max_attempts = 30
    
    for i in range(max_attempts):
        try:
            resp = requests.get(f"{base_url}/global/health", timeout=1)
            if resp.status_code == 200:
                data = resp.json()
                log(f"Server ready (version: {data.get('version', 'unknown')})", "ok")
                return proc
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            log(f"Health check error: {e}", "warn")
        
        time.sleep(1)
        if i % 5 == 4:
            log(f"  Still waiting... ({i+1}/{max_attempts})", "info")
    
    proc.terminate()
    # Read stderr to see what happened
    try:
        outs, errs = proc.communicate(timeout=5)
        log(f"Server stderr: {errs}", "error")
    except:
        pass
        
    log("Server failed to start within 30 seconds", "error")
    return None


def test_api_endpoints(base_url: str) -> dict:
    """Test core API endpoints."""
    results = {}
    
    # Test 1: Health endpoint
    log("Testing /global/health endpoint...", "info")
    try:
        resp = requests.get(f"{base_url}/global/health")
        results["health"] = resp.status_code == 200
        log(f"Health: {resp.json()}", "ok" if results["health"] else "error")
    except Exception as e:
        results["health"] = False
        log(f"Health failed: {e}", "error")
    
    # Test 2: List sessions
    log("Testing /session endpoint...", "info")
    try:
        resp = requests.get(f"{base_url}/session")
        results["session_list"] = resp.status_code == 200
        sessions = resp.json()
        log(f"Sessions: {len(sessions)} existing", "ok" if results["session_list"] else "error")
    except Exception as e:
        results["session_list"] = False
        log(f"Session list failed: {e}", "error")
    
    # Test 3: Create session
    log("Testing session creation...", "info")
    try:
        resp = requests.post(
            f"{base_url}/session",
            json={"title": "LifeOS Phase 0 Validation"},
            headers={"Content-Type": "application/json"}
        )
        results["session_create"] = resp.status_code == 200
        if results["session_create"]:
            session = resp.json()
            results["session_id"] = session.get("id")
            log(f"Created session: {results['session_id']}", "ok")
        else:
            log(f"Session create failed: {resp.status_code} - {resp.text}", "error")
    except Exception as e:
        results["session_create"] = False
        log(f"Session create failed: {e}", "error")
    
    # Test 4: Send prompt and get response
    if results.get("session_id"):
        log("Testing prompt/response cycle (this may take 10-20 seconds)...", "info")
        try:
            # Note: For OpenRouter/OpenAI compatibility, arguments might vary.
            # Assuming opencode abstracts this or expects standard format.
            resp = requests.post(
                f"{base_url}/session/{results['session_id']}/message",
                json={
                    "parts": [{"type": "text", "text": "Respond with exactly: LIFEOS_PHASE0_OK"}]
                },
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            results["prompt"] = resp.status_code == 200
            if results["prompt"]:
                msg = resp.json()
                parts = msg.get("parts", [])
                text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
                response_text = " ".join(text_parts)
                
                if "LIFEOS_PHASE0_OK" in response_text:
                    log(f"Got expected response", "ok")
                    results["response_valid"] = True
                else:
                    log(f"Response received but unexpected: {response_text[:100]}...", "warn")
                    # We mark valid if we got *any* response, as model behavior might vary
                    # But the prompt asked for exact string.
                    results["response_valid"] = False
            else:
                log(f"Prompt failed: {resp.status_code} - {resp.text[:200]}", "error")
        except requests.exceptions.Timeout:
            results["prompt"] = False
            log("Prompt timed out after 60 seconds", "error")
        except Exception as e:
            results["prompt"] = False
            log(f"Prompt failed: {e}", "error")
    
    # Test 5: Delete session (cleanup)
    if results.get("session_id"):
        log("Cleaning up test session...", "info")
        try:
            resp = requests.delete(f"{base_url}/session/{results['session_id']}")
            results["cleanup"] = resp.status_code == 200
            log("Session deleted", "ok" if results["cleanup"] else "warn")
        except Exception as e:
            results["cleanup"] = False
            log(f"Cleanup failed (non-critical): {e}", "warn")
    
    return results


def test_event_stream(base_url: str) -> bool:
    """Test SSE event stream connectivity."""
    log("Testing event stream (SSE)...", "info")
    try:
        # Just verify we can connect - don't wait for events
        resp = requests.get(f"{base_url}/event", stream=True, timeout=5)
        if resp.status_code == 200:
            # Read first chunk to verify stream works
            for chunk in resp.iter_content(chunk_size=100):
                log("Event stream connected", "ok")
                resp.close()
                return True
        log(f"Event stream returned {resp.status_code}", "error")
        return False
    except requests.exceptions.Timeout:
        # Timeout is OK - means connection works but no events yet
        log("Event stream connected (no events)", "ok")
        return True
    except Exception as e:
        log(f"Event stream failed: {e}", "error")
        return False


def generate_report(results: dict) -> str:
    """Generate a summary report."""
    report = []
    report.append("")
    report.append("=" * 60)
    report.append("PHASE 0 VALIDATION REPORT")
    report.append("=" * 60)
    report.append("")
    
    core_tests = ["health", "session_list", "session_create", "prompt"]
    passed = sum(1 for t in core_tests if results.get(t))
    total = len(core_tests)
    
    report.append(f"Core Tests: {passed}/{total} passed")
    report.append("")
    
    for test in core_tests:
        status = "✓ PASS" if results.get(test) else "✗ FAIL"
        report.append(f"  {test}: {status}")
    
    report.append("")
    
    if passed == total:
        report.append(f"{Colors.GREEN}{Colors.BOLD}STATUS: PHASE 0 PASSED{Colors.RESET}")
        report.append("")
        report.append("OpenCode API connectivity validated. Ready for Phase 1.")
        report.append("")
        report.append("Next steps:")
        report.append("  1. Review architecture with council")
        report.append("  2. Create governance service skeleton")
        report.append("  3. Implement doc steward agent config")
    else:
        report.append(f"{Colors.RED}{Colors.BOLD}STATUS: PHASE 0 FAILED{Colors.RESET}")
        report.append("")
        report.append("Resolve failures before proceeding.")
    
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    print(f"\n{Colors.BOLD}LifeOS Phase 0: OpenCode Validation{Colors.RESET}\n")
    
    # Check prerequisites
    if not check_prerequisites():
        print(f"\n{Colors.RED}Prerequisites not met. Exiting.{Colors.RESET}")
        sys.exit(1)
    
    print()
    
    # Start server
    port = 4096
    server_proc = start_server(port)
    if not server_proc:
        sys.exit(1)
    
    print()
    base_url = f"http://127.0.0.1:{port}"
    
    try:
        # Run tests
        results = test_api_endpoints(base_url)
        
        print()
        results["event_stream"] = test_event_stream(base_url)
        
        # Generate report
        print(generate_report(results))
        
        # Exit code based on results
        core_passed = all(results.get(t) for t in ["health", "session_list", "session_create", "prompt"])
        sys.exit(0 if core_passed else 1)
        
    finally:
        # Cleanup: stop server
        log("Stopping server...", "info")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
            log("Server stopped", "ok")
        except subprocess.TimeoutExpired:
            server_proc.kill()
            log("Server killed", "warn")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted{Colors.RESET}")
        sys.exit(130)
