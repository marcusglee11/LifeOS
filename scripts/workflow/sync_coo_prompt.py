#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from runtime.orchestration.ops.registry import resolve_openclaw_workspace_root
from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import sha256_file


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    canonical_path = repo_root / "config" / "coo" / "prompt_canonical.md"
    live_path = resolve_openclaw_workspace_root() / "AGENTS.md"
    live_path.parent.mkdir(parents=True, exist_ok=True)

    if not canonical_path.exists():
        print(json.dumps({"ok": False, "error": f"canonical prompt not found: {canonical_path}"}, indent=2))
        return 1

    content = canonical_path.read_text(encoding="utf-8")
    atomic_write_text(live_path, content)

    receipt_dir = repo_root / "artifacts" / "coo" / "operations" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "canonical_path": str(canonical_path),
        "live_path": str(live_path),
        "canonical_sha256": sha256_file(canonical_path),
        "live_sha256": sha256_file(live_path),
    }
    receipt_path = receipt_dir / f"prompt_sync_{ts}.json"
    atomic_write_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True))
    print(json.dumps({"ok": True, "receipt_path": str(receipt_path), **receipt}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
