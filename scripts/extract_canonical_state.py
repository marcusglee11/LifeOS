#!/usr/bin/env python3
"""
Extract canonical state from LIFEOS_STATE.md into artifacts/status/canonical_state.yaml.

LIFEOS_STATE.md is authoritative. canonical_state.yaml is a derived descriptive view.
Run this manually or as a step in close_build.py closure sequence.

Usage:
  python scripts/extract_canonical_state.py

Exits 0 on success, 1 on failure.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "docs" / "11_admin" / "LIFEOS_STATE.md"
OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "canonical_state.yaml"

# Same 3 regex patterns as session-context-inject.py (intentional duplication — see Gap E rationale)
_FOCUS_RE = re.compile(r"\*\*Current Focus:\*\*\s*(.+)")
_WIP_RE = re.compile(r"\*\*Active WIP:\*\*\s*(.+)")
_UPDATED_RE = re.compile(r"\*\*Last Updated:\*\*\s*(.+)")
_BLOCKERS_RE = re.compile(r"\*\*Blockers?:\*\*\s*(.+)")
_PHASE_RE = re.compile(r"phase_(\w+):\s*([\w]+)")


def parse_state(content: str) -> dict:
    def first(pattern: re.Pattern) -> str:
        m = pattern.search(content)
        return m.group(1).strip() if m else ""

    current_focus = first(_FOCUS_RE)
    active_wip = first(_WIP_RE)
    last_updated = first(_UPDATED_RE)

    blockers_raw = first(_BLOCKERS_RE)
    if blockers_raw and blockers_raw.lower() not in ("none", "[]", ""):
        blockers = [b.strip() for b in blockers_raw.split(",") if b.strip()]
    else:
        blockers = []

    phase_status = {}
    for m in _PHASE_RE.finditer(content):
        phase_status[f"phase_{m.group(1)}"] = m.group(2)

    return {
        "current_focus": current_focus,
        "active_wip": active_wip,
        "last_updated": last_updated,
        "blockers": blockers,
        "phase_status": phase_status,
    }


def main() -> int:
    if not STATE_FILE.exists():
        print(f"ERROR: {STATE_FILE} not found", file=sys.stderr)
        return 1

    content = STATE_FILE.read_text(encoding="utf-8")
    parsed = parse_state(content)

    extracted_at = datetime.now(timezone.utc).isoformat()

    # Build YAML manually to avoid yaml dependency and control key order
    lines = [
        "schema_version: canonical_state.v1",
        f"extracted_from: docs/11_admin/LIFEOS_STATE.md",
        f"extracted_at: \"{extracted_at}\"",
        f"current_focus: \"{parsed['current_focus']}\"",
        f"active_wip: \"{parsed['active_wip']}\"",
        f"last_updated: \"{parsed['last_updated']}\"",
    ]

    if parsed["blockers"]:
        lines.append("blockers:")
        for b in parsed["blockers"]:
            lines.append(f"  - \"{b}\"")
    else:
        lines.append("blockers: []")

    if parsed["phase_status"]:
        lines.append("phase_status:")
        for k, v in sorted(parsed["phase_status"].items()):
            lines.append(f"  {k}: {v}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
