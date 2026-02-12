#!/usr/bin/env python3
"""
Generate runtime status facts used by documentation freshness checks.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def generate(repo_root: Path) -> dict:
    lifeos_state = _read_text(repo_root / "docs" / "11_admin" / "LIFEOS_STATE.md")
    backlog = _read_text(repo_root / "docs" / "11_admin" / "BACKLOG.md")

    openclaw_bin = shutil.which("openclaw")
    openclaw_installed = openclaw_bin is not None

    claims_openclaw_blocker = "OpenClaw COO Install" in lifeos_state and "Only genuine gap" in lifeos_state
    backlog_openclaw_open = "- [ ] **Install OpenClaw COO on WSL2**" in backlog

    contradictions = []
    if openclaw_installed and claims_openclaw_blocker:
        contradictions.append("LIFEOS_STATE still claims OpenClaw install as blocker while binary is present.")
    if openclaw_installed and backlog_openclaw_open:
        contradictions.append("BACKLOG still lists OpenClaw install unchecked while binary is present.")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "facts": {
            "openclaw_installed": openclaw_installed,
            "openclaw_bin": openclaw_bin,
            "lifeos_state_claims_openclaw_blocker": claims_openclaw_blocker,
            "backlog_openclaw_install_unchecked": backlog_openclaw_open,
        },
        "contradictions": contradictions,
        "status": "ok" if not contradictions else "warn",
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    payload = generate(repo_root)
    status_dir = repo_root / "artifacts" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    status_path = status_dir / "runtime_status.json"
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checkpoint_dir = repo_root / "artifacts" / "packets" / "status"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = datetime.now(timezone.utc).strftime("checkpoint_report_%Y%m%d.json")
    checkpoint_path = checkpoint_dir / checkpoint_name
    checkpoint_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(str(status_path))
    print(str(checkpoint_path))
    print(payload["status"])
    for item in payload["contradictions"]:
        print(f"WARNING: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
