#!/usr/bin/env python3
"""Thin wrapper for close-build lifecycle with optional JSON output.

Without --json: streams stage banners and output live to stdout/stderr so
hangs are immediately attributable to a specific closure stage.

With --json: accumulates all output and emits a single JSON blob on exit
(backward-compatible with callers that parse structured output).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Stage banner markers emitted by closure_pack.py (matched by prefix)
_STAGE_PREFIXES = (
    "[tests]",
    "[quality_gate]",
    "[doc_stewardship]",
    "[merge]",
    "[cleanup]",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", default=".", help="Repository/worktree root (default: current directory)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Run gates only")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip post-merge cleanup")
    parser.add_argument("--no-state-update", action="store_true", help="Skip STATE/BACKLOG updates")
    parser.add_argument(
        "--allow-concurrent-wip",
        action="store_true",
        help=(
            "Skip untracked-file gate when concurrent agent WIP is present "
            "(Article XIX exemption)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured output (accumulates; no live streaming)",
    )
    args = parser.parse_args()

    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "workflow" / "closure_pack.py")]
    if args.repo_root:
        cmd.extend(["--repo-root", args.repo_root])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.no_cleanup:
        cmd.append("--no-cleanup")
    if args.no_state_update:
        cmd.append("--no-state-update")
    if args.allow_concurrent_wip:
        cmd.append("--allow-concurrent-wip")

    if args.json:
        # Accumulate mode: capture everything, emit single JSON blob on exit
        proc = subprocess.run(
            cmd,
            cwd=Path(args.repo_root).resolve(),
            capture_output=True,
            text=True,
            check=False,
        )
        print(
            json.dumps(
                {
                    "ok": proc.returncode == 0,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "",
                    "command": cmd,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return proc.returncode

    # Streaming mode: print stage banners and output live
    proc = subprocess.Popen(
        cmd,
        cwd=Path(args.repo_root).resolve(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Stream stdout line-by-line; emit stage banners when stage lines appear
    current_stage: str | None = None
    assert proc.stdout is not None
    for line in proc.stdout:
        stripped = line.rstrip("\n")
        for prefix in _STAGE_PREFIXES:
            if stripped.startswith(prefix):
                stage_label = prefix.strip("[]")
                if stage_label != current_stage:
                    current_stage = stage_label
                    print(f"\n--- [{stage_label}] ---", flush=True)
                break
        print(stripped, flush=True)

    proc.wait()
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
