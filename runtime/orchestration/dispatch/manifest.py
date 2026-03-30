"""
RunManifest — append-only JSONL canonical manifest.

Per v2.1 § Storage Policy: artifacts/manifests/run_log.jsonl is the canonical run manifest.
Each line is a JSON object with a compact summary of one dispatch execution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

MANIFEST_RELATIVE_PATH = Path("artifacts/manifests/run_log.jsonl")


class RunManifest:
    """
    Append-only JSONL manifest at artifacts/manifests/run_log.jsonl.

    Each append writes one complete JSON line using a plain file append.
    Not safe for concurrent writers — Phase 1 single-flight constraint applies.
    Reading returns all recorded entries in order.
    """

    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        self.path = self.repo_root / MANIFEST_RELATIVE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: Dict[str, Any]) -> None:
        """Append one manifest entry as a JSON line."""
        entry_with_ts = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        line = (
            json.dumps(entry_with_ts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        )
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line)

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all manifest entries. Returns empty list if file doesn't exist."""
        if not self.path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries
