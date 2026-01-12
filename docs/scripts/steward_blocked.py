#!/usr/bin/env python3
"""
steward_blocked.py - Report on BLOCKED packets visibility.

Scans artifacts/packets/blocked/*.yaml and emits a deterministic report
grouping by owner with age-hours and unblock_condition.

Ordering: sorted by created_at (ascending, UNKNOWN last), then by path.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
BLOCKED_DIR = REPO_ROOT / "artifacts" / "packets" / "blocked"
REPORT_DIR = REPO_ROOT / "artifacts" / "packets" / "reports"


def parse_created_at(created_at: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 timestamp."""
    if not created_at:
        return None
    try:
        # Handle various ISO formats
        if created_at.endswith('Z'):
            created_at = created_at[:-1] + '+00:00'
        return datetime.fromisoformat(created_at)
    except ValueError:
        return None


def calculate_age_hours(created_at: Optional[str]) -> str:
    """Calculate age in hours from created_at."""
    dt = parse_created_at(created_at)
    if not dt:
        return "UNKNOWN"
    
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    delta = now - dt
    hours = delta.total_seconds() / 3600
    return f"{hours:.1f}h"


def get_created_at_for_item(item: dict) -> Optional[str]:
    """Extract created_at from item or nested blocked structure."""
    blocked = item.get("blocked", {})
    return blocked.get("created_at") or item.get("created_at")


def sort_key_for_item(item: dict) -> Tuple[int, str, str]:
    """Generate sort key: (has_date, created_at_iso, source_path).
    
    Items with dates sort first (ascending), then items without dates (UNKNOWN).
    Within same date bucket, sort by source path.
    """
    created_at = get_created_at_for_item(item)
    source = item.get("_source_path", "zzz_unknown")
    
    dt = parse_created_at(created_at)
    if dt is None:
        # UNKNOWN dates sort last (priority 1), then by path
        return (1, "9999-12-31", source)
    else:
        # Valid dates sort first (priority 0), ascending, then by path
        return (0, dt.isoformat(), source)


def load_blocked_packets() -> list:
    """Load all BLOCKED packets from artifacts/packets/blocked/, sorted deterministically."""
    if not BLOCKED_DIR.exists():
        return []
    
    packets = []
    for path in sorted(BLOCKED_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if data:
                data["_source_path"] = str(path.relative_to(REPO_ROOT))
                packets.append(data)
        except Exception as e:
            print(f"Warning: Failed to parse {path}: {e}", file=sys.stderr)
    
    # Sort deterministically before returning
    packets.sort(key=sort_key_for_item)
    return packets


def group_by_owner(packets: list) -> dict:
    """Group packets by owner, maintaining deterministic order within groups."""
    groups = {"Builder": [], "CEO": [], "Council": [], "UNKNOWN": []}
    
    for packet in packets:
        # Handle nested blocked structure
        blocked = packet.get("blocked", packet)
        owner = blocked.get("owner", "UNKNOWN")
        if owner not in groups:
            groups[owner] = []
        groups[owner].append(packet)
    
    # Sort each group deterministically
    for owner in groups:
        groups[owner].sort(key=sort_key_for_item)
    
    return groups


def generate_report(groups: dict) -> str:
    """Generate deterministic markdown report."""
    lines = [
        "# BLOCKED Items Report",
        "",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"**Total Items**: {sum(len(v) for v in groups.values())}",
        "",
    ]
    
    for owner in ["Builder", "CEO", "Council", "UNKNOWN"]:
        items = groups.get(owner, [])
        if not items:
            continue
        
        lines.append(f"## Owner: {owner}")
        lines.append("")
        lines.append("| Source | Age | Unblock Condition |")
        lines.append("|--------|-----|-------------------|")
        
        # Items are already sorted by sort_key_for_item
        for item in items:
            blocked = item.get("blocked", item)
            source = item.get("_source_path", "UNKNOWN")
            created_at = get_created_at_for_item(item)
            age = calculate_age_hours(created_at)
            condition = blocked.get("unblock_condition", "Not specified")
            lines.append(f"| {source} | {age} | {condition} |")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    packets = load_blocked_packets()
    
    if not packets:
        print("No blocked items found in artifacts/packets/blocked/")
        return 0
    
    groups = group_by_owner(packets)
    report = generate_report(groups)
    
    # Write report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"blocked_report_{ts}.md"
    report_path.write_text(report, encoding="utf-8")
    
    print(report)
    print(f"\nReport written to: {report_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
