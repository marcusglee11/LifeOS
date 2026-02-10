#!/usr/bin/env python3
"""
Claude Code Review Packet Gate

Enforces that a Review Packet exists before Claude Code session completion.

Exit codes:
  0: Review Packet gate passed
  1: Review Packet gate failed
  2: Error condition
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def find_recent_review_packet(repo_root: Path, max_age_minutes: int = 120) -> Optional[Path]:
    """
    Find the most recent Review Packet in artifacts/review_packets/.

    Looks for .md files created/modified in the last max_age_minutes.
    """
    packets_dir = repo_root / "artifacts" / "review_packets"

    if not packets_dir.exists():
        # Try alternate location (root level)
        packets = list(repo_root.glob("Review_Packet_*.md"))
        if packets:
            # Sort by modification time, most recent first
            packets.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return packets[0]
        return None

    # Find all .md files in packets directory
    packets = list(packets_dir.glob("*.md"))

    if not packets:
        # Check root level as fallback
        packets = list(repo_root.glob("Review_Packet_*.md"))

    if not packets:
        return None

    # Filter by age and sort
    now = datetime.now()
    cutoff = now - timedelta(minutes=max_age_minutes)

    recent_packets = []
    for packet in packets:
        mtime = datetime.fromtimestamp(packet.stat().st_mtime)
        if mtime >= cutoff:
            recent_packets.append(packet)

    if not recent_packets:
        return None

    # Return most recent
    recent_packets.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recent_packets[0]


def validate_review_packet(packet_path: Path, lightweight_mode: bool, repo_root: Path) -> Dict[str, Any]:
    """
    Validate Review Packet using validate_review_packet.py script.

    Returns:
      - valid: bool
      - errors: list of error messages
    """
    validator_script = repo_root / "scripts" / "validate_review_packet.py"

    if not validator_script.exists():
        return {
            'valid': False,
            'errors': [f"Validator script not found: {validator_script}"]
        }

    # Build command
    cmd = [sys.executable, str(validator_script), str(packet_path)]

    if lightweight_mode:
        cmd.append("--lightweight")

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return {'valid': True, 'errors': []}
        else:
            # Parse error output
            errors = result.stdout.strip().split('\n') if result.stdout else []
            if result.stderr:
                errors.extend(result.stderr.strip().split('\n'))
            return {'valid': False, 'errors': errors}

    except subprocess.TimeoutExpired:
        return {'valid': False, 'errors': ['Validation timed out']}
    except Exception as e:
        return {'valid': False, 'errors': [f"Validation error: {str(e)}"]}


def enforce_review_packet_gate(repo_root: Path, lightweight_mode: bool) -> Dict[str, Any]:
    """
    Enforce Review Packet gate.

    Returns:
      - passed: bool
      - review_packet_path: str (if found)
      - errors: list of error messages
    """
    # Find most recent Review Packet
    packet_path = find_recent_review_packet(repo_root)

    if not packet_path:
        return {
            'passed': False,
            'review_packet_path': None,
            'errors': [
                'No Review Packet found',
                'Expected: artifacts/review_packets/Review_Packet_*.md',
                f"Or: Review_Packet_*.md in repo root (created in last 120 minutes)"
            ]
        }

    # Validate the packet
    validation_result = validate_review_packet(packet_path, lightweight_mode, repo_root)

    if not validation_result['valid']:
        return {
            'passed': False,
            'review_packet_path': str(packet_path.relative_to(repo_root)),
            'errors': [
                f"Review Packet found but validation failed: {packet_path.name}",
                *validation_result['errors']
            ]
        }

    return {
        'passed': True,
        'review_packet_path': str(packet_path.relative_to(repo_root)),
        'errors': []
    }


def main():
    """Main entry point."""
    # Parse arguments
    lightweight_mode = "--lightweight" in sys.argv

    # Determine repo root
    repo_root = Path.cwd()
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        print(json.dumps({
            'passed': False,
            'review_packet_path': None,
            'errors': ['Not in a git repository']
        }), file=sys.stderr)
        sys.exit(2)

    # Enforce gate
    result = enforce_review_packet_gate(repo_root, lightweight_mode)

    # Output JSON
    print(json.dumps(result, indent=2))

    # Exit code
    if result['passed']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
