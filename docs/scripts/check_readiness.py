#!/usr/bin/env python3
"""
check_readiness.py - Preflight readiness checker.

Runs pytest, captures output, computes hashes, and emits READINESS packet.
"""

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = REPO_ROOT / "logs" / "preflight"
PACKETS_DIR = REPO_ROOT / "artifacts" / "packets" / "readiness"
CURRENT_DIR = REPO_ROOT / "artifacts" / "packets" / "current"
STATE_PATH = REPO_ROOT / "docs" / "11_admin" / "LIFEOS_STATE.md"


def sha256_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def check_blockers() -> list[str]:
    """Check LIFEOS_STATE.md for blockers."""
    if not STATE_PATH.exists():
        return []
    
    content = STATE_PATH.read_text(encoding="utf-8")
    
    # Find Blockers section
    import re
    match = re.search(r'## Blockers\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if not match:
        return []
    
    blockers_text = match.group(1).strip()
    if blockers_text.lower() in ("none", "- none", ""):
        return []
    
    # Extract blocker lines
    blockers = []
    for line in blockers_text.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            blockers.append(line[1:].strip())
    
    return blockers


def check_blocked_packets() -> list[str]:
    """Check for unresolved BLOCKED packets."""
    blocked_dir = REPO_ROOT / "artifacts" / "packets" / "blocked"
    if not blocked_dir.exists():
        return []
    
    return [str(p.relative_to(REPO_ROOT)) for p in blocked_dir.glob("*.yaml")]


def run_pytest(component: str = "general") -> dict:
    """Run pytest and capture results."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_filename = f"test_output_{ts}_{component}.log"
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / log_filename
    
    # Run pytest
    result = subprocess.run(
        ["pytest", "runtime/tests", "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    
    # Write log
    log_content = f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}\n\n=== EXIT CODE ===\n{result.returncode}"
    log_path.write_text(log_content, encoding="utf-8")
    
    return {
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "log_path": str(log_path.relative_to(REPO_ROOT)),
        "stdout_hash": sha256_hash(stdout),
        "stderr_hash": sha256_hash(stderr),
    }


def generate_readiness_packet(test_result: dict, blockers: list, blocked_packets: list, component: str) -> dict:
    """Generate READINESS packet."""
    checks = [
        {
            "id": "CHK-001",
            "name": "Runtime Tests",
            "command": "pytest runtime/tests -q",
            "status": "PASSED" if test_result["exit_code"] == 0 else "FAILED",
            "evidence_path": test_result["log_path"],
        },
        {
            "id": "CHK-002",
            "name": "No Blockers in LIFEOS_STATE",
            "source": "docs/11_admin/LIFEOS_STATE.md",
            "status": "PASSED" if not blockers else "FAILED",
            "details": blockers if blockers else None,
        },
        {
            "id": "CHK-003",
            "name": "No Unresolved BLOCKED Packets",
            "source": "artifacts/packets/blocked/",
            "status": "PASSED" if not blocked_packets else "FAILED",
            "details": blocked_packets if blocked_packets else None,
        },
    ]
    
    failed_checks = [c["id"] for c in checks if c["status"] == "FAILED"]
    outcome = "NOT_READY" if failed_checks else "READY"
    
    packet = {
        "packet_type": "READINESS",
        "packet_id": str(__import__("uuid").uuid4()),
        "component": component,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "attestation": {
            "script_path": "docs/scripts/check_readiness.py",
            "exit_code": test_result["exit_code"],
            "stdout_hash": test_result["stdout_hash"],
            "stderr_hash": test_result["stderr_hash"],
            "log_path": test_result["log_path"],
        },
        "decision": {
            "outcome": outcome,
            "blocking_checks": failed_checks,
            "recommended_action": "Proceed with build" if outcome == "READY" else "Fix blocking issues first",
        },
    }
    
    return packet


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check build readiness")
    parser.add_argument("--component", default="general", help="Component name for logging")
    args = parser.parse_args()
    
    component = args.component.replace(" ", "_").lower()
    
    print(f"Running preflight checks for: {args.component}")
    print("=" * 50)
    
    # Check blockers
    print("Checking LIFEOS_STATE.md for blockers...")
    blockers = check_blockers()
    if blockers:
        print(f"  WARN: Found {len(blockers)} blocker(s)")
    else:
        print("  OK: No blockers")
    
    # Check blocked packets
    print("Checking for unresolved BLOCKED packets...")
    blocked_packets = check_blocked_packets()
    if blocked_packets:
        print(f"  WARN: Found {len(blocked_packets)} BLOCKED packet(s)")
    else:
        print("  OK: No BLOCKED packets")
    
    # Run tests
    print("Running pytest runtime/tests -q...")
    test_result = run_pytest(component)
    if test_result["exit_code"] == 0:
        print(f"  OK: Tests passed")
    else:
        print(f"  FAIL: Tests failed (exit code {test_result['exit_code']})")
    
    # Generate packet
    packet = generate_readiness_packet(test_result, blockers, blocked_packets, component)
    
    # Write packet
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    packet_path = PACKETS_DIR / f"READINESS_{component}_{ts}.yaml"
    packet_path.write_text(yaml.dump(packet, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    # Update current pointer
    current_comp_dir = CURRENT_DIR / component
    current_comp_dir.mkdir(parents=True, exist_ok=True)
    pointer_path = current_comp_dir / "READINESS.current.yaml"
    pointer_path.write_text(yaml.dump(packet, sort_keys=False, allow_unicode=True), encoding="utf-8")
    
    print("=" * 50)
    print(f"Outcome: {packet['decision']['outcome']}")
    print(f"Log: {test_result['log_path']}")
    print(f"Packet: {packet_path.relative_to(REPO_ROOT)}")
    print(f"Attestation:")
    print(f"  stdout_hash: {test_result['stdout_hash']}")
    print(f"  stderr_hash: {test_result['stderr_hash']}")
    
    # Exit with appropriate code
    return 0 if packet['decision']['outcome'] == 'READY' else 1


if __name__ == "__main__":
    sys.exit(main())
