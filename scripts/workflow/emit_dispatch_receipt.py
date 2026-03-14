#!/usr/bin/env python3
"""
Emit an invocation receipt after a Codex shell dispatch.

Called by dispatch_codex.sh after codex exits so the audit trail
matches the invocation_receipt schema used by the Python receipt system.

Usage:
    emit_dispatch_receipt.py --topic TOPIC --worktree PATH
                             --exit-code N --repo-root PATH
                             [--start-ts ISO] [--end-ts ISO]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit Codex dispatch invocation receipt")
    parser.add_argument("--topic", required=True, help="Codex dispatch topic slug")
    parser.add_argument("--worktree", required=True, help="Absolute worktree path")
    parser.add_argument("--exit-code", required=True, type=int, help="Codex process exit code")
    parser.add_argument("--repo-root", required=True, help="Repository root path (receipt output base)")
    parser.add_argument("--python-root", default="", help="Python import root if different from --repo-root")
    parser.add_argument("--start-ts", default="", help="ISO start timestamp (optional)")
    parser.add_argument("--end-ts", default="", help="ISO end timestamp (optional)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    python_root = Path(args.python_root) if args.python_root else repo_root

    # Add python_root to sys.path so we can import runtime.*
    if str(python_root) not in sys.path:
        sys.path.insert(0, str(python_root))

    from runtime.receipts.invocation_receipt import (
        finalize_run_receipts,
        record_invocation_receipt,
    )
    from runtime.util.canonical import compute_sha256

    end_ts = args.end_ts or _utc_now()
    start_ts = args.start_ts or end_ts  # best-effort if caller omitted start

    # Content-addressable run_id from topic + worktree
    run_id = compute_sha256({"provider": "codex", "topic": args.topic, "worktree": args.worktree})

    record_invocation_receipt(
        run_id=run_id,
        provider_id="codex",
        mode="cli",
        seat_id=f"codex_{args.topic}",
        start_ts=start_ts,
        end_ts=end_ts,
        exit_status=args.exit_code,
        output_content="",  # Codex stdout is already written to worktree files
        schema_validation="n/a",
        error=f"exit code {args.exit_code}" if args.exit_code != 0 else None,
    )

    index_path = finalize_run_receipts(run_id, output_dir=repo_root)
    if index_path:
        print(f"[emit_dispatch_receipt] receipt written: {index_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
