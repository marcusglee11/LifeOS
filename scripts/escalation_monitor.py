#!/usr/bin/env python3
"""
Escalation Monitor - Observe and summarize escalation artifacts.

Provides operator visibility into autonomous loop escalations.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md - P1.1 Observability.

Usage:
    python scripts/escalation_monitor.py              # Show summary
    python scripts/escalation_monitor.py --watch      # Continuous watch mode
    python scripts/escalation_monitor.py --json       # JSON output
    python scripts/escalation_monitor.py --verbose    # Show full escalation details
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# Escalation artifact location per policy.py
ESCALATION_DIR = "artifacts/escalations"

# Default watch interval
WATCH_INTERVAL_SECONDS = 5


def get_repo_root() -> Path:
    """Detect repository root."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    if not (repo_root / ".git").exists():
        # Try cwd
        cwd = Path.cwd()
        if (cwd / ".git").exists():
            return cwd
        raise RuntimeError("Cannot detect repository root")
    return repo_root


def parse_escalation(file_path: Path) -> Optional[Dict]:
    """Parse an escalation artifact JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "file": file_path.name,
            "path": str(file_path),
            "reason": data.get("reason", "UNKNOWN"),
            "requested_authority": data.get("requested_authority", "UNKNOWN"),
            "ttl_seconds": data.get("ttl_seconds", 0),
            "created_at": data.get("created_at", ""),
            "context": data.get("context", {}),
        }
    except json.JSONDecodeError:
        return {
            "file": file_path.name,
            "path": str(file_path),
            "reason": "PARSE_ERROR: Invalid JSON",
            "requested_authority": "UNKNOWN",
            "ttl_seconds": 0,
            "created_at": "",
            "context": {},
        }
    except Exception as e:
        return {
            "file": file_path.name,
            "path": str(file_path),
            "reason": f"READ_ERROR: {type(e).__name__}",
            "requested_authority": "UNKNOWN",
            "ttl_seconds": 0,
            "created_at": "",
            "context": {},
        }


def is_expired(escalation: Dict) -> bool:
    """Check if escalation has expired based on TTL."""
    created_at = escalation.get("created_at", "")
    ttl = escalation.get("ttl_seconds", 0)

    if not created_at or ttl <= 0:
        return False  # Never expires if no TTL

    try:
        # Parse ISO timestamp
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_seconds = (now - created).total_seconds()
        return age_seconds > ttl
    except Exception:
        return False


def enumerate_escalations(repo_root: Path) -> List[Dict]:
    """Find and parse all escalation artifacts."""
    escalation_root = repo_root / ESCALATION_DIR
    escalations = []

    if not escalation_root.exists():
        return escalations

    # Recursively find all .json files
    for json_file in sorted(escalation_root.rglob("*.json")):
        parsed = parse_escalation(json_file)
        if parsed:
            parsed["expired"] = is_expired(parsed)
            # Extract domain from path (e.g., Policy_Engine)
            rel_path = json_file.relative_to(escalation_root)
            if len(rel_path.parts) > 1:
                parsed["domain"] = rel_path.parts[0]
            else:
                parsed["domain"] = "unknown"
            escalations.append(parsed)

    return escalations


def format_timestamp(iso_str: str) -> str:
    """Format ISO timestamp for display."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return iso_str[:19]


def print_summary(escalations: List[Dict], verbose: bool = False) -> None:
    """Print human-readable escalation summary."""
    if not escalations:
        print("No escalation artifacts found.")
        return

    # Group by domain
    by_domain: Dict[str, List[Dict]] = {}
    for e in escalations:
        domain = e.get("domain", "unknown")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(e)

    # Count stats
    total = len(escalations)
    expired = sum(1 for e in escalations if e.get("expired"))
    active = total - expired

    print("=" * 60)
    print("ESCALATION MONITOR - Summary")
    print("=" * 60)
    print(f"Total: {total}  |  Active: {active}  |  Expired: {expired}")
    print()

    for domain, items in sorted(by_domain.items()):
        print(f"--- {domain} ({len(items)} escalation(s)) ---")

        for e in items:
            status = "[EXPIRED]" if e.get("expired") else "[ACTIVE]"
            created = format_timestamp(e.get("created_at", ""))
            reason_short = e.get("reason", "")[:50]
            authority = e.get("requested_authority", "")

            print(f"  {status} {e['file']}")
            print(f"    Created: {created}")
            print(f"    Authority: {authority}")
            print(f"    Reason: {reason_short}...")

            if verbose:
                context = e.get("context", {})
                if context:
                    print(f"    Context: {json.dumps(context, indent=6)}")

            print()

    print("=" * 60)
    if active > 0:
        print(f"ACTION REQUIRED: {active} active escalation(s) await CEO resolution.")
    else:
        print("No active escalations.")


def print_json(escalations: List[Dict]) -> None:
    """Print escalations as JSON."""
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(escalations),
        "active": sum(1 for e in escalations if not e.get("expired")),
        "expired": sum(1 for e in escalations if e.get("expired")),
        "escalations": escalations,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def watch_mode(repo_root: Path, interval: int, verbose: bool) -> None:
    """Continuous watch mode - poll for new escalations."""
    seen_files: set = set()

    print(f"Watching for escalations (interval: {interval}s). Press Ctrl+C to stop.")
    print()

    try:
        while True:
            escalations = enumerate_escalations(repo_root)
            current_files = {e["file"] for e in escalations}

            # Detect new escalations
            new_files = current_files - seen_files
            if new_files:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] NEW ESCALATIONS DETECTED:")
                for e in escalations:
                    if e["file"] in new_files:
                        print(f"  - {e['file']}: {e.get('reason', '')[:60]}...")
                seen_files.update(new_files)

            # Summary every interval
            active = sum(1 for e in escalations if not e.get("expired"))
            expired = sum(1 for e in escalations if e.get("expired"))

            status = f"[{datetime.now().strftime('%H:%M:%S')}] Total: {len(escalations)} | Active: {active} | Expired: {expired}"
            # Overwrite line in-place
            print(f"\r{status}    ", end="", flush=True)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Escalation Monitor - Observe autonomous loop escalations"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuous watch mode"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=WATCH_INTERVAL_SECONDS,
        help=f"Watch interval in seconds (default: {WATCH_INTERVAL_SECONDS})"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full escalation details"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root (default: auto-detect)"
    )

    args = parser.parse_args()

    # Detect repo root
    try:
        if args.repo_root:
            repo_root = Path(args.repo_root)
        else:
            repo_root = get_repo_root()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.watch:
        watch_mode(repo_root, args.interval, args.verbose)
        return 0

    # One-shot mode
    escalations = enumerate_escalations(repo_root)

    if args.json:
        print_json(escalations)
    else:
        print_summary(escalations, args.verbose)

    # Exit code: 1 if active escalations, 0 otherwise
    active = sum(1 for e in escalations if not e.get("expired"))
    return 1 if active > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
